"""
根据当前公网 IP 获取地理位置和天气信息
"""
import json


def _normalize(text: str) -> str:
    return text.replace("\n", " ").replace("\r", " ").strip()


def _weather_desc(hourly: list) -> str:
    if not hourly:
        return ""
    mid = hourly[len(hourly) // 2]
    return _normalize(mid.get("weatherDesc", [{}])[0].get("value", ""))


def get_weather_forecast(city: str, day: str = "tomorrow"):
    """
    查询指定城市天气预报。
    day: today / tomorrow / after_tomorrow
    """
    city = (city or "").strip()
    if not city:
        return {"success": False, "error": "未提供城市名"}

    day_index = {
        "today": 0,
        "tomorrow": 1,
        "after_tomorrow": 2,
    }.get(day, 1)

    try:
        import requests

        resp = requests.get(
            f"https://wttr.in/{city}?format=j1",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if resp.status_code != 200:
            return {"success": False, "error": f"天气服务返回 HTTP {resp.status_code}"}

        data = resp.json()
        forecast = data.get("weather", [])
        if len(forecast) <= day_index:
            return {"success": False, "error": "未获取到对应日期的天气预报"}

        item = forecast[day_index]
        hourly = item.get("hourly", [])
        astronomy = item.get("astronomy", [{}])[0]
        target_date = item.get("date", "")

        result = {
            "success": True,
            "city": city,
            "day": day,
            "date": target_date,
            "max_temp_c": item.get("maxtempC", ""),
            "min_temp_c": item.get("mintempC", ""),
            "avg_temp_c": item.get("avgtempC", ""),
            "weather_desc": _weather_desc(hourly),
            "sunrise": astronomy.get("sunrise", ""),
            "sunset": astronomy.get("sunset", ""),
        }

        if hourly:
            noon = min(hourly, key=lambda h: abs(int(h.get("time", "1200") or "1200") - 1200))
            result.update({
                "chance_of_rain": noon.get("chanceofrain", ""),
                "humidity": noon.get("humidity", ""),
                "wind_speed_kmph": noon.get("windspeedKmph", ""),
                "wind_dir": noon.get("winddir16Point", ""),
                "feels_like_c": noon.get("FeelsLikeC", ""),
                "uv_index": noon.get("uvIndex", ""),
            })

        return result

    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


def get_local_weather_forecast(day: str = "tomorrow"):
    """根据当前公网 IP 定位城市，再查询该城市天气预报。"""
    try:
        import urllib.request

        req = urllib.request.Request(
            "http://ip-api.com/json/?fields=status,country,regionName,city,lat,lon,query",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            ip_data = json.loads(resp.read().decode("utf-8"))

        if ip_data.get("status") != "success":
            return {
                "success": False,
                "error": f"IP 定位失败: {ip_data.get('message', '未知错误')}"
            }

        city = ip_data.get("city", "")
        forecast = get_weather_forecast(city, day=day)
        if forecast.get("success"):
            forecast["ip"] = ip_data.get("query", "")
            forecast["location"] = f"{ip_data.get('country', '')} {ip_data.get('regionName', '')} {city}".strip()
        return forecast

    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


def get_weather_by_ip():
    """
    综合获取：IP → 城市 + 天气
    第一步：ip-api 获取城市
    第二步：wttr.in 获取该城市天气
    """
    try:
        import urllib.request

        # 第一步：IP 定位
        req = urllib.request.Request(
            "http://ip-api.com/json/?fields=status,country,regionName,city,lat,lon,query",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            ip_data = json.loads(resp.read().decode("utf-8"))

        if ip_data.get("status") != "success":
            return {
                "success": False,
                "error": f"IP 定位失败: {ip_data.get('message', '未知错误')}"
            }

        city = ip_data.get("city", "")
        region = ip_data.get("regionName", "")
        country = ip_data.get("country", "")
        ip = ip_data.get("query", "")
        location = f"{country} {region} {city}".strip()

        # 第二步：天气
        import requests
        weather_data = {}
        weather_resp = requests.get(
            f"https://wttr.in/{city}?format=j1",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if weather_resp.status_code == 200:
            w = weather_resp.json()
            current = w.get("current_condition", [{}])[0]
            weather_data = {
                "temperature_c": current.get("temp_C", ""),
                "feels_like_c": current.get("FeelsLikeC", ""),
                "humidity": current.get("humidity", ""),
                "weather_desc": _normalize(current.get("weatherDesc", [{}])[0].get("value", "")),
                "wind_speed_kmph": current.get("windspeedKmph", ""),
                "wind_dir": current.get("winddir16Point", ""),
                "visibility_km": current.get("visibility", ""),
                "uv_index": current.get("uvIndex", ""),
            }

            forecast = w.get("weather", [])
            if forecast:
                today = forecast[0]
                weather_data["max_temp_c"] = today.get("maxtempC", "")
                weather_data["min_temp_c"] = today.get("mintempC", "")
                weather_data["sunrise"] = today.get("astronomy", [{}])[0].get("sunrise", "")
                weather_data["sunset"] = today.get("astronomy", [{}])[0].get("sunset", "")

        return {
            "success": True,
            "ip": ip,
            "location": location,
            "city": city,
            "region": region,
            "country": country,
            "weather": weather_data
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)[:200]
        }
