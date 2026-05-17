#!/usr/bin/env bash
set -e

# ============================================================
# baibot 一键部署脚本 (Linux)
# 用法: bash deploy.sh              → 交互菜单
#       bash deploy.sh start|cli|stop|restart|status|install|uninstall|service
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
LOG_FILE="$PROJECT_DIR/baibot.log"
PID_FILE="$PROJECT_DIR/baibot.pid"
PORT=7200

log()  { echo -e "${CYAN}[baibot]${NC} $1"; }
ok()   { echo -e "${GREEN}[  ok  ]${NC} $1"; }
warn() { echo -e "${YELLOW}[ warn ]${NC} $1"; }
err()  { echo -e "${RED}[ fail ]${NC} $1"; }

check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON=python3
    elif command -v python &>/dev/null; then
        PYTHON=python
    else
        err "未找到 Python，请先安装 Python 3.10+"
        exit 1
    fi

    local ver=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [ "$(echo "$ver" | cut -d. -f1)" -lt 3 ] || { [ "$(echo "$ver" | cut -d. -f1)" -eq 3 ] && [ "$(echo "$ver" | cut -d. -f2)" -lt 10 ]; }; then
        err "Python 版本过低 ($ver)，需要 3.10+"
        exit 1
    fi
    ok "Python $ver"
}

check_system() {
    if ! command -v apt-get &>/dev/null && ! command -v yum &>/dev/null && ! command -v apk &>/dev/null; then
        warn "未检测到 apt/yum/apk，请手动安装系统依赖"
        return
    fi

    local missing=""
    if ! command -v python3-venv &>/dev/null && ! $PYTHON -m venv --help &>/dev/null 2>&1; then
        missing="$missing python3-venv"
    fi

    if [ -n "$missing" ]; then
        warn "需要安装系统包: $missing"
        if [ "$(id -u)" -eq 0 ]; then
            if command -v apt-get &>/dev/null; then
                apt-get update -qq && apt-get install -y -qq $missing
            elif command -v yum &>/dev/null; then
                yum install -y -q $missing
            fi
        else
            warn "请用 root 权限运行: sudo bash deploy.sh"
            warn "或手动安装: apt install $missing"
        fi
    fi
}

create_venv() {
    if [ -d "$VENV_DIR" ]; then
        return
    fi
    log "创建虚拟环境..."
    $PYTHON -m venv "$VENV_DIR"
    ok "虚拟环境创建完成"
}

install_deps() {
    log "安装 Python 依赖..."
    "$VENV_DIR/bin/pip" install --upgrade pip -q
    "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt" -q
    ok "依赖安装完成"
}

ensure_env() {
    check_python
    check_system
    create_venv
    install_deps
}

install_service() {
    local service_file="/etc/systemd/system/baibot.service"

    if [ -f "$service_file" ]; then
        warn "systemd 服务已存在"
        return
    fi

    if [ "$(id -u)" -ne 0 ]; then
        warn "创建 systemd 服务需要 root 权限，请用 sudo 运行"
        return 1
    fi

    ensure_env

    log "创建 systemd 服务..."
    cat > "$service_file" << EOF
[Unit]
Description=baibot AI Assistant WebUI
After=network.target

[Service]
Type=simple
User=${SUDO_USER:-$USER}
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/python $PROJECT_DIR/server.py
Restart=on-failure
RestartSec=5
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable baibot
    ok "systemd 服务已创建并设为开机启动"
    echo ""
    echo -e "  ${GREEN}systemctl start baibot${NC}   启动"
    echo -e "  ${GREEN}systemctl stop baibot${NC}    停止"
    echo -e "  ${GREEN}systemctl status baibot${NC}  状态"
    echo -e "  ${GREEN}journalctl -u baibot -f${NC}  日志"
}

uninstall_service() {
    local service_file="/etc/systemd/system/baibot.service"

    if [ -f "$service_file" ]; then
        if [ "$(id -u)" -ne 0 ]; then
            warn "删除 systemd 服务需要 root 权限，请用 sudo 运行"
            return 1
        fi
        systemctl stop baibot 2>/dev/null || true
        systemctl disable baibot 2>/dev/null || true
        rm -f "$service_file"
        systemctl daemon-reload
        ok "systemd 服务已删除"
    else
        warn "未找到 systemd 服务"
    fi
}

get_ip() {
    local ip
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$ip" ]; then
        ip=$(ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127.0.0.1 | head -1)
    fi
    echo "${ip:-localhost}"
}

running() {
    [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

start_cli() {
    ensure_env
    echo ""
    log "启动命令行聊天模式..."
    echo ""
    cd "$PROJECT_DIR"
    exec "$VENV_DIR/bin/python" main.py
}

start_webui() {
    ensure_env

    if running; then
        local old_pid=$(cat "$PID_FILE")
        kill "$old_pid" 2>/dev/null || true
        rm -f "$PID_FILE"
        sleep 1
    fi

    log "启动 WebUI 服务..."
    cd "$PROJECT_DIR"
    nohup "$VENV_DIR/bin/python" server.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2

    if running; then
        local ip=$(get_ip)
        echo ""
        echo -e "  ╔══════════════════════════════════════╗"
        echo -e "  ║   ${GREEN}baibot WebUI 已启动${NC}               ║"
        echo -e "  ╠══════════════════════════════════════╣"
        echo -e "  ║                                      ║"
        echo -e "  ║   ${WHITE}本地访问:${NC}                          ║"
        printf "  ║   http://localhost:%-5d              ║\n" $PORT
        if [ "$ip" != "localhost" ] && [ "$ip" != "127.0.0.1" ]; then
        echo -e "  ║                                      ║"
        echo -e "  ║   ${WHITE}局域网访问:${NC}                        ║"
        printf "  ║   http://%s:%-5d     ║\n" "$ip" $PORT
        fi
        echo -e "  ║                                      ║"
        echo -e "  ╠══════════════════════════════════════╣"
        echo -e "  ║   ${YELLOW}返回菜单: bash deploy.sh${NC}            ║"
        echo -e "  ║   ${YELLOW}日志:     tail -f baibot.log${NC}      ║"
        echo -e "  ╚══════════════════════════════════════╝"
        echo ""
    else
        err "启动失败，查看日志: cat $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_server() {
    if ! running; then
        warn "服务未运行"
        return
    fi
    local pid=$(cat "$PID_FILE")
    if kill "$pid" 2>/dev/null; then
        ok "服务已停止 (PID: $pid)"
    fi
    rm -f "$PID_FILE"
}

restart_webui() {
    stop_server
    start_webui
}

show_status() {
    if running; then
        local pid=$(cat "$PID_FILE")
        local ip=$(get_ip)
        echo ""
        echo -e "  ${GREEN}运行中${NC}  PID: $pid  端口: $PORT"
        echo -e "  本地:   http://localhost:$PORT"
        [ "$ip" != "localhost" ] && [ "$ip" != "127.0.0.1" ] && echo -e "  局域网: http://$ip:$PORT"
        local uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
        [ -n "$uptime" ] && echo -e "  运行时间: $uptime"
        echo ""
    else
        echo ""
        echo -e "  ${YELLOW}未运行${NC}"
        echo ""
    fi
}

uninstall_all() {
    echo ""
    echo -e "${YELLOW}此操作将删除虚拟环境、PID 文件、日志和 systemd 服务${NC}"
    echo -e "${YELLOW}项目源代码不会被删除${NC}"
    echo ""
    read -p "确认卸载？输入 yes 继续: " confirm
    if [ "$confirm" != "yes" ]; then
        echo "已取消"
        return
    fi

    stop_server

    if [ "$(id -u)" -eq 0 ]; then
        uninstall_service
    else
        warn "跳过 systemd 服务删除（需要 root）"
    fi

    rm -rf "$VENV_DIR" 2>/dev/null || true
    rm -f "$PID_FILE" "$LOG_FILE" 2>/dev/null || true
    rm -f "$PROJECT_DIR/config.json" "$PROJECT_DIR/plugin_config.json" "$PROJECT_DIR/app_config.json" 2>/dev/null || true
    rm -rf "$PROJECT_DIR/__pycache__" "$PROJECT_DIR/tools/__pycache__" 2>/dev/null || true
    ok "卸载完成！项目源码保留在 $PROJECT_DIR"
}

# ============================================================
# 交互主菜单
# ============================================================

show_main_menu() {
    clear 2>/dev/null || true
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     baibot · 小白  控制面板     ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════╝${NC}"
    echo ""

    check_python

    if running; then
        local pid=$(cat "$PID_FILE")
        echo -e "  ${GREEN}● WebUI 运行中${NC}  (PID: $pid)  http://localhost:$PORT"
    else
        echo -e "  ${YELLOW}○ WebUI 未运行${NC}"
    fi

    echo ""
    echo -e "  ${WHITE}── 启动 ──${NC}"
    echo -e "  ${GREEN}[1]${NC} 命令行聊天"
    echo -e "  ${GREEN}[2]${NC} 启动 WebUI"
    echo ""
    echo -e "  ${WHITE}── 管理 ──${NC}"
    echo -e "  ${GREEN}[3]${NC} 重启 WebUI"
    echo -e "  ${GREEN}[4]${NC} 停止 WebUI"
    echo -e "  ${GREEN}[5]${NC} 查看状态"
    echo -e "  ${GREEN}[6]${NC} 查看日志"
    echo ""
    echo -e "  ${WHITE}── 系统 ──${NC}"
    echo -e "  ${GREEN}[7]${NC} 安装 systemd 开机自启"
    echo -e "  ${GREEN}[8]${NC} 卸载（删除 venv / 配置）"
    echo -e "  ${GREEN}[9]${NC} 更新依赖"
    echo ""
    echo -e "  ${GREEN}[0]${NC} 退出"
    echo ""
    read -p "请输入数字: " choice

    case "$choice" in
        1) start_cli ;;
        2) start_webui; press_enter ;;
        3) restart_webui; press_enter ;;
        4) stop_server; press_enter ;;
        5) show_status; press_enter ;;
        6) show_log; press_enter ;;
        7) install_service; press_enter ;;
        8) uninstall_all; press_enter ;;
        9) update_deps; press_enter ;;
        0) echo ""; exit 0 ;;
        *) err "无效输入"; press_enter ;;
    esac
}

show_log() {
    if [ -f "$LOG_FILE" ]; then
        echo ""
        tail -30 "$LOG_FILE"
        echo ""
    else
        warn "日志文件不存在"
    fi
}

update_deps() {
    ensure_env
    log "更新 Python 依赖..."
    "$VENV_DIR/bin/pip" install --upgrade pip -q
    "$VENV_DIR/bin/pip" install --upgrade -r "$PROJECT_DIR/requirements.txt" -q
    ok "依赖更新完成"
}

press_enter() {
    echo ""
    read -p "按 Enter 返回菜单..." _
    show_main_menu
}

# ============================================================
# 命令行参数兼容
# ============================================================

ACTION="${1:-menu}"

case "$ACTION" in
    menu)
        show_main_menu
        ;;
    cli)
        start_cli
        ;;
    start|webui)
        start_webui
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_webui
        ;;
    status)
        show_status
        ;;
    log)
        show_log
        ;;
    install)
        install_service
        ;;
    uninstall)
        uninstall_all
        ;;
    update)
        update_deps
        ;;
    *)
        echo "用法: bash deploy.sh [命令]"
        echo ""
        echo "  无参数      交互式控制面板菜单"
        echo "  cli         直接进入命令行聊天"
        echo "  start       后台启动 WebUI"
        echo "  stop        停止 WebUI"
        echo "  restart     重启 WebUI"
        echo "  status      查看运行状态"
        echo "  log         查看最近日志"
        echo "  install     注册 systemd 服务（需 root）"
        echo "  uninstall   卸载 venv / 配置 / systemd"
        echo "  update      更新 Python 依赖"
        ;;
esac
