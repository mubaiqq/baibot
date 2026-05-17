/*
 * baibot Windows 控制面板 (C + Win32 Unicode)
 * 编译: gcc -mwindows -O2 -municode deploy.c -o deploy.exe -lcomctl32 -lshlwapi
 */

#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE
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

#define PORT 7200
#define IDC_START   101
#define IDC_STOP    102
#define IDC_LOG     103
#define IDC_UNINST  104
#define IDC_SETUP   105
#define IDC_COPY    106
#define IDC_URL     107

static WCHAR g_dir[MAX_PATH];
static WCHAR g_venv[MAX_PATH];
static WCHAR g_marker[MAX_PATH];
static WCHAR g_pythonw[MAX_PATH];
static WCHAR g_python[MAX_PATH];
static WCHAR g_pip[MAX_PATH];
static WCHAR g_server[MAX_PATH];
static WCHAR g_log[MAX_PATH];
static WCHAR g_sys_python[MAX_PATH];
static WCHAR g_url_text[128];
static HWND  g_hwnd;
static HWND  g_status;
static HWND  g_url;
static int   g_has_venv;

/* ── 辅助 ── */
static int _exists(const WCHAR *path) { return GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES; }

static void _init_paths(void) {
    GetModuleFileNameW(NULL, g_dir, MAX_PATH);
    WCHAR *p = wcsrchr(g_dir, L'\\'); if (p) *p = 0;

    wsprintfW(g_venv,    L"%s\\.venv", g_dir);
    wsprintfW(g_marker,  L"%s\\.venv\\.installed", g_dir);
    wsprintfW(g_pythonw, L"%s\\.venv\\Scripts\\pythonw.exe", g_dir);
    wsprintfW(g_python,  L"%s\\.venv\\Scripts\\python.exe", g_dir);
    wsprintfW(g_pip,     L"%s\\.venv\\Scripts\\pip.exe", g_dir);
    wsprintfW(g_server,  L"%s\\server.py", g_dir);
    wsprintfW(g_log,     L"%s\\baibot.log", g_dir);
    wsprintfW(g_url_text, L"http://localhost:%d", PORT);
    g_has_venv = _exists(g_marker);
}

/* ── 查找系统 Python ── */
static const WCHAR *_find_python(void) {
    g_sys_python[0] = 0;
    const WCHAR *home = _wgetenv(L"USERPROFILE");
    const WCHAR *lapp = _wgetenv(L"LOCALAPPDATA");
    WCHAR buf[8][MAX_PATH];
    int n = 0;

    if (home) { wsprintfW(buf[n], L"%s\\python-sdk\\python3.13.2\\python.exe", home); n++; }
    if (lapp) { wsprintfW(buf[n], L"%s\\Programs\\Python\\Python314\\python.exe", lapp); n++; }
    if (lapp) { wsprintfW(buf[n], L"%s\\Programs\\Python\\Python313\\python.exe", lapp); n++; }
    if (lapp) { wsprintfW(buf[n], L"%s\\Programs\\Python\\Python312\\python.exe", lapp); n++; }
    if (lapp) { wsprintfW(buf[n], L"%s\\Programs\\Python\\Python311\\python.exe", lapp); n++; }
    wcscpy(buf[n], L"C:\\Python313\\python.exe"); n++;
    wcscpy(buf[n], L"C:\\Python312\\python.exe"); n++;

    for (int i = 0; i < n; i++) {
        if (_exists(buf[i])) { wcscpy(g_sys_python, buf[i]); return g_sys_python; }
    }

    FILE *fp = _wpopen(L"where python 2>nul", L"r");
    if (fp) {
        WCHAR line[512];
        if (fgetws(line, 512, fp)) {
            line[wcscspn(line, L"\r\n")] = 0;
            _pclose(fp);
            if (_exists(line)) { wcscpy(g_sys_python, line); return g_sys_python; }
        } else _pclose(fp);
    }
    return NULL;
}

/* ── 检测 WebUI 是否运行 ── */
static int _is_running(void) {
    /* 方法1: 查进程名 */
    HANDLE h = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (h != INVALID_HANDLE_VALUE) {
        PROCESSENTRY32W pe = { sizeof(pe) };
        if (Process32FirstW(h, &pe)) {
            do {
                if (lstrcmpiW(pe.szExeFile, L"pythonw.exe") == 0 ||
                    lstrcmpiW(pe.szExeFile, L"python.exe") == 0)
                {
                    CloseHandle(h);
                    return 1;
                }
            } while (Process32NextW(h, &pe));
        }
        CloseHandle(h);
    }
    return 0;
}

/* ── 运行命令隐藏窗口等待 ── */
static int _run_wait(const WCHAR *fmt, ...) {
    WCHAR cmd[4096], line[8192];
    va_list va; va_start(va, fmt); wvnsprintfW(cmd, 4096, fmt, va); va_end(va);
    wsprintfW(line, L"cmd /c \"%s\"", cmd);

    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE;
    if (!CreateProcessW(NULL, line, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi))
        return -1;
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD ec; GetExitCodeProcess(pi.hProcess, &ec);
    CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
    return (int)ec;
}

/* ── 启动 WebUI ── */
static void _start_webui(void) {
    WCHAR cmd[1024];
    wsprintfW(cmd, L"\"%s\" \"%s\"", g_pythonw, g_server);

    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE;
    if (CreateProcessW(NULL, cmd, NULL, NULL, FALSE,
                       CREATE_NO_WINDOW, NULL, g_dir, &si, &pi)) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
    Sleep(3000);
}

/* ── 停止 WebUI ── */
static void _stop_webui(void) {
    /* 杀掉 pythonw.exe 和 python.exe */
    HANDLE h = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (h != INVALID_HANDLE_VALUE) {
        PROCESSENTRY32W pe = { sizeof(pe) };
        if (Process32FirstW(h, &pe)) {
            do {
                if (lstrcmpiW(pe.szExeFile, L"pythonw.exe") == 0 ||
                    lstrcmpiW(pe.szExeFile, L"python.exe") == 0)
                {
                    HANDLE ph = OpenProcess(PROCESS_TERMINATE, FALSE, pe.th32ProcessID);
                    if (ph) { TerminateProcess(ph, 0); CloseHandle(ph); }
                }
            } while (Process32NextW(h, &pe));
        }
        CloseHandle(h);
    }
    Sleep(800);
}

/* ── 刷新界面 ── */
static void _refresh(void) {
    int on = _is_running();

    SetWindowTextW(g_status, on ?
        L"[运行中]  已启动" :
        L"[未启动]  点击下方按钮启动服务");

    WCHAR url[256];
    if (on) {
        wsprintfW(url, L"<a href=\"http://localhost:%d\">http://localhost:%d</a>  ", PORT, PORT);
    } else {
        wcscpy(url, L"服务未启动");
    }
    SetWindowTextW(g_url, url);

    EnableWindow(GetDlgItem(g_hwnd, IDC_START), !on && g_has_venv);
    EnableWindow(GetDlgItem(g_hwnd, IDC_STOP), on);
    EnableWindow(GetDlgItem(g_hwnd, IDC_SETUP), !g_has_venv);
    EnableWindow(GetDlgItem(g_hwnd, IDC_COPY), on);
}

/* ── 安装 ── */
static int _do_setup(void) {
    const WCHAR *py = _find_python();
    if (!py) {
        MessageBoxW(g_hwnd,
            L"未找到 Python 3.10+ ！\n\n"
            L"请从 https://www.python.org/downloads/ 下载安装\n"
            L"安装时请勾选 \"Add Python to PATH\"",
            L"baibot - 错误", MB_OK | MB_ICONERROR);
        return 0;
    }

    WCHAR msg[256];
    wsprintfW(msg, L"检测到 Python: %s\n开始安装...", py);
    SetWindowTextW(g_status, msg);

    /* 创建虚拟环境 */
    if (_run_wait(L"\"%s\" -m venv \"%s\"", py, g_venv) != 0) {
        MessageBoxW(g_hwnd, L"虚拟环境创建失败", L"baibot", MB_OK | MB_ICONERROR);
        return 0;
    }

    /* 安装依赖 */
    SetWindowTextW(g_status, L"正在安装依赖（可能需要几分钟）...");
    if (_run_wait(L"\"%s\" install -q -r \"%s\\requirements.txt\"", g_pip, g_dir) != 0) {
        MessageBoxW(g_hwnd, L"依赖安装失败，请检查网络或代理设置", L"baibot", MB_OK | MB_ICONERROR);
        return 0;
    }

    HANDLE hf = CreateFileW(g_marker, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hf != INVALID_HANDLE_VALUE) CloseHandle(hf);

    g_has_venv = 1;
    return 1;
}

/* ── 后台线程 ── */
static DWORD WINAPI _setup_and_start(LPVOID p) {
    (void)p;
    if (_do_setup()) {
        SetWindowTextW(g_status, L"正在启动服务...");
        _start_webui();
    }
    _refresh();
    return 0;
}

static DWORD WINAPI _start_thread(LPVOID p) {
    (void)p;
    SetWindowTextW(g_status, L"正在启动...");
    _start_webui();
    _refresh();
    return 0;
}

static DWORD WINAPI _stop_thread(LPVOID p) {
    (void)p;
    _stop_webui();
    _refresh();
    return 0;
}

/* ── 窗口过程 ── */
static LRESULT CALLBACK _wndproc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_CREATE: {
        g_hwnd = hwnd;

        HFONT hTitle = CreateFontW(18,0,0,0,FW_BOLD,0,0,0,
            DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,
            DEFAULT_QUALITY,DEFAULT_PITCH,L"Microsoft YaHei UI");
        HFONT hNormal = CreateFontW(14,0,0,0,FW_NORMAL,0,0,0,
            DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,
            DEFAULT_QUALITY,DEFAULT_PITCH,L"Microsoft YaHei UI");

        /* 标题 */
        HWND ctl = CreateWindowW(L"STATIC", L"baibot · 小白 控制面板",
            WS_VISIBLE|WS_CHILD|SS_CENTER,
            10,12,340,28, hwnd, NULL, NULL, NULL);
        SendMessageW(ctl, WM_SETFONT, (WPARAM)hTitle, TRUE);

        /* 状态 */
        g_status = CreateWindowW(L"STATIC", L"[未启动]",
            WS_VISIBLE|WS_CHILD|SS_CENTER,
            10,48,340,22, hwnd, NULL, NULL, NULL);
        SendMessageW(g_status, WM_SETFONT, (WPARAM)hNormal, TRUE);

        /* URL - 使用 SysLink 控件支持点击 */
        g_url = CreateWindowW(L"SysLink", L"<a>http://localhost:7200</a>",
            WS_VISIBLE|WS_CHILD|SS_CENTER,
            30,82,300,26, hwnd, (HMENU)IDC_URL, NULL, NULL);
        SendMessageW(g_url, WM_SETFONT, (WPARAM)hNormal, TRUE);

        /* 按钮行1 */
        int btw = 100, bth = 36, gap = 8;
        int x = (360 - (btw*3 + gap*2)) / 2;

        CreateWindowW(L"BUTTON", L"启动 WebUI",
            WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON,
            x, 120, btw, bth, hwnd, (HMENU)IDC_START, NULL, NULL);

        CreateWindowW(L"BUTTON", L"停止 WebUI",
            WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON,
            x+btw+gap, 120, btw, bth, hwnd, (HMENU)IDC_STOP, NULL, NULL);

        CreateWindowW(L"BUTTON", L"复制地址",
            WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON,
            x+(btw+gap)*2, 120, btw, bth, hwnd, (HMENU)IDC_COPY, NULL, NULL);

        /* 按钮行2 */
        int btw2 = 110, x2 = (360 - (btw2*3 + gap*2)) / 2;

        CreateWindowW(L"BUTTON", L"一键安装",
            WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON,
            x2, 168, btw2, bth-6, hwnd, (HMENU)IDC_SETUP, NULL, NULL);

        CreateWindowW(L"BUTTON", L"查看日志",
            WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON,
            x2+btw2+gap, 168, btw2, bth-6, hwnd, (HMENU)IDC_LOG, NULL, NULL);

        CreateWindowW(L"BUTTON", L"卸载",
            WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON,
            x2+(btw2+gap)*2, 168, btw2, bth-6, hwnd, (HMENU)IDC_UNINST, NULL, NULL);

        _refresh();
        return 0;
    }

    case WM_COMMAND: {
        int id = LOWORD(wp);
        if (id == IDC_START) {
            EnableWindow(GetDlgItem(hwnd, IDC_START), FALSE);
            SetWindowTextW(g_status, L"正在启动...");
            CreateThread(NULL, 0, _start_thread, NULL, 0, NULL);
        } else if (id == IDC_STOP) {
            EnableWindow(GetDlgItem(hwnd, IDC_STOP), FALSE);
            SetWindowTextW(g_status, L"正在停止...");
            CreateThread(NULL, 0, _stop_thread, NULL, 0, NULL);
        } else if (id == IDC_COPY) {
            if (OpenClipboard(hwnd)) {
                EmptyClipboard();
                int len = (lstrlenW(g_url_text) + 1) * sizeof(WCHAR);
                HGLOBAL hMem = GlobalAlloc(GMEM_MOVEABLE, len);
                if (hMem) {
                    memcpy(GlobalLock(hMem), g_url_text, len);
                    GlobalUnlock(hMem);
                    SetClipboardData(CF_UNICODETEXT, hMem);
                }
                CloseClipboard();
            }
            MessageBoxW(hwnd, L"地址已复制到剪贴板！", L"baibot", MB_OK | MB_ICONINFORMATION);
        } else if (id == IDC_SETUP) {
            EnableWindow(GetDlgItem(hwnd, IDC_SETUP), FALSE);
            SetWindowTextW(g_status, L"正在检测环境...");
            CreateThread(NULL, 0, _setup_and_start, NULL, 0, NULL);
        } else if (id == IDC_LOG) {
            if (_exists(g_log))
                ShellExecuteW(hwnd, L"open", L"notepad.exe", g_log, NULL, SW_SHOW);
            else
                MessageBoxW(hwnd, L"暂无日志文件", L"baibot", MB_OK | MB_ICONINFORMATION);
        } else if (id == IDC_UNINST) {
            if (MessageBoxW(hwnd,
                L"确定要卸载吗？\n\n"
                L"将删除虚拟环境、日志和持久化配置。\n"
                L"源代码不会被删除。",
                L"baibot - 卸载", MB_YESNO | MB_ICONWARNING) == IDYES) {

                _stop_webui();

                WCHAR cmd[MAX_PATH+32];
                wsprintfW(cmd, L"rmdir /s /q \"%s\"", g_venv);
                _wsystem(cmd);
                DeleteFileW(g_log);
                wsprintfW(cmd, L"%s\\config.json", g_dir); DeleteFileW(cmd);
                wsprintfW(cmd, L"%s\\plugin_config.json", g_dir); DeleteFileW(cmd);
                wsprintfW(cmd, L"%s\\app_config.json", g_dir); DeleteFileW(cmd);

                g_has_venv = 0;
                _refresh();
                MessageBoxW(hwnd,
                    L"卸载完成！\n\n源代码已保留，点击 [一键安装] 即可重新部署。",
                    L"baibot", MB_OK | MB_ICONINFORMATION);
            }
        }
        return 0;
    }

    case WM_NOTIFY: {
        NMHDR *nm = (NMHDR*)lp;
        if (nm->code == NM_CLICK || nm->code == NM_RETURN) {
            if (nm->idFrom == IDC_URL) {
                ShellExecuteW(hwnd, L"open", g_url_text, NULL, NULL, SW_SHOW);
                return 0;
            }
        }
        break;
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
    return DefWindowProcW(hwnd, msg, wp, lp);
}

/* ── WinMain ── */
int WINAPI wWinMain(HINSTANCE hInst, HINSTANCE hPrev, LPWSTR cmd, int nShow) {
    (void)hPrev; (void)cmd;

    _init_paths();

    INITCOMMONCONTROLSEX icc = { sizeof(icc), ICC_STANDARD_CLASSES | ICC_LINK_CLASS };
    InitCommonControlsEx(&icc);

    WNDCLASSW wc = {0};
    wc.lpfnWndProc   = _wndproc;
    wc.hInstance     = hInst;
    wc.hCursor       = LoadCursorW(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.lpszClassName = L"baibotPanel";
    RegisterClassW(&wc);

    HWND hwnd = CreateWindowW(L"baibotPanel", L"baibot · 小白",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT, 380, 250,
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
    while (GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    return (int)msg.wParam;
}
