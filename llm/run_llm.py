import os
from openai import OpenAI
import asyncio
async def run_llm(sys_prompt,user_msg):
    message = [{'role': 'system', 'content': sys_prompt},
                {'role': 'user', 'content': user_msg}]
    return start(message)
def start(input):
    client = OpenAI(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    completion = client.chat.completions.create(
        model="qwen-plus",  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        messages=input,
        stream=False,
        # stream_options={"include_usage": True}
        )
    res = completion.choices[0].message.content
    return res
   

async def main():
    with open("E:/gitlab/mcp_learning/host/sys_prompt.md", "r", encoding="utf-8") as f:
        res = f.read()
    tool = '''
# 工具使用格式

工具使用采用 XML 风格的标签进行格式化。工具名称包含在开始和结束标签中，每个参数也同样包含在其自己的一组标签中。结构如下：

<tool_name>
<parameter1_name>value1</parameter1_name>
<parameter2_name>value2</parameter2_name>
...
</tool_name>

例如：

<read_file>
<path>src/main.js</path>
</read_file>

始终遵守此格式以确保工具使用的正确解析和执行。

#可用工具列表
工具名: get_alerts
描述: Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    
参数: {"properties": {"state": {"title": "State", "type": "string"}}, "required": ["state"], "title": "get_alertsArguments", "type": "object"}
--------------------
工具名: get_forecast
描述: Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    
参数: {"properties": {"latitude": {"title": "Latitude", "type": "number"}, "longitude": {"title": "Longitude", "type": "number"}}, "required": ["latitude", "longitude"], "title": "get_forecastArguments", "type": "object"}
--------------------
'''
    sys_prompt = f"""
{res}
{tool}
"""
    user_msg = '纽约明天天气怎么样'
    result =await run_llm(sys_prompt,user_msg)
    print(result)

    # for chunk in completion:
    #     print(chunk.model_dump_json())

# if __name__ == "__main__":
#     sys_prompt = 'You are a helpful assistant.'
#     user_msg = '你是谁'
#     run_llm(sys_prompt,user_msg)

if __name__ == "__main__":
    asyncio.run(main())

