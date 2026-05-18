<p align="center">
  <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMTExIiBzdHJva2Utd2lkdGg9IjEuNSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIvPjxwYXRoIGQ9Ik04IDE0czEuNSAyIDQgMiA0LTIgNC0yIi8+PGxpbmUgeDE9IjkiIHkxPSI5IiB4Mj0iOS4wMSIgeTI9IjkiLz48bGluZSB4MT0iMTUiIHkxPSI5IiB4Mj0iMTUuMDEiIHkyPSI5Ii8+PC9zdmc+" alt="logo" width="72" />
</p>

<h1 align="center">🤖 baibot · 小白</h1>
<p align="center"><strong>基于大语言模型的自主 AI 助手</strong></p>
<p align="center">支持工具调用 · 实时联网搜索 · 系统信息 · 天气预报 · Shell 命令 · 桌面 GUI · 文件操作</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-3.0+-black?logo=flask" alt="Flask" />
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License" />
</p>

---

## ✨ 为什么选择小白？

> 不是又一个 AI 聊天框。**小白是长在系统里的自主 Agent**，能动手就不废话。

小白拥有 **14 个内置工具**，覆盖桌面操控、联网搜索、天气预报、文件操作、Shell 命令等场景。收到用户意图后，它自行规划调用链——一次对话可以连续调用多轮工具，直到完成任务才输出精简结论。

### 🧠 越用越聪明的记忆系统

- **跨会话持久记忆**：用户偏好、习惯、历史任务自动沉淀，换会话不丢上下文
- **🚀 自我进化（Skill Memory）**：AI 完成任务后自动总结操作经验（如"启动程序优先搜 Get-StartApps"），存入高优先级记忆池，新会话直接复用——**越用越懂你**
- **智能遗忘**：低价值、长期未访问的记忆自动清理，保持记忆池高效

### 🛡️ 安全红线内置

- 临时文件强制写入系统 `%TEMP%`，不污染工作目录
- API 密钥、Token、配置文件**绝对不可泄露**——即使用户要求查看也不行
- 破坏性操作需二次确认；不下载不执行不信任代码

### 🌤 多源天气 · 和风天气首发

- 内置 **wttr.in** + **和风天气** 双引擎，覆盖全球城市
- 和风天气支持 **3000+ 中国市县区 + 海外 20 万城市**，实时 + 未来 3~30 天预报
- 数据 5-20 分钟更新，温度 / 体感 / 风力风向 / 湿度 / 气压 / 紫外线 / 日出日落一应俱全

### 🔌 插件化 · 即插即用

- 工具模块声明 `CONFIG_SCHEMA` 即可在 WebUI 自动出现设置面板
- 支持 `apply_config()` 热更新，改 API Key 不用重启
- 规范简洁，一个文件就是一个插件

### 🎛 多模型 · 自由切换

- 支持任意 OpenAI 兼容 API，一个窗口管理多个提供商
- **一键自动获取模型列表**，多选批量添加，不用手打模型名
- 设置页实时切换默认模型，立即生效

### 🖥 桌面即平台

- PowerShell / Shell 无缝执行，Windows 启动应用自动搜索开始菜单 → 注册表 → 常用路径
- GUI 自动化：模拟键盘输入、快捷键、鼠标点击、窗口聚焦
- 写文件支持指定桌面 / 自定义路径，生成 HTML / Python / JSON 不在话下

---

## 🖥 WebUI 预览

启动后打开 `http://localhost:7200`，在浏览器中与小白对话，实时查看工具调用进度和 Token 消耗。

| 特性 | 说明 |
|------|------|
| **侧边栏** | 历史会话管理，支持新建 / 加载 / 删除 |
| **实时进度** | 工具调用过程以步骤形式逐条展示 |
| **暗色主题** | 点击右上角 🌙/☀️ 切换，偏好自动保存 |
| **设置页面** | 独立 `/settings` 页面：基本信息、大模型设置、插件管理 |
| **Token 统计** | 每条回复底部显示输入 / 输出 / 合计 Token |

---

## 📋 运行环境

### 必需

| 项 | 最低版本 | 说明 |
|---|---|---|
| Python | `3.10+` | [官网下载](https://www.python.org/downloads/) |
| 操作系统 | Windows 10+ / macOS / Linux | Windows 桌面自动化需额外支持 |
| 网络 | 需联网 | LLM API + WebUI 本机运行 |

### 可选（桌面自动化）

| 依赖 | 用途 |
|------|------|
| `pyautogui` | GUI 输入、快捷键、窗口操作 |
| `pygetwindow` | 窗口查找与聚焦 |

- Windows 已内置
- macOS 需在 **系统设置 → 隐私与安全性 → 辅助功能** 中授权
- Linux 需 `python3-tk` / `scrot`

### API 密钥

| 密钥 | 用途 | 获取 |
|------|------|------|
| LLM API Key | 大模型调用 | [OpenAI](https://platform.openai.com) 等兼容接口 |
| Tavily API Key | 联网搜索 | [tavily.com](https://tavily.com) 免费额度 |

> 密钥可在 WebUI 设置页直接配置，支持热更新。

---

## 🚀 快速开始

### 🪟 Windows 一键部署（推荐）

```batch
git clone https://github.com/mubaiqq/baibot.git
cd agent

# 双击 deploy.exe
deploy.exe
```

**首次运行**会自动弹出设置向导：检测 Python → 创建虚拟环境 → 安装依赖 → 进度条完成。

**后续运行**直接进入 GUI 控制面板，点击即可启动/停止 WebUI、查看日志、卸载。

| 操作 | 说明 |
|------|------|
| 双击 `deploy.exe` | GUI 控制面板（首次自动安装） |
| `Start WebUI` | 后台启动 WebUI |
| `Stop WebUI` | 停止 WebUI |
| `View Log` | 用记事本打开日志 |
| `Uninstall` | 删除 venv / 日志 / 配置，保留源码 |

> `deploy.exe` 仅 82KB，纯 C 编写，无任何运行时依赖。
>
> 从源码编译：`gcc -mwindows -O2 -municode deploy.c -o deploy.exe -lcomctl32 -lshlwapi`

### 🐧 Linux 一键部署（推荐）
```bash
# 1. 重新从 GitHub 克隆项目
git clone https://github.com/mubaiqq/baibot.git

# 2. 进入项目目录
cd baibot

# 3. 赋予部署脚本权限并执行全新部署
chmod +x deploy.sh
bash deploy.sh start
 
```

| 命令 | 说明 |
|------|------|
| `bash deploy.sh` | 打开交互控制面板 |
| `bash deploy.sh cli` | 直接进入命令行聊天 |
| `bash deploy.sh start` | 后台启动 WebUI |
| `bash deploy.sh stop` | 停止 WebUI |
| `bash deploy.sh restart` | 重启 WebUI |
| `bash deploy.sh status` | 查看运行状态 |
| `bash deploy.sh log` | 查看最近日志 |
| `bash deploy.sh update` | 更新 Python 依赖 |
| `sudo bash deploy.sh install` | 注册 systemd 服务（开机自启） |
| `bash deploy.sh uninstall` | 卸载（删除 venv / 配置 / 缓存） |

### 🍎 macOS 部署

```bash
git clone https://github.com/mubaiqq/baibot.git
cd agent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# macOS GUI 自动化需额外授权
# 系统设置 → 隐私与安全性 → 辅助功能 → 添加终端.app

python server.py
```

### 手动安装（通用）

```bash
git clone <your-repo-url>
cd agent
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
python server.py
```

浏览器打开 **http://localhost:7200** 即可开始对话。

> 终端命令行模式：`python main.py`

### 安装常见问题

| 问题 | 解决方案 |
|------|----------|
| PowerShell 激活失败 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| pip install 报错 | 确认使用虚拟环境中的 pip：`.venv\Scripts\pip.exe install -r requirements.txt` |
| 端口被占用 | 修改 `server.py` 中 `port=7200` 为其他端口 |

---

## 🌐 WebUI 功能

### 聊天主界面

| 位置 | 功能 |
|------|------|
| 左上方 🟢 | 状态指示（绿色待机 / 黄色脉冲处理中） |
| 左侧菜单 | 历史会话列表，点击加载 |
| `＋ 新会话` | 清空上下文，前后端同步重置 |
| 右上 `模型` | 查看可用模型列表 |
| 右上 `清屏` | 清空当前聊天区域 |
| 右上 `☀/🌙` | 主题切换 |
| 右上 `⚙` | 进入设置页面 |
| 对话气泡 | 用户蓝色 / 助手白色，支持 Markdown 渲染 |

### 设置页面 (`/settings`)

**基本信息** — 修改 Agent 名称、当前模型（本次会话）、最大步数、温度，保存后立即生效。

**大模型设置** — 设置默认模型（新会话 & 重启后默认使用）；编辑器直接修改提供商 JSON 配置，包含 API Key、Base URL、模型列表等。

**插件管理** — 卡片式展示所有工具插件，有设置按钮的插件可点击配置（如联网搜索的 Tavily Key）。

### 命令

聊天框支持 `/` 前缀命令：

| 命令 | 说明 |
|------|------|
| `/model` | 查看当前模型 |
| `/model <名称>` | 切换模型（如 `/model gpt-4o`） |
| `/models` | 列出所有可用模型 |
| `/new` | 开启新会话 |
| `/session` | 查看当前会话信息 |
| `/help` | 显示帮助 |

---

## 🤖 核心能力

| 类型 | 示例 |
|------|------|
| **联网搜索** | "今天热搜" / "金价多少" |
| **天气查询** | "我这里天气" / "明天杭州天气" |
| **系统信息** | "查看电脑配置" |
| **当前时间** | "现在几点" |
| **数学计算** | "计算 123 × 456" |
| **打开文件** | "打开桌面的报告.pdf" |
| **创建文件** | "在桌面创建 hello.html" |
| **桌面操作** | "全选" / "复制" / "粘贴" / "保存" |
| **输入文字** | "输入 今天天气真好" |
| **启动应用** | "打开微信"（自动搜索开始菜单和安装路径） |
| **查看进程** | "查看当前进程" |
| **音量调节** | "音量调高" / "静音" |
| **电量查询** | "电量多少" |

---

## � 工作原理

```
用户输入
  │
  ├─ 1. 规则路由器（router.py）
  │     关键词匹配 → 直接执行工具
  │
  ├─ 2. 直接工具推断
  │     确定性查询 → 跳过 LLM
  │
  └─ 3. LLM 推理（agent.run）
        复杂任务 → LLM 选择工具
```

### 工具失败自恢复

任何工具失败，AI 自动换方式重试（最多 3 次）：

```
打开微信：
  → ① 搜索开始菜单 Get-StartApps
  → ② 搜索注册表 App Paths
  → ③ 搜索常见安装目录
  → ④ Start-Process 启动
```

### 记忆系统

- 自动提取用户偏好和对话要点
- 跨会话持久化（`memories/` 目录）
- 相似记忆自动去重合并
- 30 天未访问的低价值记忆自动遗忘

---

## 📁 项目结构

```text
agent/
├── main.py              # CLI 入口 + 命令系统
├── server.py            # Flask WebUI 服务（端口 7200）
├── webui.html           # WebUI 聊天前端
├── settings.html        # 设置页面（基本信息 / 大模型 / 插件）
├── config.py            # 配置中心 + System Prompt 构建
├── agent.py             # Agent 核心：推理、兜底、收敛
├── router.py            # 规则级意图路由
├── memory.py            # 记忆系统
├── api_providers.py     # 多 API 多模型配置（支持持久化）
├── config.json          # 提供商 + 默认模型持久化配置
├── plugin_config.json   # 插件配置持久化
├── app_config.json      # Agent 参数持久化
├── requirements.txt     # Python 依赖
├── deploy.sh            # Linux 一键部署脚本
├── deploy.bat           # Windows 控制面板（调用 deploy.exe）
├── deploy.c             # Windows GUI 控制面板源码（C / Win32）
├── deploy.exe           # Windows GUI 控制面板（82KB，预编译）
├── scripts/             # AI 自动生成的 Python 脚本
└── tools/
    ├── __init__.py       # 工具注册 + Schema + 配置收集
    ├── calculator.py     # 数学计算
    ├── web_search.py     # 联网搜索（Tavily）
    ├── fetch_url.py      # 网页抓取
    ├── time_tool.py      # 日期时间
    ├── system_info.py    # 系统信息
    ├── weather.py        # IP 天气 + 城市预报
    ├── shell_exec.py     # Shell 命令
    ├── gui_action.py     # GUI 自动化
    ├── open_file.py      # 文件打开
    └── write_file.py     # 文件写入
```

---

## 🔌 插件开发规范

插件系统支持**配置自动发现**：只需在工具模块中声明 `CONFIG_SCHEMA` 和 `apply_config()`，WebUI 会自动识别并渲染设置界面。

### 最小插件模板

```python
# tools/my_plugin.py

# 1. 声明可配置字段（可选）
CONFIG_SCHEMA = {
    "API_KEY": {
        "label": "API 密钥",           # 前端显示的标签
        "type": "password",             # text / password
        "description": "前往 xxx.com 获取",  # 提示文字
        "default": "",                  # 默认值
    },
    "MAX_RESULTS": {
        "label": "最大结果数",
        "type": "text",
        "description": "单次查询返回上限",
        "default": "10",
    }
}

# 2. 应用配置回调（可选 — 有 CONFIG_SCHEMA 时必须提供）
def apply_config(config: dict):
    """前端保存时调用，config = {字段名: 新值}"""
    global API_KEY, _client
    if "API_KEY" in config and config["API_KEY"]:
        API_KEY = config["API_KEY"]
        _client = SomeClient(api_key=API_KEY)
    if "MAX_RESULTS" in config:
        MAX_RESULTS = int(config["MAX_RESULTS"])

# 3. 工具函数
def my_tool(param: str):
    """工具描述"""
    return {"success": True, "data": "..."}
```

### 注册工具

在 `tools/__init__.py` 中：

```python
from .my_plugin import my_tool

TOOLS_MAP = {
    # ... 已有工具
    "my_tool": my_tool,
}

TOOLS = [
    # ... 已有工具
    {
        "type": "function",
        "function": {
            "name": "my_tool",
            "description": "工具描述",
            "parameters": {
                "type": "object",
                "properties": {
                    "param": {"type": "string", "description": "参数说明"}
                },
                "required": ["param"]
            }
        }
    },
]
```

### 约定一览

| 标记 | 必须 | 说明 |
|------|:--:|------|
| `CONFIG_SCHEMA` | 有配置则必须 | dict，key 为字段名，value 含 label / type / description / default |
| `apply_config(config)` | 有 CONFIG_SCHEMA 则必须 | 接收 dict，更新全局变量，重构客户端实例 |
| `TOOLS_MAP` 注册 | ✅ | `"函数名": 函数引用` |
| `TOOLS` 注册 | ✅ | OpenAI Function Schema 格式 |

### 自动发现流程

```
tools/__init__.py 启动时
  → 遍历 TOOLS_MAP 中每个函数所在模块
  → 检查是否有 CONFIG_SCHEMA
  → 有 → 收集到 TOOL_CONFIG_SCHEMAS / TOOL_APPLY_CONFIG
  → WebUI 读取 → 卡片显示"设置"按钮
  → 用户保存 → POST /api/plugin-config → apply_config() → 持久化到 plugin_config.json
```

> **只需在 `.py` 文件中声明，WebUI 无需任何改动，自动适配。**

---

## 🔧 配置说明

### 持久化

设置页面修改的配置会写入以下文件，重启后自动恢复：

| 文件 | 内容 |
|------|------|
| `config.json` | 提供商列表 + 默认模型 |
| `app_config.json` | Agent 名称、最大步数、温度 |
| `plugin_config.json` | 各插件配置字段 |

> 原始 `api_providers.py` 中的值仅作首次启动的默认值，不会被修改。

### Agent 参数

在 `agent.py` 中可调整：

```python
MAX_CONTEXT_MESSAGES = 6      # 工作记忆条数
MAX_TOOL_CONTENT = 1500       # 单次工具结果上限（字符）
MAX_TOTAL_TOOL_CALLS = 8      # 单轮最大工具调用次数
```

### 记忆系统

- 存储位置：`memories/{user_hash}.json`
- Upsert 相似度阈值：`0.35`
- 自动遗忘周期：`30 天`

---

## 📄 License

MIT
