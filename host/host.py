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
        #持续接收用户输入并调用 LLM
        if not hasattr(self, 'sessions') or not self.sessions:
            print("\n没有可用的 MCP Server,退出.")
            return

        print("\n所有服务连接完毕!输入你的问题(输入 'quit' 退出):")

        while True:
            try:
                user_msg = input("\ninput: ")
            except (EOFError, KeyboardInterrupt):
                break

            if user_msg.lower() in ['quit', 'exit', 'q']:
                break

            if not user_msg.strip():
                continue

            all_tools = []
            tools_str_list = []
            for tools in self.tools_by_name.values():
                for tool in tools:
                    # 把每个工具格式化为易读的文本，例如：
                    # 工具名: get_weather
                    # 描述: 获取指定城市的天气信息
                    # 参数: {"location": "城市名称", "unit": "温度单位"}
                    tool_desc = (
                        f"工具名: {tool.name}\n"
                        f"描述: {tool.description}\n"
                        f"参数: {json.dumps(tool.inputSchema, ensure_ascii=False)}\n"
                        "--------------------"
                    )
                    tools_str_list.append(tool_desc)
            
            # 把所有工具的文本用换行符拼成一个超级长的字符串
            tools_string = "\n".join(tools_str_list)
            sys_prompt_path = Path(SYSTEM_PROMPT_PATH)
            # 将工具字符串拼接到系统提示词中
            with open(sys_prompt_path, "r", encoding="utf-8") as f:
                sys_prompt = f.read()
            final_system_prompt = f"""
{sys_prompt}
#可用工具列表
{tools_string}
            """
            print(final_system_prompt)
            try:
                res = await run_llm(final_system_prompt, user_msg)
                print(res)
            except Exception as e:
                print(f"LLM 调用发生错误: {e}")
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
        # 后进先出，先退 session 再退 stdio
        for kind, name, cm in reversed(self._stack):
            try:
                await cm.__aexit__(None, None, None)
                print(f"[{name}] {kind} 已断开")
            except Exception as e:
                print(f"[{name}] {kind} 断开时出错: {e}")

async def main():
    manager = MCPClientManager()
    
    try:
        # 1. 启动并连接所有服务
        await manager.connect_servers()
        # 2. 进入聊天循环
        await manager.chat_loop()
    finally:
        # 3. 无论是否报错，最后都要清理子进程
        await manager.cleanup()

if __name__ == "__main__":
    # 整个程序的生命周期都在这一个 asyncio.run 里面
    asyncio.run(main())
