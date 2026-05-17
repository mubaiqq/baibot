from tavily import TavilyClient

TAVILY_API_KEY = "tvly-your-key-here"

_tavily = TavilyClient(api_key=TAVILY_API_KEY)

CONFIG_SCHEMA = {
    "TAVILY_API_KEY": {
        "label": "Tavily API Key",
        "type": "password",
        "description": "用于联网搜索的 Tavily API 密钥，前往 tavily.com 获取",
        "default": "",
    }
}


def apply_config(config: dict):
    global TAVILY_API_KEY, _tavily
    if "TAVILY_API_KEY" in config and config["TAVILY_API_KEY"]:
        TAVILY_API_KEY = config["TAVILY_API_KEY"]
        _tavily = TavilyClient(api_key=TAVILY_API_KEY)


def web_search(query: str):
    """
    使用 Tavily Search API 进行高质量网页搜索
    """

    try:
        response = _tavily.search(query, max_results=8)

        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("content", ""),
                "url": item.get("url", "")
            })

        if not results:
            results.append({
                "title": "未找到结果",
                "snippet": f"未找到与 '{query}' 相关的结果",
                "url": ""
            })

        return {
            "success": True,
            "results": results[:8]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)[:200]
        }
