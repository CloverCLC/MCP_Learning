from typing import Any
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
            print(response.json())
            return response.json()
        except Exception:
            return None


@mcp.tool()
async def get_weather_now(location: int) -> str:
    """Get weather now for a LocationID.

    Args:
        location: 该地天气的LocationID,如果没有就先使用get_location_id工具获取LocationID
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

# @mcp.tool()
# async def get_forecast(latitude: float, longitude: float) -> str:
#     """Get weather forecast for a location.

#     Args:
#         latitude: Latitude of the location
#         longitude: Longitude of the location
#     """
#     # First get the forecast grid endpoint
#     points_url = f"{CMA_API_BASE}/points/{latitude},{longitude}"
#     points_data = await make_cma_request(points_url)

#     if not points_data:
#         return "Unable to fetch forecast data for this location."

#     # Get the forecast URL from the points response
#     forecast_url = points_data["properties"]["forecast"]
#     forecast_data = await make_cma_request(forecast_url)

#     if not forecast_data:
#         return "Unable to fetch detailed forecast."

#     # Format the periods into a readable forecast
#     periods = forecast_data["properties"]["periods"]
#     forecasts = []
#     for period in periods[:5]:  # Only show next 5 periods
#         forecast = f"""
# {period['name']}:
# Temperature: {period['temperature']}°{period['temperatureUnit']}
# Wind: {period['windSpeed']} {period['windDirection']}
# Forecast: {period['detailedForecast']}
# """
#         forecasts.append(forecast)

#     return "\n---\n".join(forecasts)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
