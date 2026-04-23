import asyncio
import json
from pathlib import Path
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# 1. 定义配置文件的路径
CONFIG_FILE_PATH = "host/mcp_config.json" 

async def load_and_run_server(server_name: str, server_config: dict):
    """根据配置启动并测试单个 MCP Server"""
    print(f"\n{'='*40}")
    print(f"正在连接 MCP Server: [{server_name}]")
    
    # 检查是否被禁用
    if server_config.get("disabled", False):
        print(f"{server_name} 已在配置中被禁用")
        return

    # 2. 构造 StdioServerParameters
    server_params = StdioServerParameters(
        command=server_config.get("command"),
        args=server_config.get("args", []),
        env=None # 如果需要额外环境变量可以在这里传，默认继承当前进程环境
    )

    try:
        # 3. 启动子进程并连接
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                
                # 4. 握手(设置超时时间，从配置中读取，默认 30 秒)
                timeout = server_config.get("timeout", 30)
                await asyncio.wait_for(session.initialize(), timeout=timeout)
                print(f"[{server_name}] 连接成功并完成握手！")

                # 5. 列出工具
                tools_result = await session.list_tools()
                print(f"[{server_name}] 发现 {len(tools_result.tools)} 个工具:")
                for tool in tools_result.tools:
                    print(f"  - {tool.name}: {tool.description}")

                # 这里可以像之前一样，接入 LLM 进行 tool_call 循环...
                # ...

    except asyncio.TimeoutError:
        print(f"[{server_name}] timeout")
    except Exception as e:
        print(f"[{server_name}] error: {type(e).__name__} - {e}")

async def main():
    # 1. 读取 JSON 配置文件
    config_path = Path(CONFIG_FILE_PATH)
    if not config_path.exists():
        print(f"找不到配置文件: {config_path.absolute()}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    mcp_servers = config_data.get("mcpServers", {})
    if not mcp_servers:
        print("not found mcpServers")
        return

    print(f"读取到 {len(mcp_servers)} 个 MCP Server 配置")

    # 2. 遍历配置，逐个连接
    # （如果你的 Server 之间没有依赖，可以用 asyncio.gather 并发启动）
    tasks = []
    for name, cfg in mcp_servers.items():
        tasks.append(load_and_run_server(name, cfg))
    
    # 串行执行，防止多个终端输出混在一起（推荐调试时使用）
    for task in tasks:
        await task
        
    # 如果想并发启动（生产环境可用）：
    # await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
