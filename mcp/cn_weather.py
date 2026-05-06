from typing import Any
import json
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('cn_weather',log_level="ERROR")
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

            return response.json()
        except json.JSONDecodeError:
            # 响应不是合法的 JSON（大概率是接口报错返回了 HTML 或纯文本）
            return f"API返回数据格式错误(非JSON),原始内容前100字符: {response.text[:100]}"
            
        except httpx.HTTPStatusError as e:
            # 专门处理 HTTP 状态码错误 (400, 401, 403, 404, 500等)
            # 尝试从和风天气的错误响应体里提取错误信息
            try:
                error_msg = e.response.json().get("message", "无详细说明")
            except:
                error_msg = e.response.text[:100]
            return f"API请求失败,状态码: {e.response.status_code},原因: {error_msg}"
            
        except httpx.TimeoutException:
            # 专门处理超时
            return "请求和风天气API超时,请稍后重试或检查网络。"
            
        except httpx.ConnectError:
            # 专门处理连接失败 (DNS解析失败、拒绝连接等)
            return "无法连接到和风天气API服务器,请检查网络连接。"
            
        except Exception as e:
            # 兜底处理其他未知异常 (一定不要吞掉,要把错误信息带出去)
            return f"发生未知异常: {type(e).__name__} - {str(e)}"

@mcp.tool()
async def get_weather_now(location: int) -> str:
    """Get weather now for a LocationID.

    Args:
        location: 该地天气的LocationID,如果没有就先使用get_location_id工具获取LocationID(仅限中国地区使用)
    """
    url = f"{CMA_API_BASE}/v7/weather/now?location={location}"
    data = await make_cma_request(url)

    if not data or "now" not in data:
        return "not found"

    if not data["now"]:
        return "not found"

    weather_now = data["now"]
    print(f"{weather_now}")
    return ";".join([f"{key}: {value}" for key, value in weather_now.items()])
@mcp.tool()
async def get_location_id(city:str) -> str:
    """获取该地的locationID

    Args:
        location: 该地的名称
    """
    url = f"{CMA_API_BASE}/geo/v2/city/lookup?location={city}"
    data = await make_cma_request(url)

    if not data or "location" not in data:
        return "not found"

    if not data["location"]:
        return "not found"

    location_info = data["location"]
    print(f"{location_info}")
    if isinstance(location_info, list) and location_info:
        # 返回第一个匹配城市的ID
        return str(location_info[0].get("id", "not found"))
    return str(location_info)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
