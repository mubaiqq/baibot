/*
 * baibot Control Panel - Windows GUI
 * Compile: gcc -mwindows -O2 deploy.c -o deploy.exe -lcomctl32 -lcomdlg32
 *
 * Features:
 *   - First run: detect Python → create venv → install deps → start WebUI
 *   - Control panel: start/stop WebUI, status, uninstall
 *   - Pure Win32 GUI, no console
 */

#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0600
#include <windows.h>
#include <commctrl.h>
#include <tlhelp32.h>
#include <shellapi.h>
#include <shlwapi.h>
#include <stdio.h>
#include <stdlib.h>

#pragma comment(linker, "\"/manifestdependency:type='win32' \
name='Microsoft.Windows.Common-Controls' version='6.0.0.0' \
processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")

/* ── Globals ── */
static char    g_project_dir[MAX_PATH];
static char    g_venv_dir[MAX_PATH];
static char    g_python_exe[MAX_PATH];
static char    g_pythonw_exe[MAX_PATH];
static char    g_pip_exe[MAX_PATH];
static char    g_marker_file[MAX_PATH];
static char    g_log_file[MAX_PATH];
static char    g_server_py[MAX_PATH];
static int     g_first_run = 0;
static int     g_is_running = 0;
static int     g_setup_step = 0;
static int     g_setup_total = 3;

static HWND    hwnd_main;
static HWND    hwnd_status_text;
static HWND    hwnd_url_text;
static HWND    hwnd_btn_start;
static HWND    hwnd_btn_stop;
static HWND    hwnd_btn_uninstall;
static HWND    hwnd_btn_log;
static HWND    hwnd_progress;
static HWND    hwnd_setup_text;
static HWND    hwnd_setup_btn;

#define WM_SETUP_STEP     (WM_USER + 100)
#define WM_SETUP_DONE     (WM_USER + 101)
#define WM_REFRESH_STATUS (WM_USER + 102)

#define PORT 7200

/* ── Forward declarations ── */
LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM);
LRESULT CALLBACK SetupWndProc(HWND, UINT, WPARAM, LPARAM);
DWORD WINAPI SetupThread(LPVOID);
DWORD WINAPI StartWebUIThread(LPVOID);
DWORD WINAPI StopWebUIThread(LPVOID);
void InitPaths(void);
int  FindSystemPython(void);
int  IsWebUIRunning(void);
void RefreshUI(void);
void ShowMainPanel(void);
void ShowSetupWizard(void);
void RunCommand(const char *cmd, char *output, int maxlen);
int  RunCommandWait(const char *cmd);

/* ── Init paths ── */
void InitPaths(void) {
    GetModuleFileNameA(NULL, g_project_dir, MAX_PATH);
    char *p = strrchr(g_project_dir, '\\');
    if (p) *p = '\0';

    snprintf(g_venv_dir,    MAX_PATH, "%s\\.venv",          g_project_dir);
    snprintf(g_python_exe,  MAX_PATH, "%s\\.venv\\Scripts\\python.exe",  g_project_dir);
    snprintf(g_pythonw_exe, MAX_PATH, "%s\\.venv\\Scripts\\pythonw.exe", g_project_dir);
    snprintf(g_pip_exe,     MAX_PATH, "%s\\.venv\\Scripts\\pip.exe",     g_project_dir);
    snprintf(g_marker_file, MAX_PATH, "%s\\.venv\\.installed",          g_project_dir);
    snprintf(g_log_file,    MAX_PATH, "%s\\baibot.log",     g_project_dir);
    snprintf(g_server_py,   MAX_PATH, "%s\\server.py",      g_project_dir);

    g_first_run = !PathFileExistsA(g_marker_file);
}

/* ── Find system Python ── */
int FindSystemPython(void) {
    const char *candidates[] = {
        NULL, /* USERPROFILE\python-sdk\... */
        NULL, /* LOCALAPPDATA\...Python314 */
        NULL, /* LOCALAPPDATA\...Python313 */
        NULL, /* LOCALAPPDATA\...Python312 */
        NULL, /* LOCALAPPDATA\...Python311 */
        "C:\\Python313\\python.exe",
        "C:\\Python312\\python.exe",
        NULL
    };

    char buf[MAX_PATH];
    char *up = getenv("USERPROFILE");
    char *la = getenv("LOCALAPPDATA");

    if (up) { snprintf(buf, MAX_PATH, "%s\\python-sdk\\python3.13.2\\python.exe", up); candidates[0] = strdup(buf); }
    if (la) { snprintf(buf, MAX_PATH, "%s\\Programs\\Python\\Python314\\python.exe", la); candidates[1] = strdup(buf); }
    if (la) { snprintf(buf, MAX_PATH, "%s\\Programs\\Python\\Python313\\python.exe", la); candidates[2] = strdup(buf); }
    if (la) { snprintf(buf, MAX_PATH, "%s\\Programs\\Python\\Python312\\python.exe", la); candidates[3] = strdup(buf); }
    if (la) { snprintf(buf, MAX_PATH, "%s\\Programs\\Python\\Python311\\python.exe", la); candidates[4] = strdup(buf); }

    for (int i = 0; i < 8; i++) {
        if (candidates[i] && PathFileExistsA(candidates[i])) return 1;
    }

    // Fallback: try "where python"
    FILE *fp = _popen("where python 2>nul", "r");
    if (fp) {
        if (fgets(buf, sizeof(buf), fp)) {
            buf[strcspn(buf, "\r\n")] = 0;
            _pclose(fp);
            if (PathFileExistsA(buf)) return 1;
        } else {
            _pclose(fp);
        }
    }
    return 0;
}

/* ── Is WebUI running? ── */
int IsWebUIRunning(void) {
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap == INVALID_HANDLE_VALUE) return 0;

    PROCESSENTRY32 pe;
    pe.dwSize = sizeof(pe);
    int found = 0;

    if (Process32First(hSnap, &pe)) {
        do {
            if (stricmp(pe.szExeFile, "pythonw.exe") == 0) {
                found = 1;
                break;
            }
        } while (Process32Next(hSnap, &pe));
    }
    CloseHandle(hSnap);
    return found;
}

/* ── Run command, capture output ── */
void RunCommand(const char *cmd, char *output, int maxlen) {
    if (output) output[0] = 0;
    FILE *fp = _popen(cmd, "r");
    if (!fp) return;
    if (output) {
        int total = 0;
        char line[1024];
        while (fgets(line, sizeof(line), fp) && total < maxlen - 1) {
            int len = (int)strlen(line);
            if (total + len >= maxlen) break;
            strcpy(output + total, line);
            total += len;
        }
    }
    _pclose(fp);
}

int RunCommandWait(const char *cmd) {
    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    char cmdline[1024];
    snprintf(cmdline, sizeof(cmdline), "cmd /c \"%s\"", cmd);

    if (!CreateProcessA(NULL, cmdline, NULL, NULL, FALSE,
                        CREATE_NO_WINDOW, NULL, NULL, &si, &pi))
        return -1;

    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD exitCode;
    GetExitCodeProcess(pi.hProcess, &exitCode);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return (int)exitCode;
}

/* ── Refresh UI ── */
void RefreshUI(void) {
    g_is_running = IsWebUIRunning();

    if (g_is_running) {
        SetWindowTextA(hwnd_status_text,
            "[ONLINE]  baibot WebUI running");
        char url[256];
        snprintf(url, sizeof(url), "http://localhost:%d", PORT);
        SetWindowTextA(hwnd_url_text, url);
        EnableWindow(hwnd_btn_start, FALSE);
        EnableWindow(hwnd_btn_stop, TRUE);
    } else {
        SetWindowTextA(hwnd_status_text,
            "[OFFLINE]  WebUI not running");
        SetWindowTextA(hwnd_url_text, "http://localhost:7200");
        EnableWindow(hwnd_btn_start, TRUE);
        EnableWindow(hwnd_btn_stop, FALSE);
    }
}

/* ── Start WebUI (background thread) ── */
DWORD WINAPI StartWebUIThread(LPVOID param) {
    (void)param;

    SetWindowTextA(hwnd_status_text, "Starting WebUI...");
    EnableWindow(hwnd_btn_start, FALSE);

    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "\"%s\" \"%s\"", g_pythonw_exe, g_server_py);

    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    if (CreateProcessA(NULL, cmd, NULL, NULL, FALSE,
                       CREATE_NO_WINDOW | DETACHED_PROCESS,
                       NULL, g_project_dir, &si, &pi)) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }

    Sleep(2000);
    PostMessageA(hwnd_main, WM_REFRESH_STATUS, 0, 0);
    return 0;
}

/* ── Stop WebUI (background thread) ── */
DWORD WINAPI StopWebUIThread(LPVOID param) {
    (void)param;
    system("taskkill /IM pythonw.exe /F >nul 2>&1");
    Sleep(500);
    PostMessageA(hwnd_main, WM_REFRESH_STATUS, 0, 0);
    return 0;
}

/* ── Setup thread ── */
DWORD WINAPI SetupThread(LPVOID param) {
    HWND hwnd = (HWND)param;
    char cmd[2048];
    int rc;

    /* Step 1: Create venv */
    PostMessageA(hwnd, WM_SETUP_STEP, 0, (LPARAM)"Creating virtual environment...");
    SendMessageA(hwnd_progress, PBM_SETPOS, 1, 0);

    snprintf(cmd, sizeof(cmd), "\"%s\" -m venv \"%s\"",
             getenv("PYTHON_SYS") ? getenv("PYTHON_SYS") : "python",
             g_venv_dir);
    rc = RunCommandWait(cmd);
    if (rc != 0) {
        PostMessageA(hwnd, WM_SETUP_STEP, 0, (LPARAM)"FAILED: venv creation failed");
        return 1;
    }

    /* Step 2: Install pip deps */
    PostMessageA(hwnd, WM_SETUP_STEP, 0, (LPARAM)"Installing dependencies...");
    SendMessageA(hwnd_progress, PBM_SETPOS, 2, 0);

    snprintf(cmd, sizeof(cmd),
             "\"%s\" install --quiet --upgrade pip && \"%s\" install --quiet -r \"%s\\requirements.txt\"",
             g_pip_exe, g_pip_exe, g_project_dir);
    rc = RunCommandWait(cmd);
    if (rc != 0) {
        PostMessageA(hwnd, WM_SETUP_STEP, 0, (LPARAM)"FAILED: pip install failed - check network");
        return 1;
    }

    /* Mark installed */
    HANDLE hf = CreateFileA(g_marker_file, GENERIC_WRITE, 0, NULL,
                            CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hf != INVALID_HANDLE_VALUE) CloseHandle(hf);

    /* Step 3: Start WebUI */
    PostMessageA(hwnd, WM_SETUP_STEP, 0, (LPARAM)"Starting WebUI...");
    SendMessageA(hwnd_progress, PBM_SETPOS, 3, 0);
    Sleep(500);

    PostMessageA(hwnd, WM_SETUP_DONE, 0, 0);
    return 0;
}

/* ── Setup wizard window proc ── */
LRESULT CALLBACK SetupWndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_CREATE: {
        /* Title */
        CreateWindowA("STATIC", "baibot Setup Wizard",
            WS_VISIBLE | WS_CHILD | SS_CENTER,
            20, 20, 360, 30, hwnd, NULL, NULL, NULL);

        /* Setup text */
        hwnd_setup_text = CreateWindowA("STATIC", "Preparing environment...",
            WS_VISIBLE | WS_CHILD | SS_LEFT,
            20, 60, 360, 20, hwnd, NULL, NULL, NULL);

        /* Progress bar */
        hwnd_progress = CreateWindowA(PROGRESS_CLASSA, NULL,
            WS_VISIBLE | WS_CHILD | PBS_SMOOTH,
            20, 90, 360, 25, hwnd, (HMENU)1, NULL, NULL);
        SendMessageA(hwnd_progress, PBM_SETRANGE, 0, MAKELPARAM(0, 3));
        SendMessageA(hwnd_progress, PBM_SETPOS, 0, 0);

        /* Cancel button */
        hwnd_setup_btn = CreateWindowA("BUTTON", "Cancel",
            WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
            310, 140, 70, 28, hwnd, (HMENU)2, NULL, NULL);

        /* Start setup in background thread */
        CreateThread(NULL, 0, SetupThread, hwnd, 0, NULL);
        return 0;
    }

    case WM_SETUP_STEP:
        SetWindowTextA(hwnd_setup_text, (LPCSTR)lp);
        return 0;

    case WM_SETUP_DONE:
        SetWindowTextA(hwnd_setup_text, "Setup complete! Launching control panel...");
        SendMessageA(hwnd_progress, PBM_SETPOS, 3, 0);
        Sleep(1000);
        ShowMainPanel();
        return 0;

    case WM_COMMAND:
        if (LOWORD(wp) == 2) {
            ShowMainPanel();
            return 0;
        }
        break;

    case WM_CLOSE:
        DestroyWindow(hwnd);
        return 0;
    }
    return DefWindowProcA(hwnd, msg, wp, lp);
}

void ShowSetupWizard(void) {
    /* Find system python first */
    if (!FindSystemPython()) {
        MessageBoxA(hwnd_main,
            "Python 3.10+ not found!\n\n"
            "Please install Python from https://www.python.org/downloads/\n"
            "Make sure to check 'Add Python to PATH' during installation.",
            "baibot - Error", MB_OK | MB_ICONERROR);
        PostQuitMessage(0);
        return;
    }

    /* Hide main panel, show wizard */
    DestroyWindow(hwnd_status_text);
    DestroyWindow(hwnd_url_text);
    DestroyWindow(hwnd_btn_start);
    DestroyWindow(hwnd_btn_stop);
    DestroyWindow(hwnd_btn_uninstall);
    DestroyWindow(hwnd_btn_log);

    WNDCLASSA wc = {0};
    wc.lpfnWndProc = SetupWndProc;
    wc.hInstance = GetModuleHandleA(NULL);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.lpszClassName = "baibotSetupWnd";
    RegisterClassA(&wc);

    HWND hwndSetup = CreateWindowA("baibotSetupWnd", "baibot Setup",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_VISIBLE,
        CW_USEDEFAULT, CW_USEDEFAULT, 420, 220,
        hwnd_main, NULL, wc.hInstance, NULL);

    /* Center relative to main */
    RECT rMain, rSetup;
    GetWindowRect(hwnd_main, &rMain);
    GetWindowRect(hwndSetup, &rSetup);
    int sw = rSetup.right - rSetup.left;
    int sh = rSetup.bottom - rSetup.top;
    SetWindowPos(hwndSetup, NULL,
        rMain.left + (rMain.right - rMain.left - sw) / 2,
        rMain.top + (rMain.bottom - rMain.top - sh) / 2,
        0, 0, SWP_NOSIZE | SWP_NOZORDER);

    ShowWindow(hwnd_main, SW_HIDE);
}

void ShowMainPanel(void) {
    ShowWindow(hwnd_main, SW_SHOW);

    /* Recreate child controls */
    hwnd_status_text = CreateWindowA("STATIC", "[OFFLINE]  WebUI not running",
        WS_VISIBLE | WS_CHILD | SS_CENTER,
        20, 15, 360, 25, hwnd_main, NULL, NULL, NULL);

    hwnd_url_text = CreateWindowA("EDIT", "http://localhost:7200",
        WS_VISIBLE | WS_CHILD | ES_READONLY | ES_CENTER | WS_BORDER,
        60, 55, 280, 22, hwnd_main, NULL, NULL, NULL);

    SendMessageA(hwnd_url_text, WM_SETFONT,
        (WPARAM)CreateFontA(16, 0, 0, 0, FW_NORMAL, 0, 0, 0,
            DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
            DEFAULT_QUALITY, DEFAULT_PITCH, "Consolas"), TRUE);

    hwnd_btn_start = CreateWindowA("BUTTON", "Start WebUI",
        WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        40, 100, 110, 35, hwnd_main, (HMENU)10, NULL, NULL);

    hwnd_btn_stop = CreateWindowA("BUTTON", "Stop WebUI",
        WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        155, 100, 110, 35, hwnd_main, (HMENU)11, NULL, NULL);

    hwnd_btn_log = CreateWindowA("BUTTON", "View Log",
        WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        270, 100, 110, 35, hwnd_main, (HMENU)12, NULL, NULL);

    hwnd_btn_uninstall = CreateWindowA("BUTTON", "Uninstall",
        WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
        140, 150, 110, 30, hwnd_main, (HMENU)13, NULL, NULL);

    RefreshUI();
}

/* ── Main window proc ── */
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_CREATE:
        if (g_first_run) {
            ShowSetupWizard();
        } else {
            ShowMainPanel();
        }
        return 0;

    case WM_COMMAND:
        switch (LOWORD(wp)) {
        case 10: /* Start */
            CreateThread(NULL, 0, StartWebUIThread, NULL, 0, NULL);
            break;
        case 11: /* Stop */
            CreateThread(NULL, 0, StopWebUIThread, NULL, 0, NULL);
            break;
        case 12: /* View Log */
            if (PathFileExistsA(g_log_file)) {
                ShellExecuteA(hwnd, "open", "notepad.exe", g_log_file, NULL, SW_SHOW);
            } else {
                MessageBoxA(hwnd, "No log file yet.", "baibot", MB_OK | MB_ICONINFORMATION);
            }
            break;
        case 13: /* Uninstall */
            if (MessageBoxA(hwnd,
                "This will remove the virtual environment,\n"
                "logs, and persistent configuration.\n\n"
                "Source code will NOT be deleted.\n\n"
                "Continue?",
                "baibot - Uninstall", MB_YESNO | MB_ICONWARNING) == IDYES) {

                if (g_is_running) {
                    system("taskkill /IM pythonw.exe /F >nul 2>&1");
                    Sleep(500);
                }

                char cmd[1024];
                snprintf(cmd, sizeof(cmd), "rmdir /s /q \"%s\"", g_venv_dir);
                system(cmd);
                DeleteFileA(g_log_file);
                snprintf(cmd, sizeof(cmd), "%s\\config.json", g_project_dir);
                DeleteFileA(cmd);
                snprintf(cmd, sizeof(cmd), "%s\\plugin_config.json", g_project_dir);
                DeleteFileA(cmd);
                snprintf(cmd, sizeof(cmd), "%s\\app_config.json", g_project_dir);
                DeleteFileA(cmd);

                MessageBoxA(hwnd,
                    "Uninstall complete.\n\n"
                    "Source code is preserved.\n"
                    "Run deploy.exe again to reinstall.",
                    "baibot", MB_OK | MB_ICONINFORMATION);
                PostQuitMessage(0);
            }
            break;
        }
        return 0;

    case WM_REFRESH_STATUS:
        RefreshUI();
        return 0;

    case WM_CTLCOLORSTATIC: {
        HDC hdc = (HDC)wp;
        SetBkMode(hdc, TRANSPARENT);
        SetTextColor(hdc, RGB(40, 40, 40));
        return (LRESULT)GetStockObject(WHITE_BRUSH);
    }

    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcA(hwnd, msg, wp, lp);
}

/* ── WinMain ── */
int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmdLine, int nShow) {
    (void)hPrev;
    (void)cmdLine;

    InitPaths();

    INITCOMMONCONTROLSEX icc = { sizeof(icc), ICC_PROGRESS_CLASS };
    InitCommonControlsEx(&icc);

    WNDCLASSA wc = {0};
    wc.lpfnWndProc   = WndProc;
    wc.hInstance     = hInst;
    wc.hCursor       = LoadCursorA(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.lpszClassName = "baibotMainWnd";
    RegisterClassA(&wc);

    hwnd_main = CreateWindowA("baibotMainWnd", "baibot Control Panel",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_VISIBLE,
        CW_USEDEFAULT, CW_USEDEFAULT, 420, 250,
        NULL, NULL, hInst, NULL);

    /* Center window */
    RECT rc;
    GetWindowRect(hwnd_main, &rc);
    int w = rc.right - rc.left;
    int h = rc.bottom - rc.top;
    int x = (GetSystemMetrics(SM_CXSCREEN) - w) / 2;
    int y = (GetSystemMetrics(SM_CYSCREEN) - h) / 2;
    SetWindowPos(hwnd_main, NULL, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER);

    MSG msg;
    while (GetMessageA(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }

    return (int)msg.wParam;
}
