import os
from openai import OpenAI
async def run_llm(sys_prompt,user_msg):
    message = [{'role': 'system', 'content': sys_prompt},
                {'role': 'user', 'content': user_msg}]
    start(message)
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
    print(res)
    return res

  

    # for chunk in completion:
    #     print(chunk.model_dump_json())

if __name__ == "__main__":
    sys_prompt = 'You are a helpful assistant.'
    user_msg = '你是谁'
    run_llm(sys_prompt,user_msg)

