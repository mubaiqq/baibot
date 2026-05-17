"""
系统信息工具 — 跨平台兼容 Win / Linux
"""
import os
import platform
import subprocess
import sys


def _run(cmd: str) -> str:
    """执行系统命令并返回 stdout"""
    try:
        return subprocess.check_output(cmd, shell=True, text=True, timeout=8).strip()
    except Exception:
        return ""


def get_system_info():
    """
    获取当前运行环境的详细系统信息

    Windows: powershell Get-CimInstance
    Linux:   /proc 文件系统 + lspci
    """

    try:
        uname = platform.uname()

        info = {
            "success": True,
            "system": {
                "os": uname.system,
                "os_release": uname.release,
                "os_version": uname.version,
                "machine": uname.machine,
                "processor": uname.processor or platform.processor(),
                "hostname": uname.node,
            },
            "python": {
                "version": sys.version,
                "executable": sys.executable,
                "implementation": platform.python_implementation(),
                "compiler": platform.python_compiler(),
            },
            "paths": {
                "current_directory": os.getcwd(),
                "home_directory": os.path.expanduser("~"),
            },
            "user": {},
        }

        # 用户信息
        try:
            info["user"]["login"] = os.getlogin()
        except OSError:
            info["user"]["login"] = os.environ.get("USER", os.environ.get("USERNAME", ""))

        # CPU 核心数
        if hasattr(os, "cpu_count"):
            info["cpu_count"] = os.cpu_count()

        # =====================================================
        # Windows
        # =====================================================
        if sys.platform == "win32":
            info["system"]["platform"] = "Windows"
            win_ver = sys.getwindowsversion()
            info["system"]["windows_version"] = f"{win_ver.major}.{win_ver.minor}.{win_ver.build}"

            # CPU 型号
            cpu_name = _run('powershell -Command "(Get-CimInstance Win32_Processor).Name"')
            if cpu_name:
                info["cpu_model"] = cpu_name.strip()

            # 内存总量
            total_mem = _run('powershell -Command "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"')
            if total_mem:
                try:
                    info["ram_total_bytes"] = int(total_mem.strip())
                    info["ram_total"] = f"{info['ram_total_bytes'] / (1024**3):.1f} GB"
                except ValueError:
                    pass

            # 可用内存
            free_mem = _run('powershell -Command "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"')
            if free_mem and "ram_total_bytes" in info:
                try:
                    free_kb = int(free_mem.strip())
                    free_bytes = free_kb * 1024
                    used_bytes = info["ram_total_bytes"] - free_bytes
                    info["ram_used_bytes"] = used_bytes
                    info["ram_used"] = f"{used_bytes / (1024**3):.1f} GB"
                    info["ram_free"] = f"{free_bytes / (1024**3):.1f} GB"
                    info["ram_usage_percent"] = round(used_bytes / info["ram_total_bytes"] * 100, 1)
                except ValueError:
                    pass

            # 显卡
            gpu_output = _run(
                'powershell -Command '
                '"Get-CimInstance Win32_VideoController | '
                'Select-Object Name,AdapterRAM | ConvertTo-Csv -NoTypeInformation"'
            )
            if gpu_output:
                gpus = []
                for line in gpu_output.splitlines()[1:]:
                    parts = line.strip('"').split('","')
                    if len(parts) >= 1 and parts[0].strip():
                        gpu_info = {"name": parts[0].strip()}
                        if len(parts) >= 2 and parts[1].strip():
                            try:
                                ram_bytes = int(parts[1].strip())
                                gpu_info["ram"] = f"{ram_bytes / (1024**3):.1f} GB"
                            except ValueError:
                                pass
                        gpus.append(gpu_info)
                if gpus:
                    info["gpus"] = gpus

        # =====================================================
        # Linux
        # =====================================================
        else:
            info["system"]["platform"] = "Linux" if sys.platform.startswith("linux") else sys.platform

            # CPU 型号
            cpu = _run("cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d: -f2")
            if cpu:
                info["cpu_model"] = cpu.strip()

            # 内存 — 总量
            mem_total_raw = _run("cat /proc/meminfo | grep MemTotal | awk '{print $2}'")
            if mem_total_raw:
                try:
                    total_kb = int(mem_total_raw)
                    total_bytes = total_kb * 1024
                    info["ram_total_bytes"] = total_bytes
                    info["ram_total"] = f"{total_bytes / (1024**3):.1f} GB"
                except ValueError:
                    pass

            # 内存 — 可用
            mem_avail_raw = _run("cat /proc/meminfo | grep MemAvailable | awk '{print $2}'")
            if mem_avail_raw and "ram_total_bytes" in info:
                try:
                    avail_kb = int(mem_avail_raw)
                    avail_bytes = avail_kb * 1024
                    used_bytes = info["ram_total_bytes"] - avail_bytes
                    info["ram_used_bytes"] = used_bytes
                    info["ram_used"] = f"{used_bytes / (1024**3):.1f} GB"
                    info["ram_free"] = f"{avail_bytes / (1024**3):.1f} GB"
                    info["ram_usage_percent"] = round(used_bytes / info["ram_total_bytes"] * 100, 1)
                except ValueError:
                    pass

            # 显卡
            gpu_raw = _run("lspci | grep -E 'VGA|3D|Display'")
            if gpu_raw:
                gpus = []
                for line in gpu_raw.splitlines():
                    name = line.split(": ")[-1].strip() if ": " in line else line.strip()
                    if name:
                        gpus.append({"name": name})
                if gpus:
                    info["gpus"] = gpus

        return info

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
