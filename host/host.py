import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio


import re
import json
from pathlib import Path
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from llm.run_llm import run_llm

CONFIG_FILE_PATH = "host/mcp_config.json" 
SYSTEM_PROMPT_PATH = "host/sys_prompt.md"

class MCPClientManager:
    def __init__(self):
        self.sessions = {}
        self.tools_by_name = {}
        self._stack = []

    async def connect_servers(self):
        #读取配置并连接所有未禁用的 MCP Server
        config_path = Path(CONFIG_FILE_PATH)
        if not config_path.exists():
            print(f"找不到配置文件: {config_path.absolute()}")
            return

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        mcp_servers = config_data.get("mcpServers", {})
        if not mcp_servers:
            print("配置文件中未找到 mcpServers")
            return

        print(f"读取到 {len(mcp_servers)} 个 MCP Server 配置\n")

        for name, cfg in mcp_servers.items():
            if cfg.get("disabled", False):
                print(f"[{name}] 已在配置中被禁用，跳过")
                continue

            server_params = StdioServerParameters(
                command=cfg.get("command"),
                args=cfg.get("args", []),
                env=None
            )

            try:
                timeout = cfg.get("timeout", 30)

                # 用列表保存上下文管理器，确保在同一个任务中进和出
                cm_stdio = stdio_client(server_params)
                read_stream, write_stream = await cm_stdio.__aenter__()
                self._stack.append(("stdio", name, cm_stdio))

                cm_session = ClientSession(read_stream, write_stream)
                await cm_session.__aenter__()
                self._stack.append(("session", name, cm_session))

                # 握手
                await asyncio.wait_for(cm_session.initialize(), timeout=timeout)

                # 获取工具列表
                tools_result = await cm_session.list_tools()
                print(f"[{name}] 连接成功 发现 {len(tools_result.tools)} 个工具:")
                for tool in tools_result.tools:
                    print(f"  - {tool.name}: {tool.description}")

                # 保存工具列表供后续使用
                self.tools_by_name[name] = tools_result.tools
                self.sessions[name] = cm_session
                print("-" * 40)

            except asyncio.TimeoutError:
                print(f"[{name}] 连接超时")
            except Exception as e:
                print(f"[{name}] 连接错误: {type(e).__name__} - {e}")

    async def chat_loop(self):
        # 持续接收用户输入并调用 LLM
        if not hasattr(self, 'sessions') or not self.sessions:
            print("\n没有可用的 MCP Server, 退出.")
            return

        # 读取系统提示词
        sys_prompt_path = Path(SYSTEM_PROMPT_PATH)
        if not sys_prompt_path.exists():
            print(f"找不到系统提示词文件: {sys_prompt_path}")
            return
        with open(sys_prompt_path, "r", encoding="utf-8") as f:
            sys_prompt = f.read()

        # 把工具列表格式化为纯文本拼接到提示词
        tools_str_list = []
        for tools in self.tools_by_name.values():
            for tool in tools:
                tool_desc = (
                    f"工具名: {tool.name}\n"
                    f"描述: {tool.description}\n"
                    f"参数: {json.dumps(tool.inputSchema, ensure_ascii=False)}\n"
                    "--------------------"
                )
                tools_str_list.append(tool_desc)
        
        final_system_prompt = f"""
{sys_prompt}

# 可用工具列表
{chr(10).join(tools_str_list)}
        """
        print(final_system_prompt)
        print("\n所有服务连接完毕! 输入你的问题 (输入 'quit' 退出):\n")

        while True:
            try:
                user_msg = input("input: ")
            except (EOFError, KeyboardInterrupt):
                break

            if user_msg.lower() in ['quit', 'exit', 'q']:
                break

            if not user_msg.strip():
                continue

            

            # ============ Agent 循环开始 ============
            MAX_ROUNDS = 10  # 防止 LLM 陷入死循环
            current_prompt = user_msg
            final_answer_found = False

            for round_idx in range(MAX_ROUNDS):
                try:
                    # 调用 LLM
                    llm_res = await run_llm(final_system_prompt, current_prompt)
                    print("\nLLM开始调用工具\n")
                    print(llm_res)
                except Exception as e:
                    print(f"[Host] LLM 调用发生错误: {e}")
                    break

                # 核心解析逻辑：找出所有 XML 块，过滤掉 thinking 标签
                xml_pattern = r"<(\w+)>([\s\S]*?)</\1>"
                all_matches = re.findall(xml_pattern, llm_res)
                
                real_tool_name = None
                real_arguments = {}
                
                # 遍历找到的所有 XML 块，寻找真正的工具调用
                for tag_name, tag_content in all_matches:
                    tag_name = tag_name.strip().lower()
                    tag_content = tag_content.strip()
                    
                    # 跳过黑名单标签
                    blacklist = ["thinking"]
                    if tag_name in blacklist:
                        continue
                        
                    # 跳过空标签
                    if not tag_content:
                        continue
                        
                    # 找到了疑似工具,提取里面的子标签作为参数
                    arg_pattern = r"<(\w+)>([\s\S]*?)</\1>"
                    arg_matches = re.findall(arg_pattern, tag_content)
                    
                    # 简单校验:如果里面有子标签,才认定它是工具
                    if arg_matches:
                        real_tool_name = tag_name
                        real_arguments = {key: value.strip() for key, value in arg_matches}
                        break # 找到第一个合法工具就停止查找

                # 根据查找结果执行对应逻辑
                if real_tool_name:
                    print(f"\n[Host] 检测到工具调用 (第 {round_idx + 1} 轮): {real_tool_name}({json.dumps(real_arguments, ensure_ascii=False)})")
                    
                    # 调用 execute_tool 执行
                    tool_result = await self.execute_tool(real_tool_name, real_arguments)
                    
                    if tool_result:
                        # 提取 MCP 返回对象里的纯文本
                        result_text = ""
                        if hasattr(tool_result, 'content'):
                            for item in tool_result.content:
                                if hasattr(item, 'text'):
                                    result_text += item.text
                                else:
                                    result_text += str(item)
                        else:
                            result_text = str(tool_result)
                            
                        print(f"[Host] 工具返回结果: {result_text[:300]}{'...' if len(result_text) > 300 else ''}")
                        
                        # 拼装下一轮的 prompt,把数据喂回给 LLM
                        current_prompt = f"""用户最初的问题: {user_msg}
我帮你调用了工具 {real_tool_name}，返回的真实结果如下：
<tool_result>
{result_text}
</tool_result>

请根据上述真实结果回答用户的问题。如果不需要再调用其他工具，请直接给出最终答案。"""
                    else:
                        # 工具执行失败
                        print("[Host] 错误: 工具执行失败或找不到工具")
                        print(f"[LLM 原始输出]: {llm_res.strip()}")
                        final_answer_found = True
                        break
                        
                else:
                    # 没有找到任何工具调用,说明 LLM 直接给出了最终文本回答
                    print(f"\nLLM: {llm_res.strip()}")
                    final_answer_found = True
                    break

            # 如果跑完了最大轮数，LLM 还在死循环调工具，强制打断
            if not final_answer_found:
                print("\n[Host 警告] 已达到最大工具调用次数限制，强制停止。")
            # ============ Agent 循环结束 ============

    async def execute_tool(self, tool_name: str, arguments: dict):
        #根据工具名在所有连接的 MCP Server 中寻找并执行
        for name, tools in self.tools_by_name.items():
            for tool in tools:
                if tool.name == tool_name:
                    print(f"[Host] 正在向 [{name}] 发起工具调用: {tool_name}({arguments})")
                    session = self.sessions[name]
                    # 调用 MCP Server 的工具，并等待结果
                    result = await session.call_tool(tool_name, arguments=arguments)
                    return result
        
        print(f"[Host] 错误: 找不到名为 {tool_name} 的工具")
        return None

    async def cleanup(self):
        #按 LIFO 顺序退出所有上下文管理器
        print("\n正在断开所有 MCP Server 连接...")
        # 后进先出,先退 session 再退 stdio
        for kind, name, cm in reversed(self._stack):
            try:
                await cm.__aexit__(None, None, None)
                print(f"[{name}] {kind} 已断开")
            except Exception as e:
                print(f"[{name}] {kind} 断开时出错: {e}")

async def main():
    manager = MCPClientManager()
    
    try:
        # 启动并连接所有服务
        await manager.connect_servers()
        # 进入聊天循环
        await manager.chat_loop()
    finally:
        # 无论是否报错，最后都要清理子进程
        await manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
