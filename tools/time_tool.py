from datetime import datetime


def get_current_time(timezone: str = "local"):
    """
    获取当前日期和时间
    跨平台兼容：纯 Python datetime，Win/Linux 通用
    """

    now = datetime.now()

    return {
        "success": True,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "iso": now.isoformat()
    }
