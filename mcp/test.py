from typing import Any
import asyncio
import httpx

# api_key = "f1b6f869657b44ad8fee0b6ea8ea0bbf"
# base_url = "https://jt33jqk344.re.qweatherapi.com"
# path = "/v7/weather/now?location=101070101"

# headers = {
#     "Accept": "application/json",
#     "User-Agent": "weather-app/1.0",
#     "X-QW-Api-Key": api_key
# }

# # 注意这里的 async def
# async def fetch_weather():
#     # 注意这里用的是 AsyncClient
#     async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
#         try:
#             # 注意这里的 await，表示“遇到网络等待时，先去干别的，等结果回来了再往下走”
#             response = await client.get(path, headers=headers)
#             response.raise_for_status()
#             data = response.json()
            
#             if data.get("code") == "200":
#                 print("异步获取天气成功:", data.get("now"))
#             else:
#                 print(f"API业务错误: {data}")

#         except Exception as e:
#             print(f"发生错误: {e}")

# # 运行异步函数的固定写法
# if __name__ == "__main__":
#     asyncio.run(fetch_weather())

api_key= "f1b6f869657b44ad8fee0b6ea8ea0bbf"
CMA_API_BASE = "https://jt33jqk344.re.qweatherapi.com"
USER_AGENT = "weather-app/1.0"

async def make_cma_request(url: str) -> dict[str, Any] | None:
    """统一的外部HTTP请求封装.(建议所有与外部网络的交互都通过此函数,便于统一打日志,处理超时和异常)"""
    headers = {
        "X-QW-Api-Key": api_key,
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            print(response.json())
            return response.json()
        except Exception:
            return None
async def get_weather_now(location: int) -> str:
    """Get weather now for a CN city.

    Args:
        location: 需要查询地区的LocationID或以英文逗号分隔的经度,纬度坐标(十进制，最多支持小数点后两位)
    """
    url = f"{CMA_API_BASE}/v7/weather/now?location={location}"
    data = await make_cma_request(url)

    if not data or "now" not in data:
        return "not found"

    if not data["now"]:
        return "not found"

    weather_now = data["now"]
    print(f"{weather_now}")
    return "\n---\n".join(weather_now)
if __name__ == "__main__":
    asyncio.run(get_weather_now(101070101))
