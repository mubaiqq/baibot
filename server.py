import sys
import io
import json
import queue
import threading
import os
import traceback
from flask import Flask, request, Response, send_file
from flask_cors import CORS

app = Flask(__name__, static_folder=".")
CORS(app)

AGENT_INSTANCE = None

_PLUGIN_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin_config.json")


def _load_plugin_config():
    if not os.path.exists(_PLUGIN_CONFIG_PATH):
        return
    try:
        with open(_PLUGIN_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        from tools import TOOL_APPLY_CONFIG
        for name, cfg in data.items():
            if name in TOOL_APPLY_CONFIG:
                TOOL_APPLY_CONFIG[name](cfg)
    except Exception:
        pass


def _save_plugin_config():
    from tools import TOOL_CONFIG_SCHEMAS
    import importlib
    data = {}
    for name, schema in TOOL_CONFIG_SCHEMAS.items():
        mod = importlib.import_module("tools." + name)
        entry = {}
        for key in schema:
            entry[key] = getattr(mod, key, "")
        data[name] = entry
    with open(_PLUGIN_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


_load_plugin_config()


def get_agent():
    global AGENT_INSTANCE
    if AGENT_INSTANCE is None:
        from agent import Agent
        AGENT_INSTANCE = Agent()
    return AGENT_INSTANCE


class StreamOutput:
    def __init__(self, q: queue.Queue):
        self.q = q
        self._buffer = ""

    def emit(self, event_type: str, data: str):
        self.q.put((event_type, data))

    def write(self, text: str):
        if not text:
            return
        self._buffer += text
        while "\n" in self._buffer:
            idx = self._buffer.index("\n")
            line = self._buffer[:idx]
            self._buffer = self._buffer[idx + 1:]
            if line.strip():
                self.q.put(("process", line))

    def flush(self):
        if self._buffer.strip():
            self.q.put(("process", self._buffer))
            self._buffer = ""


@app.route("/")
def index():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui.html")
    return send_file(html_path)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return Response("data: " + json.dumps({"type": "error", "data": "无效请求"}) + "\n\n",
                        mimetype="text/event-stream")

    user_input = data.get("message", "").strip()
    if not user_input:
        return Response("data: " + json.dumps({"type": "error", "data": "请输入消息"}) + "\n\n",
                        mimetype="text/event-stream")

    def generate():
        q = queue.Queue()
        stream = StreamOutput(q)
        old_stdout = sys.stdout

        def run_agent():
            try:
                agent = get_agent()
                sys.stdout = stream

                if user_input.startswith("/"):
                    from main import handle_command
                    old = sys.stdout
                    cap = io.StringIO()
                    sys.stdout = cap
                    should_exit = handle_command(user_input.strip(), agent)
                    sys.stdout = old
                    output = cap.getvalue()
                    if should_exit:
                        q.put(("result", "退出指令不可在 WebUI 使用"))
                    elif output.strip():
                        for line in output.strip().split("\n"):
                            if line.strip():
                                q.put(("result", line))
                else:
                    agent.run(user_input, stream)

            except Exception:
                q.put(("error", traceback.format_exc()))
            finally:
                sys.stdout = old_stdout
                stream.flush()
                q.put(("done", ""))

        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        while True:
            try:
                event_type, data_str = q.get(timeout=120)
                if event_type == "done":
                    yield "data: " + json.dumps({"type": "done"}, ensure_ascii=False) + "\n\n"
                    break
                if event_type == "error":
                    yield "data: " + json.dumps({"type": "error", "data": data_str}, ensure_ascii=False) + "\n\n"
                    break
                yield "data: " + json.dumps({"type": event_type, "data": data_str}, ensure_ascii=False) + "\n\n"
            except queue.Empty:
                sys.stdout = old_stdout
                yield "data: " + json.dumps({"type": "error", "data": "请求超时，请重试"}, ensure_ascii=False) + "\n\n"
                break

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/command", methods=["POST"])
def command():
    data = request.get_json()
    if not data:
        return {"ok": False, "error": "无效请求"}, 400

    cmd = data.get("command", "").strip()
    if not cmd:
        return {"ok": False, "error": "空命令"}, 400

    agent = get_agent()

    if cmd == "/new":
        agent.reset_session()
        from memory import ensure_session
        sid = ensure_session()
        return {"ok": True, "message": "新会话已创建", "session": sid}

    if cmd == "/session":
        from memory import get_session_summary
        return {"ok": True, "message": get_session_summary()}

    if cmd.startswith("/model"):
        parts = cmd.split(maxsplit=1)
        if len(parts) > 1:
            arg = parts[1].strip()
            from api_providers import find_model
            from config import apply_model
            found = find_model(arg)
            if found:
                pname, model, _ = found
                apply_model(pname, model)
                agent.reload_prompt()
                return {"ok": True, "message": f"已切换到 {pname}/{model}"}
            else:
                return {"ok": False, "error": f"未找到模型 '{arg}'"}
        else:
            from config import CONFIG
            return {"ok": True, "message": f"当前模型: {CONFIG['provider']}/{CONFIG['model']}"}

    if cmd == "/models":
        from api_providers import list_all_models
        return {"ok": True, "models": list_all_models()}

    return {"ok": False, "error": f"未知命令: {cmd}"}


@app.route("/settings")
def settings():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.html")
    return send_file(html_path)


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    from config import CONFIG
    return {"ok": True, "config": {
        "agent_name": CONFIG.get("agent_name", ""),
        "provider": CONFIG.get("provider", ""),
        "model": CONFIG.get("model", ""),
        "max_steps": CONFIG.get("max_steps", 10),
        "temperature": CONFIG.get("temperature", 0.2),
    }}


@app.route("/api/models", methods=["GET", "POST"])
def api_models():
    from api_providers import PROVIDERS
    from config import CONFIG
    result = []
    current_provider = CONFIG.get("provider", "")
    current_model = CONFIG.get("model", "")
    for p in PROVIDERS:
        for m in p["models"]:
            value = f"{p['name']}/{m}"
            result.append({
                "value": value,
                "label": f"{p['name']} / {m}",
                "selected": (p["name"] == current_provider and m == current_model),
            })
    return {"ok": True, "models": result}


@app.route("/api/set-model", methods=["POST"])
def api_set_model():
    from api_providers import find_model
    from config import apply_model
    data = request.get_json() or {}
    val = data.get("model", "").strip()
    if not val:
        return {"ok": False, "error": "缺少 model 参数"}
    found = find_model(val)
    if not found:
        return {"ok": False, "error": f"未找到模型 '{val}'"}
    pname, model, _ = found
    apply_model(pname, model)
    agent = get_agent()
    agent.reload_prompt()
    return {"ok": True, "message": f"已切换到 {pname}/{model}"}


@app.route("/api/providers", methods=["GET", "POST"])
def api_providers():
    import api_providers as ap

    data = request.get_json(silent=True) or {}
    if request.method == "GET" or "providers" not in data:
        return {"ok": True, "providers": ap.PROVIDERS,
                "default_provider": ap.DEFAULT_PROVIDER, "default_model": ap.DEFAULT_MODEL}

    new_providers = data.get("providers")
    if not isinstance(new_providers, list) or not new_providers:
        return {"ok": False, "error": "providers 必须是非空数组"}

    old_providers = ap.PROVIDERS[:]
    old_dp = ap.DEFAULT_PROVIDER
    old_dm = ap.DEFAULT_MODEL
    try:
        ap.PROVIDERS[:] = new_providers
        if data.get("default_provider"):
            ap.DEFAULT_PROVIDER = data["default_provider"]
        if data.get("default_model"):
            ap.DEFAULT_MODEL = data["default_model"]

        from config import CONFIG, apply_model
        dp = ap.DEFAULT_PROVIDER
        dm = ap.DEFAULT_MODEL
        provider_found = any(p["name"] == dp for p in new_providers)
        model_in_provider = False
        if provider_found:
            for p in new_providers:
                if p["name"] == dp and dm in p["models"]:
                    model_in_provider = True
                    break

        if not provider_found or not model_in_provider:
            first = new_providers[0]
            dp = first["name"]
            dm = first["models"][0]
            ap.DEFAULT_PROVIDER = dp
            ap.DEFAULT_MODEL = dm

        apply_model(dp, dm)
        agent = get_agent()
        agent.reload_prompt()

        ap.save_config()
        return {"ok": True, "message": "配置已保存", "default_provider": dp, "default_model": dm}
    except Exception as e:
        ap.PROVIDERS[:] = old_providers
        ap.DEFAULT_PROVIDER = old_dp
        ap.DEFAULT_MODEL = old_dm
        return {"ok": False, "error": f"保存失败: {e}"}


@app.route("/api/tools", methods=["GET", "POST"])
def api_tools():
    from tools import TOOLS
    result = []
    for t in TOOLS:
        fn = t.get("function", {})
        result.append({
            "name": fn.get("name", "unknown"),
            "type": fn.get("description", ""),
        })
    return {"ok": True, "tools": result}


@app.route("/api/set-config", methods=["POST"])
def api_set_config():
    from config import CONFIG, apply_model, save_app_config
    from api_providers import find_model
    data = request.get_json() or {}
    if "agent_name" in data:
        CONFIG["agent_name"] = data["agent_name"]
    if "max_steps" in data:
        CONFIG["max_steps"] = int(data["max_steps"])
    if "temperature" in data:
        CONFIG["temperature"] = float(data["temperature"])
    if "agent_name" in data or "max_steps" in data or "temperature" in data:
        save_app_config()
    model_error = None
    if "model" in data:
        val = data["model"].strip()
        if val:
            found = find_model(val)
            if found:
                pname, model, _ = found
                apply_model(pname, model)
                agent = get_agent()
                agent.reload_prompt()
            else:
                model_error = f"未找到模型 '{val}'"
    import config as _c
    bu = str(_c.client.base_url) if hasattr(_c.client, 'base_url') else "?"
    resp = {"ok": True, "message": "配置已更新",
            "applied_provider": CONFIG.get("provider"),
            "applied_model": CONFIG.get("model"),
            "applied_base_url": bu}
    if model_error:
        resp["ok"] = False
        resp["error"] = model_error
    return resp


@app.route("/api/debug-client", methods=["GET"])
def api_debug_client():
    import config as _c
    import api_providers as ap
    bu = "?"
    key_masked = "?"
    try:
        bu = str(_c.client.base_url)
    except Exception:
        pass
    try:
        k = str(_c.client.api_key)
        key_masked = k[:6] + "..." + k[-4:] if len(k) > 10 else k[:3] + "..."
    except Exception:
        pass
    return {"ok": True,
            "config_provider": _c.CONFIG.get("provider"),
            "config_model": _c.CONFIG.get("model"),
            "client_base_url": bu,
            "client_api_key_masked": key_masked,
            "default_provider": ap.DEFAULT_PROVIDER,
            "default_model": ap.DEFAULT_MODEL,
            "providers_list": [p["name"] for p in ap.PROVIDERS]}


@app.route("/api/set-default-model", methods=["POST"])
def api_set_default_model():
    from api_providers import find_model
    import api_providers as ap
    from config import apply_model
    data = request.get_json() or {}
    val = data.get("model", "").strip()
    if not val:
        return {"ok": False, "error": "缺少 model 参数"}
    found = find_model(val)
    if not found:
        return {"ok": False, "error": f"未找到模型 '{val}'"}
    pname, model, _ = found
    ap.DEFAULT_PROVIDER = pname
    ap.DEFAULT_MODEL = model
    ap.save_config()
    apply_model(pname, model)
    agent = get_agent()
    agent.reload_prompt()
    from config import CONFIG
    return {"ok": True, "message": f"默认模型已设为 {pname}/{model}",
            "default_provider": pname, "default_model": model,
            "applied_provider": CONFIG.get("provider"), "applied_model": CONFIG.get("model")}


@app.route("/api/plugin-config", methods=["GET", "POST"])
def api_plugin_config():
    from tools import TOOL_CONFIG_SCHEMAS, TOOL_APPLY_CONFIG
    import importlib

    data = request.get_json(silent=True) or {}
    if request.method == "GET" or not data.get("plugin"):
        result = {}
        for name, schema in TOOL_CONFIG_SCHEMAS.items():
            try:
                mod = importlib.import_module("tools." + name)
            except Exception:
                continue
            fields = {}
            for key, field in schema.items():
                fields[key] = {
                    "label": field["label"],
                    "type": field.get("type", "text"),
                    "description": field.get("description", ""),
                    "value": getattr(mod, key, ""),
                }
            result[name] = {"name": name, "fields": fields}
        return {"ok": True, "plugins": result}

    plugin_name = data.get("plugin", "").strip()
    fields = data.get("fields") or {}
    if not plugin_name:
        return {"ok": False, "error": "缺少 plugin 参数"}
    if plugin_name not in TOOL_APPLY_CONFIG:
        return {"ok": False, "error": f"插件 '{plugin_name}' 不支持配置"}
    TOOL_APPLY_CONFIG[plugin_name](fields)
    _save_plugin_config()
    return {"ok": True, "message": "配置已保存"}


@app.route("/api/fetch-models", methods=["POST"])
def api_fetch_models():
    """从 OpenAI 兼容地址获取模型列表"""
    data = request.get_json() or {}
    base_url = (data.get("base_url") or "").strip()
    api_key = (data.get("api_key") or "").strip()
    if not base_url:
        return {"ok": False, "error": "请输入提供商地址"}
    if not api_key:
        return {"ok": False, "error": "请输入密钥"}
    try:
        from openai import OpenAI
        c = OpenAI(api_key=api_key, base_url=base_url)
        resp = c.models.list()
        models = [m.id for m in resp]
        models.sort()
        return {"ok": True, "models": models}
    except Exception as e:
        return {"ok": False, "error": f"获取模型列表失败: {e}"}


@app.route("/api/add-provider", methods=["POST"])
def api_add_provider():
    """添加一个新的 API 提供商"""
    import api_providers as ap
    from config import CONFIG, apply_model
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    base_url = (data.get("base_url") or "").strip()
    api_key = (data.get("api_key") or "").strip()
    models = data.get("models") or []
    if not name:
        return {"ok": False, "error": "请输入提供商名称"}
    if not base_url:
        return {"ok": False, "error": "请输入提供商地址"}
    if not api_key:
        return {"ok": False, "error": "请输入密钥"}
    if not isinstance(models, list) or len(models) == 0:
        return {"ok": False, "error": "请至少添加一个模型（可点击'一键获取模型'）"}
    for p in ap.PROVIDERS:
        if p["name"] == name:
            return {"ok": False, "error": f"提供商 '{name}' 已存在，请使用其他名称"}
    new_provider = {
        "name": name,
        "base_url": base_url,
        "api_key": api_key,
        "models": models,
    }
    ap.PROVIDERS.append(new_provider)
    ap.save_config()
    return {"ok": True, "message": f"已添加提供商 '{name}'（{len(models)} 个模型）"}


if __name__ == "__main__":
    print("baibot API 服务启动")
    print("WebUI 地址: http://localhost:7200")
    print("API 地址: POST http://localhost:7200/api/chat")
    app.run(host="0.0.0.0", port=7200, debug=False, threaded=True)
