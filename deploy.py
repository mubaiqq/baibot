"""
baibot Windows Control Panel
双击 deploy.exe 或 python deploy.py 运行
"""
import os
import sys
import subprocess
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR    = os.path.join(PROJECT_DIR, ".venv")
MARKER_FILE = os.path.join(VENV_DIR, ".installed")
LOG_FILE    = os.path.join(PROJECT_DIR, "baibot.log")
PORT        = 7200

PYTHON_EXE  = os.path.join(VENV_DIR, "Scripts", "python.exe")
PYTHONW_EXE = os.path.join(VENV_DIR, "Scripts", "pythonw.exe")


def title(text: str) -> None:
    os.system(f"title {text}")


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def is_running() -> bool:
    try:
        out = subprocess.check_output(
            'tasklist /FI "IMAGENAME eq pythonw.exe" /FO CSV /NH',
            shell=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return "pythonw.exe" in out
    except Exception:
        return False


def ensure_venv() -> None:
    python = _find_system_python()
    if not os.path.exists(VENV_DIR):
        print("  [1/2] Creating virtual environment...")
        subprocess.run([python, "-m", "venv", VENV_DIR], check=True)
        print("        done")

    if not os.path.exists(MARKER_FILE):
        print("  [2/2] Installing dependencies...")
        pip = os.path.join(VENV_DIR, "Scripts", "pip.exe")
        subprocess.run([pip, "install", "--quiet", "--upgrade", "pip"], check=True)
        subprocess.run([pip, "install", "--quiet", "-r", os.path.join(PROJECT_DIR, "requirements.txt")], check=True)
        open(MARKER_FILE, "w").close()
        print("        done")


def _find_system_python() -> str:
    candidates = [
        os.path.join(os.environ["USERPROFILE"], "python-sdk", "python3.13.2", "python.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python314", "python.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python313", "python.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python312", "python.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python311", "python.exe"),
        r"C:\Python313\python.exe",
        r"C:\Python312\python.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # fallback
    result = subprocess.run(["where", "python"], capture_output=True, text=True, shell=True)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().splitlines()[0]
    print("[FAIL] No Python found. Install Python 3.10+")
    print("       https://www.python.org/downloads/")
    input("Press Enter to exit...")
    sys.exit(1)


def stop_server() -> None:
    if is_running():
        subprocess.run(["taskkill", "/IM", "pythonw.exe", "/F"],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(0.5)


def start_webui() -> None:
    ensure_venv()
    stop_server()

    print("  Starting WebUI...")
    subprocess.Popen(
        [PYTHONW_EXE, os.path.join(PROJECT_DIR, "server.py")],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    if not is_running():
        print("  [FAIL] Startup failed. Check log:", LOG_FILE)
    else:
        print()
        print("  +----------------------------------------+")
        print("  |  baibot WebUI is running               |")
        print("  |                                        |")
        print(f"  |  http://localhost:{PORT}                  |")
        print("  |                                        |")
        print("  |  stop: deploy.exe stop                 |")
        print("  +----------------------------------------+")
        print()


def cli_chat() -> None:
    ensure_venv()
    print()
    print("  CLI chat mode. /help for help, /exit to quit.")
    print()
    subprocess.run([PYTHON_EXE, os.path.join(PROJECT_DIR, "main.py")])


def show_status() -> None:
    if is_running():
        print()
        print(f"  Online   Port: {PORT}")
        print(f"  http://localhost:{PORT}")
        print()
    else:
        print("  Offline")


def show_log() -> None:
    if os.path.exists(LOG_FILE):
        print()
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            print(f.read())
        print()
    else:
        print("  No log yet")


def update_deps() -> None:
    ensure_venv()
    print("  Updating...")
    pip = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    subprocess.run([pip, "install", "--quiet", "--upgrade", "pip"], check=True)
    subprocess.run([pip, "install", "--quiet", "--upgrade", "-r", os.path.join(PROJECT_DIR, "requirements.txt")], check=True)
    print("  Done")


def uninstall() -> None:
    print()
    print("  [WARNING] Will remove venv, logs and config.")
    print("  Source code will NOT be deleted.")
    print()
    confirm = input("  Type yes to confirm: ")
    if confirm.strip().lower() != "yes":
        print("  Cancelled")
        return

    stop_server()

    import shutil
    if os.path.exists(VENV_DIR):
        shutil.rmtree(VENV_DIR, ignore_errors=True)
    for f in [LOG_FILE,
              os.path.join(PROJECT_DIR, "config.json"),
              os.path.join(PROJECT_DIR, "plugin_config.json"),
              os.path.join(PROJECT_DIR, "app_config.json")]:
        if os.path.exists(f):
            os.remove(f)
    print("  Uninstall complete")


def menu() -> None:
    while True:
        clear()
        online = is_running()
        print()
        print("  ========================================")
        print("      baibot Control Panel")
        print("  ========================================")
        print()
        print(f"  Status: {'[ONLINE]' if online else '[OFFLINE]'}  http://localhost:{PORT}")
        print()
        print("  [1] CLI chat")
        print("  [2] Start WebUI")
        print("  [3] Stop WebUI")
        print("  [4] Restart WebUI")
        print("  [5] Status")
        print("  [6] View log")
        print("  [7] Update deps")
        print("  [8] Uninstall")
        print("  [0] Exit")
        print()
        try:
            choice = input("  Enter number: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "0":
            break
        elif choice == "1":
            cli_chat()
        elif choice == "2":
            start_webui()
        elif choice == "3":
            stop_server()
            print("  Stopped")
        elif choice == "4":
            stop_server()
            start_webui()
        elif choice == "5":
            show_status()
        elif choice == "6":
            show_log()
        elif choice == "7":
            update_deps()
        elif choice == "8":
            uninstall()
        else:
            print("  Invalid")
            time.sleep(0.5)
            continue

        input("\n  Press Enter to return...")


# ── CLI arg routing ──
if __name__ == "__main__":
    title("baibot Control Panel")
    ensure_venv()

    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg in ("cli", "1"):
        cli_chat()
    elif arg in ("start", "webui", "2"):
        start_webui()
    elif arg in ("stop", "3"):
        stop_server()
        print("Stopped")
    elif arg in ("restart", "4"):
        stop_server()
        start_webui()
    elif arg in ("status", "5"):
        show_status()
    elif arg in ("log", "6"):
        show_log()
    elif arg in ("update", "7"):
        update_deps()
    elif arg in ("uninstall", "8"):
        uninstall()
    else:
        menu()
