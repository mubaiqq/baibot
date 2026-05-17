import requests


def _decode(raw: bytes) -> str:
    for enc in ("utf-8", "gbk", "gb2312", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def fetch_url(url: str):
    """
    获取网页内容，自动识别中文编码
    """

    try:
        response = requests.get(url, timeout=10)
        raw = response.content
        text = _decode(raw)

        return {
            "success": True,
            "content": text[:1000]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
