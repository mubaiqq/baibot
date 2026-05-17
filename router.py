"""
意图路由器 — 规则级 Intent Detection
  用户输入 → 关键词匹配 → 返回强制 tool 调用列表
  先规则后 LLM，确保桌面操作必被路由
"""
import sys
import json
from typing import Optional, List


# =========================================================
# Intent patterns → (tool_name, tool_args)
# =========================================================

ROUTES: List[tuple] = [
    # ── 关闭程序 ──
    ("关闭程序", ["关闭", "kill", "结束", "退出", "杀掉", "停止"], lambda t: (
        "shell_exec",
        {"command": _kill_cmd(t)}
    )),

    # ── 打开文件 ──
    ("打开文件", ["打开", "open", "启动", "查看"], lambda t: (
        "open_file",
        {"filename": _extract_filename(t)}
    )),

    # ── 查看进程 ──
    ("查看进程", ["进程", "任务管理器", "任务列表", "ps", "tasklist"], lambda t: (
        "shell_exec",
        {"command": "Get-Process | Select-Object Id,ProcessName | Format-Table -AutoSize" if sys.platform == "win32" else "ps aux --sort=-%mem | head -20"}
    )),

    # ── 全选 ──
    ("全选", ["全选", "ctrl+a", "ctrl a", "^a", "^A", "ctrl-a"], lambda t: (
        "gui_action",
        {"action": "hotkey", "keys": ["ctrl", "a"]}
    )),

    # ── 保存 ──
    ("保存", ["保存", "ctrl+s", "ctrl s", "ctrl-s", "save", "存盘"], lambda t: (
        "gui_action",
        {"action": "hotkey", "keys": ["ctrl", "s"]}
    )),

    # ── 输入/写入文字 ──
    ("输入文字", ["输入", "写入", "键入", "填入", "填上", "改成", "改为", "替换成", "修改为", "修改成"], lambda t: (
        "gui_action",
        {"action": "type", "text": _extract_input_text(t)}
    )),

    # ── 关闭窗口 ──
    ("关闭窗口", ["关闭窗口", "alt+f4", "alt f4", "alt-f4", "关闭当前窗口", "关闭这个窗口"], lambda t: (
        "gui_action",
        {"action": "hotkey", "keys": ["alt", "f4"]}
    )),

    # ── 回车/确认 ──
    ("回车", ["回车", "enter", "确认", "换行"], lambda t: (
        "gui_action",
        {"action": "press", "keys": ["enter"]}
    )),

    # ── 粘贴 ──
    ("粘贴", ["粘贴", "ctrl+v", "ctrl v", "ctrl-v", "paste"], lambda t: (
        "gui_action",
        {"action": "hotkey", "keys": ["ctrl", "v"]}
    )),

    # ── 复制 ──
    ("复制", ["复制", "ctrl+c", "ctrl c", "ctrl-c", "copy"], lambda t: (
        "gui_action",
        {"action": "hotkey", "keys": ["ctrl", "c"]}
    )),
]


def _kill_cmd(text: str) -> str:
    """根据文本提取要关闭的程序名，返回跨平台命令"""
    lower = text.lower()
    if "记事本" in text or "notepad" in lower:
        name = "notepad"
    elif "浏览器" in text or "chrome" in lower:
        name = "chrome"
    elif "edge" in lower:
        name = "msedge"
    elif "firefox" in lower or "火狐" in text:
        name = "firefox"
    elif "计算器" in text or "calc" in lower:
        name = "Calculator"
    elif "explorer" in lower or "资源管理器" in text:
        name = "explorer"
    elif "cmd" in lower or "终端" in text or "命令提示符" in text:
        name = "cmd"
    elif "vscode" in lower or "vs code" in lower or "code" in lower:
        name = "Code"
    elif "word" in lower:
        name = "WINWORD"
    elif "excel" in lower:
        name = "EXCEL"
    else:
        return "taskkill /f /im notepad.exe" if sys.platform == "win32" else "pkill -f notepad"

    if sys.platform == "win32":
        return f"taskkill /f /im {name}.exe" if "." not in name else f"taskkill /f /im {name}"
    return f"pkill -f {name}"


def _extract_filename(text: str) -> str:
    """从文本提取文件名"""
    import re

    # 1. 引号内优先
    m = re.search(r'["\']([^"\']+\.\w{2,5})["\']', text)
    if m:
        return m.group(1).strip()

    # 2. 锚定 "打开" 之后的内容
    for kw in ["打开", "open"]:
        idx = text.lower().find(kw)
        if idx >= 0:
            text = text[idx + len(kw):]
            break

    # 3. 优先匹配纯英文/数字文件名（如 1.txt, report.pdf），不受中文干扰
    m = re.search(r'([a-zA-Z0-9_\-.]{1,40}\.\w{2,5})', text)
    if m:
        return m.group(1)

    # 4. 匹配含中文的文件名（限制前缀长度避免贪婪吞入修饰词）
    m = re.search(r'([\w\u4e00-\u9fff\-_.]{1,12}\.\w{2,5})', text)
    if m:
        candidate = m.group(1)
        # 去掉明显是修饰词的前缀（如 "桌面的" → "报告.txt"）
        return _trim_modifier(candidate)

    return ""


def _trim_modifier(filename: str) -> str:
    """去掉中文修饰词前缀（如 桌面的报告.txt → 报告.txt）"""
    import re
    m = re.match(r'(?:桌面上的?|文件夹里的?|目录下的?|这里的?|那个的?|这个的?|我的的?)(.*)', filename)
    if m:
        return m.group(1)
    return filename


def _extract_input_text(text: str) -> str:
    """从文本提取要输入的内容"""
    import re
    keywords = ["输入", "写入", "键入", "填入", "填上", "改成", "改为", "替换成", "修改为", "修改成"]
    sorted_kw = sorted(keywords, key=len, reverse=True)
    for kw in sorted_kw:
        idx = text.find(kw)
        if idx >= 0:
            after = text[idx + len(kw):].strip()
            if after.startswith("：") or after.startswith(":"):
                after = after[1:].strip()
            # remove trailing punctuation
            after = re.sub(r'[。，！？,!?;；\s]+$', '', after)
            if len(after) >= 1 and len(after) < 500:
                return _expand_vague_input_text(text, after)
            break
    return text


def _expand_vague_input_text(original: str, extracted: str) -> str:
    """把“随便输入一首诗”这类模糊内容展开成可实际输入的文本。"""
    vague = any(k in original for k in ["随便", "任意", "帮我", "写一"])
    if vague and extracted in {"一首诗", "首诗", "诗"}:
        return "春风拂过旧窗台，\n一缕清光入梦来。\n若问人间何处好，\n半杯热茶伴花开。"
    if vague and extracted in {"一段话", "段话", "一些文字", "文字"}:
        return "愿今天的事情都慢慢变好，窗外有风，手边有光，心里也有一点安静的力量。"
    return extracted


def detect(user_input: str) -> Optional[List[dict]]:
    """
    检测用户输入，返回要强制执行的 tool 调用列表。
    返回 None 表示不匹配任何路由，交给 LLM 处理。
    """
    if _looks_like_file_creation_task(user_input):
        return None

    results = []

    for name, keywords, builder in ROUTES:
        for kw in keywords:
            if kw.lower() in user_input.lower():
                tool_name, tool_args = builder(user_input)
                if not tool_args:
                    continue
                if tool_name == "open_file" and not (tool_args.get("path") or tool_args.get("filename")):
                    continue
                # 去重：不重复添加相同 tool
                sig = f"{tool_name}|{json.dumps(tool_args, sort_keys=True, ensure_ascii=False)}"
                if not any(
                    f"{r['name']}|{json.dumps(r['args'], sort_keys=True, ensure_ascii=False)}" == sig
                    for r in results
                ):
                    results.append({"name": tool_name, "args": tool_args})
                break

    if not results:
        return None

    # 如果有关闭程序+关闭窗口同时命中，只保留关闭程序（更直接）
    names = [r["name"] for r in results]
    if "shell_exec" in names and "gui_action" in names:
        has_kill = any(r["name"] == "shell_exec" and "taskkill" in str(r["args"]) for r in results)
        has_altf4 = any(r["name"] == "gui_action" and r["args"].get("action") == "hotkey" and "alt" in str(r["args"]) for r in results)
        if has_kill and has_altf4:
            results = [r for r in results if not (r["name"] == "gui_action" and "alt" in str(r["args"]))]

    # 多步骤复杂任务 → 交给 LLM
    # 同时命中"打开"+"关闭" 或 "打开"+"输入"+"关闭" 等组合时，router 无法保证顺序
    route_names = set(r[0] for r in ROUTES if any(
        kw.lower() in user_input.lower() for kw in r[1]
    ))
    complex_combos = [
        {"打开文件", "关闭程序"},
        {"打开文件", "输入文字"},
        {"打开文件", "关闭窗口"},
        {"关闭程序", "输入文字"},
    ]
    for combo in complex_combos:
        if combo.issubset(route_names):
            return None

    return results


def _looks_like_file_creation_task(text: str) -> bool:
    """创建/生成文件类任务需要规划内容和路径，不能被“保存”热键路由截走。"""
    import re
    create_words = ["写", "创建", "新建", "生成", "做一个", "制作"]
    file_words = ["html", "网页", "文件", ".txt", ".md", ".py", ".json", ".css", ".js"]
    save_target_words = ["保存到", "保存为", "保存成", "放到", "桌面"]
    has_filename = bool(re.search(r'[\w\u4e00-\u9fff\-]+?\.(?:html?|txt|md|py|json|css|js)', text, re.IGNORECASE))
    if has_filename and any(w in text for w in ["保存到", "保存为", "保存成", "命名为", "改成", "叫"]):
        return True
    return (
        any(w in text.lower() for w in file_words)
        and any(w in text for w in create_words)
        and any(w in text for w in save_target_words)
    )
