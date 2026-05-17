"""
跨平台 Shell 命令执行工具
Windows -> PowerShell
Linux   -> bash
"""

import subprocess
import sys
import os
from typing import Dict, Any

SHELL_TIMEOUT = 30
MAX_OUTPUT = 2000


def shell_exec(command: str) -> Dict[str, Any]:
    """
    在当前操作系统上执行 Shell 命令

    Windows: PowerShell
    Linux:   bash

    返回:
    {
        success: bool,
        exit_code: int,
        stdout: str,
        stderr: str,
        has_output: bool,
        summary: str,
        error: str (optional)
    }
    """

    try:
        # Windows
        if sys.platform == "win32":
            ps_command = (
                "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "
                "$OutputEncoding=[System.Text.UTF8Encoding]::new(); "
                + command
            )
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=SHELL_TIMEOUT,
                cwd=os.getcwd(),
            )

        # Linux / macOS
        else:
            proc = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=SHELL_TIMEOUT,
                cwd=os.getcwd(),
            )

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        # 截断超长输出
        if len(stdout) > MAX_OUTPUT:
            stdout = stdout[:MAX_OUTPUT] + "\n... (stdout 已截断)"

        if len(stderr) > MAX_OUTPUT:
            stderr = stderr[:MAX_OUTPUT] + "\n... (stderr 已截断)"

        success = proc.returncode == 0
        has_output = bool(stdout or stderr)

        # 给 Agent/UI 的简洁摘要
        if success:
            if stdout:
                summary = "命令执行成功"
            else:
                summary = "命令执行成功（无输出）"
        else:
            summary = f"命令执行失败 (exit_code={proc.returncode})"

        result = {
            "success": success,
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "has_output": has_output,
            "summary": summary,
        }

        # 错误信息
        if not success:
            result["error"] = (
                stderr[:300]
                if stderr
                else f"命令退出码 {proc.returncode}"
            )

        return result

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "has_output": False,
            "summary": f"命令超时（>{SHELL_TIMEOUT}s）",
            "error": f"命令超时（>{SHELL_TIMEOUT}s），已终止"
        }

    except FileNotFoundError:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "has_output": False,
            "summary": "Shell 不存在",
            "error": "未找到 shell，可能是环境异常"
        }

    except Exception as e:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "has_output": False,
            "summary": "执行异常",
            "error": str(e)[:300]
        }
