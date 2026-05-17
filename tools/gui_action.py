"""
跨平台 GUI 自动化工具（增强稳定性版）
  Windows: pyautogui + pygetwindow
  Linux:   pyautogui + xdotool/wmctrl
"""
import sys
import subprocess
import os
import time

GUI_TIMEOUT = 10


def _paste_text(text: str):
    if sys.platform == "win32":
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "$text = [Console]::In.ReadToEnd(); Set-Clipboard -Value $text"],
            input=text,
            text=True,
            timeout=5,
            check=True,
        )
        return

    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
    except Exception:
        subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, timeout=5, check=True)


def _win_activate(title: str):
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if windows:
            w = windows[0]
            if w.isMinimized:
                w.restore()
            w.activate()
            time.sleep(0.4)
            try:
                active = gw.getActiveWindow()
                if active and title.lower() in (active.title or "").lower():
                    return True, f"已聚焦窗口: {title}"
            except Exception:
                pass
            return True, f"已聚焦窗口: {title}"
        return False, f"未找到包含 '{title}' 的窗口"
    except Exception as e:
        return False, str(e)


def _linux_activate(title: str):
    try:
        subprocess.run(["wmctrl", "-a", title], timeout=5, capture_output=True)
        time.sleep(0.4)
        return True, f"已聚焦窗口: {title}"
    except FileNotFoundError:
        try:
            subprocess.run(
                ["xdotool", "search", "--name", title, "windowactivate"],
                timeout=5, capture_output=True
            )
            time.sleep(0.4)
            return True, f"已聚焦窗口: {title}"
        except Exception:
            return False, "需要安装 wmctrl 或 xdotool"
    except Exception as e:
        return False, str(e)


def _verify_window_exists(title: str) -> bool:
    try:
        if sys.platform == "win32":
            import pygetwindow as gw
            return len(gw.getWindowsWithTitle(title)) > 0
        else:
            r = subprocess.run(["xdotool", "search", "--name", title],
                               capture_output=True, timeout=3)
            return len(r.stdout.strip()) > 0
    except Exception:
        return True


def gui_action(
    action: str,
    text: str = "",
    keys: list = None,
    x: int = 0,
    y: int = 0,
    title: str = "",
):
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

        if action == "activate_window":
            if not title:
                return {"success": False, "error": "activate_window 需要 title 参数"}
            if sys.platform == "win32":
                ok, msg = _win_activate(title)
            else:
                ok, msg = _linux_activate(title)
            if ok:
                return {"success": True, "summary": msg, "active_window": title}
            return {"success": False, "error": msg}

        elif action == "hotkey":
            if not keys or len(keys) < 2:
                return {"success": False, "error": "hotkey 需要至少 2 个键"}
            pyautogui.hotkey(*keys)
            time.sleep(0.2)
            return {
                "success": True,
                "summary": f"已按下组合键: {'+'.join(keys)}",
            }

        elif action == "type":
            if not text:
                return {"success": False, "error": "type 需要 text 参数"}
            if any(ord(ch) > 127 for ch in text) or "\n" in text:
                _paste_text(text)
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.typewrite(text, interval=0.03)
            time.sleep(0.1)
            return {
                "success": True,
                "summary": f"已输入: {text[:60]}",
            }

        elif action == "press":
            if not keys:
                return {"success": False, "error": "press 需要 keys 参数"}
            for k in keys:
                pyautogui.press(k)
                time.sleep(0.05)
            return {
                "success": True,
                "summary": f"已按下: {', '.join(keys)}",
            }

        elif action == "click":
            if x <= 0 and y <= 0:
                return {"success": False, "error": "click 需要有效的 x, y 坐标"}
            pyautogui.click(x, y)
            time.sleep(0.1)
            return {
                "success": True,
                "summary": f"已点击 ({x}, {y})",
            }

        elif action == "get_position":
            pos = pyautogui.position()
            return {
                "success": True,
                "summary": f"鼠标位置: ({pos.x}, {pos.y})",
                "x": pos.x,
                "y": pos.y,
            }

        else:
            return {
                "success": False,
                "error": f"未知 action: {action}"
            }

    except ImportError:
        return {"success": False, "error": "pyautogui 未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}
