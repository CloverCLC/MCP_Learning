# MCP基础原理学习

这是一个基于openai的MCP Host基础原理实现,帮助理解MCP Host在Agent工作流中的工作定位
```py
# 项目初始化(需要安装uv)
uv sync
#启动项目
uv run .\host\host.py
```

## 项目结构

```text
mcp_learning/
├─ host/
|  ├─ host.py
|  └─ mcp_config.json
├─ llm/
|  └─ run_llm.py
└─ mcp/*
```

## 模块说明

- `host.py`: `MCP` 核心,用来读取 `MCP server` 以及与 `LLM` 交互的中枢
- `run_llm.py`: `LLM` 运行入口
- `mcp/*`: 各种 `mcp server`,通过 `openai` 规范的 `stdio` 格式编写 `MCP server`

## 核心实现原理
- 第一阶段(握手保持连接)
    1. Host启动MCP Server
    2. Host向MCP Server发起握手请求
    3. MCP Server 回应Host握手成功
    4. Host向MCP Server询问有哪些工具可用
    5. MCP Server回应可用工具列表
- 第二阶段(等待发起调用)
    1. Host等待用户发起提问
    2. Host收到用户请求后将问题转发给LLM
    3. LLM回应prompt里规定的固定格式内容给Host
    4. Host解析LLM的回复并判断是否需要调用MCP Tool
    5. 如果需要调用则转发调用请求至MCP Server,并重复`2-5`,否则返回给用户最终LLM回复


