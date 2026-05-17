"""
baibot — 主入口，支持命令系统
"""
from agent import Agent
from config import CONFIG, apply_model
from api_providers import list_all_models, find_model
from memory import get_session_summary

CMD_HELP = """
  /model [名称]    — 查看当前模型 或 切换模型
  /models          — 列出所有可用模型
  /new             — 开启新会话
  /session         — 查看当前会话信息
  /help            — 显示帮助
  /exit, /quit     — 退出
""".strip()


def handle_command(cmd: str, agent: Agent) -> bool:
    """返回 True 表示需要退出"""

    parts = cmd.strip().split(maxsplit=1)
    action = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if action in ["/exit", "/quit"]:
        return True

    elif action == "/help":
        print(CMD_HELP)

    elif action == "/model":
        if arg:
            found = find_model(arg)
            if found:
                pname, model, _ = found
                apply_model(pname, model)
                agent.reload_prompt()
                print(f"  ✓ 已切换到 {pname}/{model}")
            else:
                print(f"  ✗ 未找到模型 '{arg}'，用 /models 查看可用列表")
        else:
            print(f"  📌 当前: {CONFIG['provider']} / {CONFIG['model']}")

    elif action == "/models":
        print("  可用模型:")
        for m in list_all_models():
            print(f"    {m}")

    elif action == "/new":
        agent.reset_session()

    elif action == "/session":
        print(f"  {get_session_summary()}")

    else:
        print(f"  ✗ 未知命令 '{action}'，输入 /help 查看帮助")

    return False


if __name__ == "__main__":

    agent = Agent()

    while True:

        user_input = input("\nUSER > ")

        if not user_input.strip():
            continue

        if user_input.startswith("/"):
            should_exit = handle_command(user_input.strip(), agent)
            if should_exit:
                break
            continue

        agent.run(user_input)
