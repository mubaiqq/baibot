from .calculator import calculator
from .web_search import web_search
from .fetch_url import fetch_url
from .time_tool import get_current_time
from .system_info import get_system_info
from .weather import get_weather_by_ip, get_weather_forecast, get_local_weather_forecast
from .qweather import get_qweather_now, get_qweather_forecast
from .shell_exec import shell_exec
from .gui_action import gui_action
from .open_file import open_file
from .write_file import write_file

TOOLS_MAP = {
    "calculator": calculator,
    "web_search": web_search,
    "fetch_url": fetch_url,
    "get_current_time": get_current_time,
    "get_system_info": get_system_info,
    "get_weather_by_ip": get_weather_by_ip,
    "get_weather_forecast": get_weather_forecast,
    "get_local_weather_forecast": get_local_weather_forecast,
    "get_qweather_now": get_qweather_now,
    "get_qweather_forecast": get_qweather_forecast,
    "shell_exec": shell_exec,
    "gui_action": gui_action,
    "open_file": open_file,
    "write_file": write_file,
}

TOOL_CONFIG_SCHEMAS = {}
TOOL_APPLY_CONFIG = {}

for _name, _fn in TOOLS_MAP.items():
    _mod = __import__(_fn.__module__, fromlist=["CONFIG_SCHEMA", "apply_config"])
    if hasattr(_mod, "CONFIG_SCHEMA") and _mod.CONFIG_SCHEMA:
        TOOL_CONFIG_SCHEMAS[_name] = _mod.CONFIG_SCHEMA
    if hasattr(_mod, "apply_config"):
        TOOL_APPLY_CONFIG[_name] = _mod.apply_config

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "数学计算工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索互联网信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "获取网页内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "网页地址"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前日期和时间，包括日期、时间、星期几",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "时区（目前仅支持 local）"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "获取当前运行环境的详细系统信息，包括操作系统、Python版本、CPU型号、内存占用、显卡等",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_by_ip",
            "description": "根据当前公网IP自动获取当前位置的实时天气。仅适用于“我这里/本地/当前位置/现在”的天气；指定城市或未来预报请使用 get_weather_forecast。返回城市、温度、天气状态、湿度、风力等结构化数据",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "查询指定城市的天气预报，适用于杭州明天、北京后天、上海未来天气等指定地点/日期问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 杭州、北京、上海"},
                    "day": {"type": "string", "enum": ["today", "tomorrow", "after_tomorrow"], "description": "查询日期"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_local_weather_forecast",
            "description": "根据当前公网IP定位城市，再查询本地今天、明天或后天的天气预报。适用于“我这里明天天气”。",
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {"type": "string", "enum": ["today", "tomorrow", "after_tomorrow"], "description": "查询日期"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_qweather_now",
            "description": "【优先】和风天气实时天气。查询指定城市的实时天气，包括温度、体感温度、风力风向、湿度、气压、降水量、能见度等。支持中文城市名，数据5-20分钟更新一次。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 北京、杭州、深圳。留空则自动IP定位"},
                    "location": {"type": "string", "description": "LocationID 或 经度,纬度，优先于 city"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_qweather_forecast",
            "description": "【优先】和风天气每日预报。查询指定城市未来3/7/10/15/30天天气预报，包括最高最低温度、白天夜间天气、风力风向、湿度、降水量、紫外线、日出日落等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 北京、杭州"},
                    "location": {"type": "string", "description": "LocationID 或 经度,纬度，优先于 city"},
                    "days": {"type": "string", "enum": ["3", "7", "10", "15", "30"], "description": "预报天数，默认3天"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "shell_exec",
            "description": "在系统上执行命令行操作。Windows 用 PowerShell，Linux 用 bash。可用于查看文件、列出目录、运行脚本、检查进程、管理系统等。创建/修改文本文件优先使用 write_file，不要手写复杂 shell。超时30秒，输出限制2000字符",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 Shell 命令"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "创建或覆盖本地文本文件，适合保存 HTML/CSS/JS/TXT/MD/PY/JSON 等内容。必须严格使用用户指定的文件名和位置；例如用户说 404.html 放桌面，就传 filename='404.html', directory='desktop'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要写入文件的完整文本内容"},
                    "filename": {"type": "string", "description": "文件名，如 404.html、index.html、notes.txt"},
                    "directory": {"type": "string", "enum": ["current", "desktop"], "description": "保存位置：current=当前目录，desktop=桌面"},
                    "path": {"type": "string", "description": "完整路径。提供 path 时优先使用 path，可留空"},
                    "overwrite": {"type": "boolean", "description": "是否覆盖已有文件，默认 true"},
                    "encoding": {"type": "string", "description": "文本编码，默认 utf-8"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_action",
            "description": "执行 GUI 自动化操作：输入文字、按组合键（Ctrl+A 全选等）、点击鼠标、聚焦窗口。所有桌面 GUI 操作请优先使用此工具而非 shell_exec",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["hotkey", "type", "press", "click", "activate_window", "get_position"],
                        "description": "操作类型: hotkey=组合键, type=输入文字, press=按键, click=鼠标点击, activate_window=聚焦窗口"
                    },
                    "text": {"type": "string", "description": "输入的文字内容（action=type 时必填）"},
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "键列表，如 ['ctrl','a']（hotkey/press 时必填）"
                    },
                    "x": {"type": "integer", "description": "点击 X 坐标（click 时必填）"},
                    "y": {"type": "integer", "description": "点击 Y 坐标（click 时必填）"},
                    "title": {"type": "string", "description": "窗口标题关键词（activate_window 时必填）"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_file",
            "description": "用系统默认程序打开文件。当用户说打开文件/文档/图片/PDF/文本等，优先使用此工具。支持纯文件名（自动桌面/当前目录查找）或完整路径",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "完整路径，如 ~/Desktop/1.txt、C:\\Users\\...\\1.txt"},
                    "filename": {"type": "string", "description": "纯文件名，如 1.txt，自动在桌面/当前目录查找"}
                },
                "required": []
            }
        }
    }
]
