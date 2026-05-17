#!/usr/bin/env bash
set -e

# ============================================================
# baibot 一键部署脚本 (Linux)
# 用法: bash deploy.sh [start|stop|status|install]
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
            warn "请用 root 权限运行: sudo bash deploy.sh install"
        fi
    fi
}

create_venv() {
    if [ -d "$VENV_DIR" ]; then
        ok "虚拟环境已存在，跳过创建"
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

install_service() {
    local service_file="/etc/systemd/system/baibot.service"
    local user="${SUDO_USER:-$USER}"

    if [ -f "$service_file" ]; then
        warn "systemd 服务已存在，跳过创建"
        return
    fi

    if [ "$(id -u)" -ne 0 ]; then
        warn "创建 systemd 服务需要 root 权限: sudo bash deploy.sh install"
        return
    fi

    log "创建 systemd 服务..."
    cat > "$service_file" << EOF
[Unit]
Description=baibot AI Assistant WebUI
After=network.target

[Service]
Type=simple
User=$user
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
    echo -e "  ${GREEN}启动:${NC} sudo systemctl start baibot"
    echo -e "  ${GREEN}停止:${NC} sudo systemctl stop baibot"
    echo -e "  ${GREEN}状态:${NC} sudo systemctl status baibot"
    echo -e "  ${GREEN}日志:${NC} sudo journalctl -u baibot -f"
}

get_ip() {
    local ip
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$ip" ]; then
        ip=$(ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127.0.0.1 | head -1)
    fi
    echo "${ip:-localhost}"
}

show_menu() {
    echo ""
    echo -e "${WHITE}请选择运行模式:${NC}"
    echo ""
    echo -e "  ${GREEN}[1]${NC} 命令行聊天  (terminal chat)"
    echo -e "  ${GREEN}[2]${NC} WebUI 界面  (浏览器访问)"
    echo ""
    read -p "请输入数字 (1 或 2): " choice

    case "$choice" in
        1)
            echo ""
            log "启动命令行聊天模式..."
            cd "$PROJECT_DIR"
            exec "$VENV_DIR/bin/python" main.py
            ;;
        2)
            start_webui
            ;;
        *)
            err "无效输入，请输入 1 或 2"
            show_menu
            ;;
    esac
}

start_webui() {
    # 先杀掉旧 PID
    if [ -f "$PID_FILE" ]; then
        local old_pid=$(cat "$PID_FILE")
        kill "$old_pid" 2>/dev/null || true
        rm -f "$PID_FILE"
    fi

    log "启动 WebUI 服务..."
    cd "$PROJECT_DIR"
    nohup "$VENV_DIR/bin/python" server.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2

    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        local ip=$(get_ip)
        echo ""
        echo -e "  ╔══════════════════════════════════════╗"
        echo -e "  ║   ${GREEN}baibot WebUI 已启动${NC}               ║"
        echo -e "  ╠══════════════════════════════════════╣"
        echo -e "  ║                                      ║"
        echo -e "  ║   ${WHITE}本地访问:${NC}                          ║"
        echo -e "  ║   http://localhost:$PORT                  ║"
        if [ "$ip" != "localhost" ] && [ "$ip" != "127.0.0.1" ]; then
        echo -e "  ║                                      ║"
        echo -e "  ║   ${WHITE}局域网访问:${NC}                        ║"
        echo -e "  ║   http://$ip:$PORT        ║"
        fi
        echo -e "  ║                                      ║"
        echo -e "  ╠══════════════════════════════════════╣"
        echo -e "  ║   ${YELLOW}停止:  bash deploy.sh stop${NC}          ║"
        echo -e "  ║   ${YELLOW}状态:  bash deploy.sh status${NC}        ║"
        echo -e "  ║   ${YELLOW}日志:  tail -f baibot.log${NC}          ║"
        echo -e "  ╚══════════════════════════════════════╝"
        echo ""
    else
        err "启动失败，查看日志: cat $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        warn "服务未运行"
        return
    fi
    local pid=$(cat "$PID_FILE")
    if kill "$pid" 2>/dev/null; then
        ok "服务已停止 (PID: $pid)"
    fi
    rm -f "$PID_FILE"
}

show_status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        local pid=$(cat "$PID_FILE")
        local ip=$(get_ip)
        echo ""
        echo -e "  ${GREEN}运行中${NC}  PID: $pid  端口: $PORT"
        echo -e "  本地: http://localhost:$PORT"
        [ "$ip" != "localhost" ] && [ "$ip" != "127.0.0.1" ] && echo -e "  局域网: http://$ip:$PORT"
        local uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
        [ -n "$uptime" ] && echo -e "  运行时间: $uptime"
        echo ""
    else
        echo -e "  ${YELLOW}未运行${NC}"
    fi
}

# ---- Main ----
echo ""
echo -e "${CYAN}╔══════════════════════════════════╗${NC}"
echo -e "${CYAN}║     baibot · 小白 一键部署     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════╝${NC}"
echo ""

check_python

ACTION="${1:-start}"

case "$ACTION" in
    install)
        check_system
        create_venv
        install_deps
        install_service
        echo ""
        ok "安装完成！运行 'bash deploy.sh start' 选择运行模式"
        ;;
    start)
        create_venv
        install_deps
        show_menu
        ;;
    stop)
        stop_server
        ;;
    restart)
        stop_server
        show_menu
        ;;
    status)
        show_status
        ;;
    service)
        install_service
        ;;
    cli)
        create_venv
        install_deps
        log "启动命令行聊天模式..."
        cd "$PROJECT_DIR"
        exec "$VENV_DIR/bin/python" main.py
        ;;
    *)
        echo "用法: bash deploy.sh [install|start|stop|restart|status|cli|service]"
        echo ""
        echo "  install   完整安装（创建 venv、安装依赖、注册 systemd 服务）"
        echo "  start     安装依赖后选择运行模式 (CLI 或 WebUI)"
        echo "  cli       直接进入命令行聊天模式"
        echo "  stop      停止后台 WebUI 服务"
        echo "  restart   停止并重新选择模式"
        echo "  status    查看运行状态"
        echo "  service   仅注册 systemd 服务（需 root）"
        ;;
esac
