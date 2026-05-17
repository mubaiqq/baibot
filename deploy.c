/*
 * baibot Control Panel - Windows GUI (C + Win32)
 * Compile: gcc -mwindows -O2 deploy.c -o deploy.exe -lcomctl32 -lshlwapi
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <tlhelp32.h>
#include <shlwapi.h>
#include <shellapi.h>
#include <stdio.h>
#include <stdlib.h>

#pragma comment(linker, "\"/manifestdependency:type='win32' \
name='Microsoft.Windows.Common-Controls' version='6.0.0.0' \
processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")

#define PORT      7200
#define IDC_START 101
#define IDC_STOP  102
#define IDC_LOG   103
#define IDC_UNINST 104
#define IDC_SETUP  105
#define IDC_URL    106

static char  g_dir[MAX_PATH];
static char  g_venv[MAX_PATH];
static char  g_marker[MAX_PATH];
static char  g_pythonw[MAX_PATH];
static char  g_server[MAX_PATH];
static char  g_log[MAX_PATH];
static char  g_sys_python[MAX_PATH];
static HWND  g_hwnd;
static HWND  g_status;
static HWND  g_url;
static int   g_has_venv;

/* ── helper ── */
static int _exists(const char *path) { return GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES; }

static void _init_paths(void) {
    GetModuleFileNameA(NULL, g_dir, MAX_PATH);
    char *p = strrchr(g_dir, '\\'); if (p) *p = 0;
    snprintf(g_venv,    MAX_PATH, "%s\\.venv", g_dir);
    snprintf(g_marker,  MAX_PATH, "%s\\.venv\\.installed", g_dir);
    snprintf(g_pythonw, MAX_PATH, "%s\\.venv\\Scripts\\pythonw.exe", g_dir);
    snprintf(g_server,  MAX_PATH, "%s\\server.py", g_dir);
    snprintf(g_log,     MAX_PATH, "%s\\baibot.log", g_dir);
    g_has_venv = _exists(g_marker);
}

/* ── find system python ── */
static const char *_find_python(void) {
    g_sys_python[0] = 0;
    const char *home = getenv("USERPROFILE");
    const char *lapp = getenv("LOCALAPPDATA");

    const char *try[] = {NULL,NULL,NULL,NULL,NULL,NULL,
        "C:\\Python313\\python.exe","C:\\Python312\\python.exe",NULL};
    char b1[MAX_PATH], b2[MAX_PATH], b3[MAX_PATH], b4[MAX_PATH], b5[MAX_PATH];

    if (home) { snprintf(b1,MAX_PATH,"%s\\python-sdk\\python3.13.2\\python.exe",home); try[0]=b1; }
    if (lapp) { snprintf(b2,MAX_PATH,"%s\\Programs\\Python\\Python314\\python.exe",lapp); try[1]=b2; }
    if (lapp) { snprintf(b3,MAX_PATH,"%s\\Programs\\Python\\Python313\\python.exe",lapp); try[2]=b3; }
    if (lapp) { snprintf(b4,MAX_PATH,"%s\\Programs\\Python\\Python312\\python.exe",lapp); try[3]=b4; }
    if (lapp) { snprintf(b5,MAX_PATH,"%s\\Programs\\Python\\Python311\\python.exe",lapp); try[4]=b5; }

    for (int i = 0; try[i]; i++) {
        if (_exists(try[i])) { strncpy(g_sys_python, try[i], MAX_PATH-1); return g_sys_python; }
    }

    /* where python */
    FILE *fp = _popen("where python 2>nul", "r");
    if (fp) {
        char line[512];
        if (fgets(line, sizeof(line), fp)) {
            line[strcspn(line, "\r\n")] = 0;
            _pclose(fp);
            if (_exists(line)) { strncpy(g_sys_python, line, MAX_PATH-1); return g_sys_python; }
        } else _pclose(fp);
    }
    return NULL;
}

/* ── is pythonw.exe running? ── */
static int _is_running(void) {
    HANDLE h = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (h == INVALID_HANDLE_VALUE) return 0;
    PROCESSENTRY32 pe = { sizeof(pe) };
    int found = 0;
    if (Process32First(h, &pe)) {
        do { if (lstrcmpiA(pe.szExeFile, "pythonw.exe") == 0) { found = 1; break; } }
        while (Process32Next(h, &pe));
    }
    CloseHandle(h);
    return found;
}

/* ── run command hidden, wait ── */
static int _run_wait(const char *fmt, ...) {
    char cmd[2048], line[3072];
    va_list va; va_start(va, fmt); vsnprintf(cmd, sizeof(cmd), fmt, va); va_end(va);
    snprintf(line, sizeof(line), "cmd /c \"%s\"", cmd);

    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE;
    if (!CreateProcessA(NULL, line, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi))
        return -1;
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD ec; GetExitCodeProcess(pi.hProcess, &ec);
    CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
    return (int)ec;
}

/* ── start webui in background ── */
static void _start_webui(void) {
    SetWindowTextA(g_status, "Starting WebUI...");
    InvalidateRect(g_hwnd, NULL, TRUE);

    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "\"%s\" \"%s\"", g_pythonw, g_server);
    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE;
    CreateProcessA(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW | DETACHED_PROCESS, NULL, g_dir, &si, &pi);
    if (pi.hProcess) { CloseHandle(pi.hProcess); CloseHandle(pi.hThread); }
    Sleep(2500);
}

/* ── refresh ui ── */
static void _refresh(void) {
    int on = _is_running();
    SetWindowTextA(g_status, on ? "[ONLINE]  baibot WebUI" : "[OFFLINE]");
    SetWindowTextA(g_url, on ? "http://localhost:7200" : "Not running");

    EnableWindow(GetDlgItem(g_hwnd, IDC_START), !on && g_has_venv);
    EnableWindow(GetDlgItem(g_hwnd, IDC_STOP), on);
    EnableWindow(GetDlgItem(g_hwnd, IDC_SETUP), !g_has_venv);

    /* flash window if running */
    ShowWindow(g_hwnd, SW_SHOW);
}

/* ── do setup ── */
static int _do_setup(void) {
    const char *py = _find_python();
    if (!py) {
        MessageBoxA(g_hwnd,
            "Python 3.10+ not found!\n\n"
            "Please install from: https://www.python.org/downloads/\n"
            "Check 'Add Python to PATH' during install.",
            "baibot - Error", MB_OK | MB_ICONERROR);
        return 0;
    }

    /* step 1: venv */
    SetWindowTextA(g_status, "Creating virtual environment...");
    InvalidateRect(g_hwnd, NULL, TRUE);
    if (_run_wait("\"%s\" -m venv \"%s\"", py, g_venv) != 0) {
        MessageBoxA(g_hwnd, "Virtual environment creation failed.", "baibot", MB_OK | MB_ICONERROR);
        return 0;
    }

    /* step 2: pip install */
    SetWindowTextA(g_status, "Installing dependencies (may take a minute)...");
    InvalidateRect(g_hwnd, NULL, TRUE);

    char pp[MAX_PATH];
    snprintf(pp, MAX_PATH, "%s\\Scripts\\pip.exe", g_venv);
    if (_run_wait("\"%s\" install -q -r \"%s\\requirements.txt\"", pp, g_dir) != 0) {
        MessageBoxA(g_hwnd, "Dependency install failed.\nCheck network or proxy settings.", "baibot", MB_OK | MB_ICONERROR);
        return 0;
    }

    /* mark */
    HANDLE hf = CreateFileA(g_marker, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hf != INVALID_HANDLE_VALUE) CloseHandle(hf);

    g_has_venv = 1;
    return 1;
}

/* ── setup + start thread ── */
static DWORD WINAPI _setup_and_start(LPVOID p) {
    (void)p;
    if (_do_setup()) {
        SetWindowTextA(g_status, "Starting WebUI...");
        InvalidateRect(g_hwnd, NULL, TRUE);
        _start_webui();
    }
    _refresh();
    return 0;
}

/* ── start thread ── */
static DWORD WINAPI _start_thread(LPVOID p) {
    (void)p;
    _start_webui();
    _refresh();
    return 0;
}

/* ── stop thread ── */
static DWORD WINAPI _stop_thread(LPVOID p) {
    (void)p;
    system("taskkill /IM pythonw.exe /F >nul 2>&1");
    Sleep(600);
    _refresh();
    return 0;
}

/* ── wndproc ── */
static LRESULT CALLBACK _wndproc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_CREATE: {
        g_hwnd = hwnd;

        /* title */
        CreateWindowA("STATIC", "baibot Control Panel",
            WS_VISIBLE | WS_CHILD | SS_CENTER,
            15, 15, 320, 22, hwnd, NULL, NULL, NULL);

        /* status */
        g_status = CreateWindowA("STATIC", "[OFFLINE]",
            WS_VISIBLE | WS_CHILD | SS_CENTER,
            15, 42, 320, 20, hwnd, NULL, NULL, NULL);

        /* url box */
        g_url = CreateWindowA("EDIT", "",
            WS_VISIBLE | WS_CHILD | ES_READONLY | ES_CENTER | WS_BORDER,
            50, 72, 250, 24, hwnd, (HMENU)IDC_URL, NULL, NULL);
        {
            HFONT f = CreateFontA(15,0,0,0,FW_SEMIBOLD,0,0,0,DEFAULT_CHARSET,
                OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,DEFAULT_QUALITY,
                FIXED_PITCH|FF_MODERN,"Consolas");
            SendMessageA(g_url, WM_SETFONT, (WPARAM)f, TRUE);
        }

        /* buttons row 1 */
        CreateWindowA("BUTTON", "Start WebUI",
            WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
            25, 112, 105, 34, hwnd, (HMENU)IDC_START, NULL, NULL);

        CreateWindowA("BUTTON", "Stop WebUI",
            WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
            135, 112, 105, 34, hwnd, (HMENU)IDC_STOP, NULL, NULL);

        CreateWindowA("BUTTON", "View Log",
            WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
            245, 112, 105, 34, hwnd, (HMENU)IDC_LOG, NULL, NULL);

        /* setup / uninstall row */
        CreateWindowA("BUTTON", "Setup (install)",
            WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
            25, 155, 130, 30, hwnd, (HMENU)IDC_SETUP, NULL, NULL);

        CreateWindowA("BUTTON", "Uninstall",
            WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
            195, 155, 130, 30, hwnd, (HMENU)IDC_UNINST, NULL, NULL);

        _refresh();
        return 0;
    }

    case WM_COMMAND: {
        int id = LOWORD(wp);
        if (id == IDC_START) {
            SetWindowTextA(g_status, "Launching...");
            InvalidateRect(hwnd, NULL, TRUE);
            CreateThread(NULL, 0, _start_thread, NULL, 0, NULL);
        } else if (id == IDC_STOP) {
            CreateThread(NULL, 0, _stop_thread, NULL, 0, NULL);
        } else if (id == IDC_SETUP) {
            SetWindowTextA(g_status, "Setting up...");
            InvalidateRect(hwnd, NULL, TRUE);
            EnableWindow(GetDlgItem(hwnd, IDC_SETUP), FALSE);
            CreateThread(NULL, 0, _setup_and_start, NULL, 0, NULL);
        } else if (id == IDC_LOG) {
            if (_exists(g_log))
                ShellExecuteA(hwnd, "open", "notepad.exe", g_log, NULL, SW_SHOW);
            else
                MessageBoxA(hwnd, "No log file yet.", "baibot", MB_OK | MB_ICONINFORMATION);
        } else if (id == IDC_UNINST) {
            if (MessageBoxA(hwnd,
                "Remove virtual environment, logs, and config?\n\n"
                "Source code will NOT be deleted.",
                "baibot - Uninstall", MB_YESNO | MB_ICONWARNING) == IDYES) {

                if (_is_running()) system("taskkill /IM pythonw.exe /F >nul 2>&1");

                char cmd[MAX_PATH+32];
                snprintf(cmd, sizeof(cmd), "rmdir /s /q \"%s\"", g_venv);
                system(cmd);
                DeleteFileA(g_log);
                snprintf(cmd, sizeof(cmd), "%s\\config.json", g_dir); DeleteFileA(cmd);
                snprintf(cmd, sizeof(cmd), "%s\\plugin_config.json", g_dir); DeleteFileA(cmd);
                snprintf(cmd, sizeof(cmd), "%s\\app_config.json", g_dir); DeleteFileA(cmd);

                g_has_venv = 0;
                _refresh();
                MessageBoxA(hwnd,
                    "Uninstall complete.\nSource code preserved.\n"
                    "Click 'Setup' to reinstall.",
                    "baibot", MB_OK | MB_ICONINFORMATION);
            }
        }
        return 0;
    }

    case WM_CTLCOLORSTATIC: {
        HDC hdc = (HDC)wp;
        SetBkMode(hdc, TRANSPARENT);
        SetTextColor(hdc, GetSysColor(COLOR_WINDOWTEXT));
        return (LRESULT)GetSysColorBrush(COLOR_WINDOW);
    }

    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcA(hwnd, msg, wp, lp);
}

/* ── WinMain ── */
int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmd, int nShow) {
    (void)hPrev; (void)cmd;

    _init_paths();

    INITCOMMONCONTROLSEX icc = { sizeof(icc), ICC_STANDARD_CLASSES };
    InitCommonControlsEx(&icc);

    WNDCLASSA wc = {0};
    wc.lpfnWndProc   = _wndproc;
    wc.hInstance     = hInst;
    wc.hCursor       = LoadCursorA(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.lpszClassName = "baibotPanel";
    RegisterClassA(&wc);

    HWND hwnd = CreateWindowA("baibotPanel", "baibot Control Panel",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT, 370, 240,
        NULL, NULL, hInst, NULL);

    RECT r; GetWindowRect(hwnd, &r);
    int w = r.right - r.left, h = r.bottom - r.top;
    SetWindowPos(hwnd, NULL,
        (GetSystemMetrics(SM_CXSCREEN) - w) / 2,
        (GetSystemMetrics(SM_CYSCREEN) - h) / 2,
        0, 0, SWP_NOSIZE | SWP_NOZORDER);

    ShowWindow(hwnd, nShow);
    UpdateWindow(hwnd);

    MSG msg;
    while (GetMessageA(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
    return (int)msg.wParam;
}
