"""
跨平台文件打开工具
  Windows: os.startfile
  Linux:   xdg-open
  macOS:   open
"""
import os
import subprocess
import sys
import platform


def _resolve(path: str) -> str:
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    return os.path.normpath(path)


def _resolve_desktop(filename: str) -> str:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.name == "nt":
        for d in ["Desktop", "桌面"]:
            p = os.path.join(os.path.expanduser("~"), d)
            if os.path.isdir(p):
                desktop = p
                break
    return os.path.join(desktop, filename)


def open_file(path: str = "", filename: str = ""):
    """
    用系统默认程序打开文件（跨平台 Windows/Linux/macOS）。

    参数:
      path: 完整路径，如 ~/Desktop/1.txt、C:\\Users\\...
      filename: 纯文件名，如 1.txt，自动在当前目录/桌面查找
    """

    try:
        if filename and not path:
            # 优先当前目录 → 桌面
            cur = _resolve(filename)
            if os.path.isfile(cur):
                path = cur
            else:
                path = _resolve_desktop(filename)

        if not path:
            return {
                "success": False,
                "error": "未提供路径或文件名",
            }

        path = _resolve(path)

        if not os.path.exists(path):
            return {
                "success": False,
                "error": f"文件不存在: {path}",
                "path": path,
            }

        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

        return {
            "success": True,
            "path": path,
            "summary": f"已打开文件: {os.path.basename(path)}",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)[:200],
        }
