"""
API 提供商配置 — 每个提供商可包含多个模型
"""
import json
import os
from openai import OpenAI

PROVIDERS = [
    {
        "name": "算力岛",
        "base_url": "https://api.mytokenland.com/v1",
        "api_key": "sk-your-key-here",
        "models": [
            "claude-sonnet-4-6",
            "claude-sonnet-4-5",
            "claude-opus-4-1",
            "gpt-4.1",
            "gpt-4o",
            "mimo-v2-omni",
            "deepseek-chat",
            "qwen-max",
        ],
    },
        {
        "name": "小米mimo",
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
        "api_key": "tp-your-key-here",
        "models": [
            "mimo-v2.5-pro",
            "mimo-v2-pro",
             "mimo-v2-omni",
            "mimo-v2.5",
        ],
    },
    {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-your-key-here",
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
        ],
    },
    {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-your-key-here",
        "models": [
            "deepseek-v4-pro",
            "deepseek-v4-flash",
        ],
    },
    {
        "name": "Ollama",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "models": [
            "llama3",
            "qwen2.5",
            "mistral",
        ],
    },
]

DEFAULT_PROVIDER = "MyTokenLand"
DEFAULT_MODEL = "claude-sonnet-4-6"


def get_client(provider_name: str | None = None) -> OpenAI:
    p = None
    for provider in PROVIDERS:
        if provider["name"] == (provider_name or DEFAULT_PROVIDER):
            p = provider
            break
    if not p:
        p = PROVIDERS[0]

    return OpenAI(api_key=p["api_key"], base_url=p["base_url"])


def get_provider(provider_name: str) -> dict | None:
    for p in PROVIDERS:
        if p["name"] == provider_name:
            return p
    return None


def list_all_models() -> list[str]:
    result = []
    for p in PROVIDERS:
        for m in p["models"]:
            label = f"{p['name']}/{m}"
            if p["name"] == DEFAULT_PROVIDER and m == DEFAULT_MODEL:
                label += " ★"
            result.append(label)
    return result


def find_model(model_key: str) -> tuple[str, str, dict] | None:
    """根据模型名或 'provider/model' 查找，返回 (provider_name, model, provider_dict)"""
    if "/" in model_key:
        provider_name, model = model_key.split("/", 1)
        p = get_provider(provider_name)
        if p and model in p["models"]:
            return provider_name, model, p
    for p in PROVIDERS:
        if model_key in p["models"]:
            return p["name"], model_key, p
    return None


_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def save_config():
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "providers": PROVIDERS,
            "default_provider": DEFAULT_PROVIDER,
            "default_model": DEFAULT_MODEL,
        }, f, ensure_ascii=False, indent=2)


def _load_config():
    if not os.path.exists(_CONFIG_PATH):
        return
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "providers" in data and isinstance(data["providers"], list) and data["providers"]:
            PROVIDERS[:] = data["providers"]
        if "default_provider" in data:
            globals()["DEFAULT_PROVIDER"] = data["default_provider"]
        if "default_model" in data:
            globals()["DEFAULT_MODEL"] = data["default_model"]
    except Exception:
        pass


_load_config()
