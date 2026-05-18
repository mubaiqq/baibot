"""
和风天气 - 实时天气 & 每日天气预报
"""
import json

QWEATHER_API_HOST = "mk7fbr9mk9.re.qweatherapi.com"
QWEATHER_API_KEY = "your-qweather-api-key"

CONFIG_SCHEMA = {
    "QWEATHER_API_HOST": {
        "label": "API 域名",
        "type": "text",
        "description": "和风天气开发者 API Host，前往 dev.qweather.com 获取。默认用开发者专属域名",
        "default": "mk7fbr9mk9.re.qweatherapi.com",
    },
    "QWEATHER_API_KEY": {
        "label": "API Key",
        "type": "password",
        "description": "和风天气开发者 Web API Key，前往控制台获取。免费订阅用 key 参数认证",
        "default": "",
    },
}


def apply_config(config: dict):
    global QWEATHER_API_HOST, QWEATHER_API_KEY
    if "QWEATHER_API_HOST" in config and config["QWEATHER_API_HOST"]:
        QWEATHER_API_HOST = config["QWEATHER_API_HOST"]
    if "QWEATHER_API_KEY" in config and config["QWEATHER_API_KEY"]:
        QWEATHER_API_KEY = config["QWEATHER_API_KEY"]


def _request(path: str, params: dict = None):
    import requests
    url = f"https://{QWEATHER_API_HOST}{path}"
    p = dict(params or {})
    p["key"] = QWEATHER_API_KEY
    headers = {"User-Agent": "baibot/1.0"}
    resp = requests.get(url, headers=headers, params=p, timeout=10)
    if resp.status_code != 200:
        try:
            detail = resp.json().get("code", str(resp.status_code))
        except Exception:
            detail = resp.status_code
        return {"success": False, "error": f"API 返回 {resp.status_code} ({detail})"}
    try:
        return resp.json()
    except Exception:
        return {"success": False, "error": "API 返回非 JSON 数据"}


def _lookup_location(city: str):
    data = _request("/geo/v2/city/lookup", {"location": city, "number": "1"})
    if isinstance(data, dict) and data.get("code") == "200":
        top_list = data.get("location", [])
        if top_list:
            loc = top_list[0]
            return {
                "id": loc.get("id", ""),
                "name": loc.get("name", ""),
                "adm1": loc.get("adm1", ""),
                "adm2": loc.get("adm2", ""),
                "country": loc.get("country", ""),
                "lat": loc.get("lat", ""),
                "lon": loc.get("lon", ""),
            }
    return None


def _auto_locate_city():
    import urllib.request
    req = urllib.request.Request(
        "http://ip-api.com/json/?fields=city", headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


def get_qweather_now(city: str = "", location: str = ""):
    loc_str = (location or "").strip()
    city = (city or "").strip()

    if not loc_str and not city:
        try:
            ipd = _auto_locate_city()
            city = ipd.get("city", "")
            if not city:
                return {"success": False, "error": "无法自动定位，请提供城市名", "summary": "和风天气：自动定位失败"}
        except Exception as e:
            return {"success": False, "error": f"自动定位失败: {e}", "summary": "和风天气：自动定位失败"}

    if not loc_str and city:
        lookup = _lookup_location(city)
        if not lookup:
            return {"success": False, "error": f"未找到城市「{city}」，请检查城市名", "summary": f"和风天气：未找到「{city}」"}
        loc_str = lookup["id"]
        loc_name = lookup["name"]
        loc_adm = f"{lookup.get('adm1', '')} {lookup.get('adm2', '')}".strip()
    else:
        loc_name = loc_str
        loc_adm = ""

    data = _request("/v7/weather/now", {"location": loc_str})
    if isinstance(data, dict) and data.get("code") == "200":
        now = data.get("now", {})
        return {
            "success": True,
            "city": loc_name,
            "adm": loc_adm,
            "obs_time": now.get("obsTime", ""),
            "temp_c": now.get("temp", ""),
            "feels_like_c": now.get("feelsLike", ""),
            "text": now.get("text", ""),
            "icon": now.get("icon", ""),
            "wind_dir": now.get("windDir", ""),
            "wind_scale": now.get("windScale", ""),
            "wind_speed_kmh": now.get("windSpeed", ""),
            "humidity": now.get("humidity", ""),
            "precip_mm": now.get("precip", ""),
            "pressure_hpa": now.get("pressure", ""),
            "vis_km": now.get("vis", ""),
            "cloud_pct": now.get("cloud", ""),
            "dew_c": now.get("dew", ""),
            "update_time": data.get("updateTime", ""),
            "summary": f"和风天气：{loc_name} {now.get('temp', '?')}°C {now.get('text', '?')}",
        }
    if isinstance(data, dict) and not data.get("success"):
        data["summary"] = data.get("summary", f"和风天气：{data.get('error', 'API异常')}")
        return data
    return {"success": False, "error": f"API 异常: {data}", "summary": "和风天气：API异常"}


def get_qweather_forecast(city: str = "", location: str = "", days: str = "3"):
    loc_str = (location or "").strip()
    city = (city or "").strip()
    days = days or "3"
    if days not in ("3", "7", "10", "15", "30"):
        days = "3"

    if not loc_str and not city:
        try:
            ipd = _auto_locate_city()
            city = ipd.get("city", "")
            if not city:
                return {"success": False, "error": "无法自动定位，请提供城市名", "summary": "和风天气：自动定位失败"}
        except Exception as e:
            return {"success": False, "error": f"自动定位失败: {e}", "summary": "和风天气：自动定位失败"}

    if not loc_str and city:
        lookup = _lookup_location(city)
        if not lookup:
            return {"success": False, "error": f"未找到城市「{city}」，请检查城市名", "summary": f"和风天气：未找到「{city}」"}
        loc_str = lookup["id"]
        loc_name = lookup["name"]
        loc_adm = f"{lookup.get('adm1', '')} {lookup.get('adm2', '')}".strip()
    else:
        loc_name = loc_str
        loc_adm = ""

    data = _request(f"/v7/weather/{days}d", {"location": loc_str})
    if isinstance(data, dict) and data.get("code") == "200":
        daily_list = data.get("daily", [])
        forecast = []
        for d in daily_list:
            forecast.append({
                "date": d.get("fxDate", ""),
                "temp_max_c": d.get("tempMax", ""),
                "temp_min_c": d.get("tempMin", ""),
                "text_day": d.get("textDay", ""),
                "text_night": d.get("textNight", ""),
                "icon_day": d.get("iconDay", ""),
                "icon_night": d.get("iconNight", ""),
                "wind_dir_day": d.get("windDirDay", ""),
                "wind_scale_day": d.get("windScaleDay", ""),
                "wind_speed_day_kmh": d.get("windSpeedDay", ""),
                "wind_dir_night": d.get("windDirNight", ""),
                "wind_scale_night": d.get("windScaleNight", ""),
                "wind_speed_night_kmh": d.get("windSpeedNight", ""),
                "humidity": d.get("humidity", ""),
                "precip_mm": d.get("precip", ""),
                "pressure_hpa": d.get("pressure", ""),
                "vis_km": d.get("vis", ""),
                "uv_index": d.get("uvIndex", ""),
                "sunrise": d.get("sunrise", ""),
                "sunset": d.get("sunset", ""),
                "moon_phase": d.get("moonPhase", ""),
            })
        first = forecast[0] if forecast else {}
        return {
            "success": True,
            "city": loc_name,
            "adm": loc_adm,
            "days": days,
            "forecast": forecast,
            "update_time": data.get("updateTime", ""),
            "summary": f"和风天气：{loc_name} {days}天预报 {first.get('temp_min_c', '?')}~{first.get('temp_max_c', '?')}°C",
        }
    if isinstance(data, dict) and not data.get("success"):
        data["summary"] = data.get("summary", f"和风天气：{data.get('error', 'API异常')}")
        return data
    return {"success": False, "error": f"API 异常: {data}", "summary": "和风天气：API异常"}
