"""
Write text content to a local file.
"""
import os
from typing import Dict, Any


def _desktop_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Desktop")


def _resolve_path(
    filename: str = "",
    directory: str = "current",
    path: str = "",
) -> str:
    if path:
        return os.path.abspath(os.path.expanduser(path))

    filename = (filename or "").strip()
    if not filename:
        raise ValueError("未提供文件名或路径")

    filename = os.path.basename(filename)
    if directory == "desktop":
        return os.path.join(_desktop_dir(), filename)
    return os.path.join(os.getcwd(), filename)


def write_file(
    content: str,
    filename: str = "",
    directory: str = "current",
    path: str = "",
    overwrite: bool = True,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """
    Write text content to a file.

    Use filename + directory for common cases, or path for an exact full path.
    """
    try:
        target = _resolve_path(filename=filename, directory=directory, path=path)

        if os.path.exists(target) and not overwrite:
            return {
                "success": False,
                "error": f"文件已存在: {target}",
                "path": target,
            }

        parent = os.path.dirname(target)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(target, "w", encoding=encoding, newline="\n") as f:
            f.write(content or "")

        return {
            "success": True,
            "path": target,
            "bytes": os.path.getsize(target),
            "summary": f"已保存文件: {target}",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)[:300],
        }
