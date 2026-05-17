"""
Advanced Agent Core
- Working Memory
- Retrieval Memory
- Context Compression
- Memory Extraction
"""

import json
import sys
from types import SimpleNamespace
from typing import Dict, List

from config import CONFIG, client, build_system_prompt
from tools import TOOLS, TOOLS_MAP
from router import detect

from memory import (
    ensure_session,
    new_session,
    record_message,
    retrieve_relevant_memories,
    extract_memories_from_conversation,
    merge_or_create_memory,
    summarize_messages,
    get_session_summary,
    save_session_summary,
)


class Agent:

    # Context budget
    MAX_CONTEXT_MESSAGES = 6
    MAX_TOOL_CONTENT = 1500

    def __init__(self):

        # Working Memory
        self.recent_messages: List[Dict] = []

        # Tool dedup (per-run)
        self._run_args_seen: set[str] = set()

        # Cross-run search/fetch/open history
        self.search_history: set[str] = set()
        self.fetch_history: set[str] = set()
        self._recent_opened_files: set[str] = set()

        # Token
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

        # Stream (set by run())
        self._stream = None

    def _emit(self, event_type: str, data: str):
        if self._stream:
            self._stream.emit(event_type, data)
        else:
            print(data)

    # =====================================================
    # RESET
    # =====================================================

    def reset_session(self):

        new_session()

        self.recent_messages = []
        self.search_history.clear()
        self.fetch_history.clear()
        self._recent_opened_files.clear()
        self._run_args_seen.clear()

        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def reload_prompt(self):
        """切换模型后刷新工作记忆，让系统提示词重新生成"""
        self.recent_messages = []
        self.search_history.clear()
        self.fetch_history.clear()
        self._recent_opened_files.clear()
        self._run_args_seen.clear()

    # =====================================================
    # BUILD MESSAGES
    # =====================================================

    def _build_messages(self, user_input: str):

        # Retrieval Memory
        retrieved = retrieve_relevant_memories(
            user_input,
            top_k=6
        )

        memory_text = ""

        if retrieved:
            memory_text = "\n".join([
                f"- {m['content']}"
                for m in retrieved
            ])

        # Session Summary
        session_summary = get_session_summary()

        # System Prompt
        system_prompt = build_system_prompt(
            memory_text + "\n\n" + session_summary
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # Working Memory（只保留最近 N 条，过滤旧 final answer）
        recent = []
        for m in self.recent_messages[-self.MAX_CONTEXT_MESSAGES:]:
            if m.get("role") == "tool":
                continue
            if m.get("role") == "assistant" and m.get("tool_calls"):
                continue
            if m.get("role") == "assistant" and not m.get("tool_calls") and not (m.get("content") or "").strip():
                continue
            recent.append(m)
        messages.extend(recent)

        # Current User Input
        messages.append({
            "role": "user",
            "content": user_input
        })

        return messages

    # =====================================================
    # SAFE API CALL (with retry)
    # =====================================================

    API_MAX_RETRIES = 3

    def _call_api(self, messages: list):
        for attempt in range(self.API_MAX_RETRIES):
            use_tools = (
                TOOLS if attempt < self.API_MAX_RETRIES - 1 else []
            )
            try:
                response = client.chat.completions.create(
                    model=CONFIG["model"],
                    messages=messages,
                    tools=use_tools,
                    tool_choice="auto" if use_tools else None,
                    max_tokens=4096,
                    temperature=CONFIG["temperature"],
                )
            except Exception as e:
                if attempt < self.API_MAX_RETRIES - 1:
                    self._emit("process", f"⟳ API 异常，重试 {attempt + 1}/{self.API_MAX_RETRIES - 1}...")
                    continue
                self._emit("process", f"✗ API 异常: {e}")
                return None

            if response.choices and response.choices[0].message:
                msg = response.choices[0].message
                if response.usage:
                    self.total_prompt_tokens += response.usage.prompt_tokens
                    self.total_completion_tokens += response.usage.completion_tokens
                return msg

            if response.usage:
                self.total_prompt_tokens += response.usage.prompt_tokens
                self.total_completion_tokens += response.usage.completion_tokens

            base = getattr(response, "base_resp", None)
            if base and base.get("status_code") and base["status_code"] != 0:
                self._emit("process", f"✗ API 返回错误: {base.get('status_msg', base['status_code'])}")
                return None

            return SimpleNamespace(content="", tool_calls=None)

        return None

    # =====================================================
    # RUN
    # =====================================================

    def run(self, user_input: str, stream=None):

        self._stream = stream

        ensure_session()

        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

        self._run_args_seen.clear()

        routed = detect(user_input)

        self.recent_messages.append({
            "role": "user",
            "content": user_input
        })

        messages = self._build_messages(user_input)

        if routed:
            self._emit("match", f"路由匹配: {[r['name'] for r in routed]}")
            messages = self._execute_initial_tools(routed, messages)

        final_reply = self._llm_loop(user_input, messages)

        self._after_response()
        return final_reply

    def _execute_initial_tools(self, tools_to_run: List[dict], messages: list) -> list:
        """Execute routed/direct tools and append tool results to messages."""
        for item in tools_to_run:
            tool_name = item["name"]
            tool_args = item["args"]

            args_sig = f"{tool_name}|{json.dumps(tool_args, sort_keys=True, ensure_ascii=False)}"
            if args_sig in self._run_args_seen:
                continue
            self._run_args_seen.add(args_sig)

            if tool_name == "open_file":
                path = tool_args.get("path") or tool_args.get("filename", "")
                if path and path in self._recent_opened_files:
                    self._emit("process", f"跳过重复打开: {path}")
                    continue

            tool_func = TOOLS_MAP.get(tool_name)
            if tool_func:
                try:
                    tool_result = tool_func(**tool_args)
                except Exception as e:
                    tool_result = {"success": False, "error": str(e)}
            else:
                tool_result = {"success": False, "error": f"未知工具: {tool_name}"}

            self._emit("tool", f"[初始] {tool_name}")

            summary = self._summarize(tool_name, tool_result)
            if tool_result.get("success"):
                self._emit("tool_ok", summary)
            else:
                self._emit("tool_fail", summary)

            if tool_name == "open_file" and tool_result.get("success"):
                path = tool_args.get("path") or tool_args.get("filename", "")
                if path:
                    self._recent_opened_files.add(path)

            compressed = self._compress_tool_result(tool_name, tool_result)

            fake_id = f"init_{tool_name}_{len(messages)}"
            fake_assistant = {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": fake_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args, ensure_ascii=False)
                    }
                }]
            }
            messages.append(fake_assistant)
            self.recent_messages.append(fake_assistant)

            tool_message = {
                "role": "tool",
                "tool_call_id": fake_id,
                "name": tool_name,
                "content": compressed
            }
            messages.append(tool_message)
            self.recent_messages.append(tool_message)

        return messages

    def _llm_loop(self, user_input: str, messages: list) -> str:
        """Multi-step LLM loop: AI can call tools repeatedly, up to max_steps times."""
        total_tool_calls = 0

        for step in range(CONFIG["max_steps"]):

            if total_tool_calls >= CONFIG["max_steps"]:
                self._emit("process", "⏹ 工具调用已达上限，生成最终回复")
                return self._finalize()

            message = self._call_api(messages)

            if message is None:
                self._emit("process", "⟳ API 无响应，尝试降级生成回复...")
                return self._finalize()

            assistant_message = {
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls,
            }

            if not message.tool_calls:
                final_reply = message.content or ""

                if not final_reply.strip():
                    fb = self._tool_fallback()
                    if "请输入具体操作指令" in fb:
                        self._emit("result", "你好！我是小白，有什么可以帮你的吗？😊")
                    else:
                        self._emit("result", fb)
                    return ""
                else:
                    messages.append(assistant_message)
                    self.recent_messages.append(assistant_message)

                self._emit("result", final_reply)
                return final_reply

            messages.append(assistant_message)
            self.recent_messages.append(assistant_message)

            for tool_call in message.tool_calls:

                total_tool_calls += 1

                if total_tool_calls > CONFIG["max_steps"]:
                    self._emit("process", "⏹ 工具调用已达上限，生成最终回复")
                    return self._finalize()

                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                args_sig = f"{tool_name}|{json.dumps(tool_args, sort_keys=True, ensure_ascii=False)}"
                if args_sig in self._run_args_seen:
                    tool_result = {
                        "success": False,
                        "error": f"本轮已执行过相同操作：{tool_name}，跳过重复调用"
                    }
                    self._emit("tool", f"[{step + 1}] {tool_name}")
                    self._emit("tool_fail", self._summarize(tool_name, tool_result))
                    compressed = self._compress_tool_result(tool_name, tool_result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": compressed
                    })
                    self.recent_messages.append(messages[-1])
                    continue
                self._run_args_seen.add(args_sig)

                if tool_name == "web_search":
                    query = tool_args.get("query", "")
                    if query and query in self.search_history:
                        tool_result = {"success": False, "error": f"重复搜索: {query}"}
                        self._emit("tool", f"[{step + 1}] {tool_name}")
                        self._emit("tool_fail", self._summarize(tool_name, tool_result))
                        compressed = self._compress_tool_result(tool_name, tool_result)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": compressed
                        })
                        self.recent_messages.append(messages[-1])
                        continue
                    if query:
                        self.search_history.add(query)

                if tool_name == "fetch_url":
                    url = tool_args.get("url", "")
                    if url and url in self.fetch_history:
                        tool_result = {"success": False, "error": f"重复抓取: {url}"}
                        self._emit("tool", f"[{step + 1}] {tool_name}")
                        self._emit("tool_fail", self._summarize(tool_name, tool_result))
                        compressed = self._compress_tool_result(tool_name, tool_result)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": compressed
                        })
                        self.recent_messages.append(messages[-1])
                        continue
                    if url:
                        self.fetch_history.add(url)

                if tool_name == "open_file":
                    path = tool_args.get("path") or tool_args.get("filename", "")
                    if path and path in self._recent_opened_files:
                        tool_result = {"success": False, "error": f"已在本次会话中打开过: {path}"}
                        self._emit("tool", f"[{step + 1}] {tool_name}")
                        self._emit("tool_fail", self._summarize(tool_name, tool_result))
                        compressed = self._compress_tool_result(tool_name, tool_result)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": compressed
                        })
                        self.recent_messages.append(messages[-1])
                        continue

                tool_func = TOOLS_MAP.get(tool_name)
                if tool_func:
                    try:
                        tool_result = tool_func(**tool_args)
                    except Exception as e:
                        tool_result = {"success": False, "error": str(e)}
                else:
                    tool_result = {"success": False, "error": f"未知工具: {tool_name}"}

                self._emit("tool", f"[{step + 1}] {tool_name}")

                summary = self._summarize(tool_name, tool_result)
                if tool_result.get("success"):
                    self._emit("tool_ok", summary)
                else:
                    self._emit("tool_fail", summary)

                compressed = self._compress_tool_result(tool_name, tool_result)

                if tool_name == "open_file" and tool_result.get("success"):
                    path = tool_args.get("path") or tool_args.get("filename", "")
                    if path:
                        self._recent_opened_files.add(path)

                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": compressed
                }

                if self._is_duplicate_obs(tool_name, compressed):
                    continue

                messages.append(tool_message)
                self.recent_messages.append(tool_message)

        return self._finalize()

    # =====================================================
    # AFTER RESPONSE
    # =====================================================

    def _after_response(self):

        record_message()

        memories = extract_memories_from_conversation(
            self.recent_messages
        )

        for memory in memories:
            merge_or_create_memory(memory)

        if len(self.recent_messages) > 12:

            old_messages = self.recent_messages[:-6]

            summary = summarize_messages(
                old_messages
            )

            save_session_summary(summary)

            self.recent_messages = (
                self.recent_messages[-6:]
            )

        self._print_token_summary()

    # =====================================================
    # TOOL RESULT COMPRESSION
    # =====================================================

    def _compress_tool_result(
        self,
        tool_name: str,
        result: dict
    ) -> str:

        if tool_name == "shell_exec":
            return json.dumps(
                {
                    "success": result.get("success", False),
                    "exit_code": result.get("exit_code"),
                    "stdout": (result.get("stdout", "")[:800]),
                    "stderr": (result.get("stderr", "")[:200]),
                    "summary": result.get("summary", ""),
                },
                ensure_ascii=False
            )

        if not result.get("success"):
            error = str(result.get("error", "失败"))
            return json.dumps(
                {"success": False, "error": error[:500]},
                ensure_ascii=False
            )

        if tool_name == "web_search":
            compressed = []
            for item in result.get("results", [])[:5]:
                compressed.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", "")[:500],
                    "url": item.get("url", "")
                })
            return json.dumps(
                {"success": True, "results": compressed},
                ensure_ascii=False
            )

        if tool_name == "fetch_url":
            content = result.get("content", "")
            return json.dumps(
                {
                    "success": True,
                    "content": content[:self.MAX_TOOL_CONTENT],
                    "truncated": len(content) > self.MAX_TOOL_CONTENT
                },
                ensure_ascii=False
            )

        if tool_name == "calculator":
            return json.dumps(
                {"success": True, "result": result.get("result")},
                ensure_ascii=False
            )

        if tool_name == "gui_action":
            return json.dumps(
                {
                    "success": result.get("success", False),
                    "summary": result.get("summary", ""),
                },
                ensure_ascii=False
            )

        if tool_name == "open_file":
            return json.dumps(
                {
                    "success": result.get("success", False),
                    "path": result.get("path", ""),
                    "summary": result.get("summary", ""),
                },
                ensure_ascii=False
            )

        if tool_name == "write_file":
            return json.dumps(
                {
                    "success": result.get("success", False),
                    "path": result.get("path", ""),
                    "bytes": result.get("bytes", 0),
                    "summary": result.get("summary", ""),
                },
                ensure_ascii=False
            )

        if tool_name in {"get_weather_forecast", "get_local_weather_forecast"}:
            return json.dumps(result, ensure_ascii=False)

        raw = json.dumps(result, ensure_ascii=False)
        if len(raw) > self.MAX_TOOL_CONTENT:
            truncated = {
                "success": True,
                "summary": raw[:self.MAX_TOOL_CONTENT],
                "truncated": True
            }
            return json.dumps(truncated, ensure_ascii=False)

        return raw

    # =====================================================
    # TOOL CONVERGENCE
    # =====================================================

    def _has_enough_information(self, tool_name: str, result: dict) -> bool:
        if not result.get("success"):
            return False

        if tool_name in {
            "web_search",
            "get_current_time",
            "get_system_info",
            "get_weather_by_ip",
            "get_weather_forecast",
            "get_local_weather_forecast",
            "fetch_url",
            "write_file",
            "calculator",
        }:
            return True

        if result.get("location") and result.get("weather"):
            return True

        return False

    def _infer_direct_tools(self, user_input: str) -> List[dict]:
        """给常见信息查询做确定性兜底，避免模型不调工具时直接失败。"""
        text = user_input.lower()

        system_keywords = ["系统信息", "电脑系统", "电脑配置", "电脑状态", "电脑信息", "硬件信息", "机器配置", "当前电脑", "电脑硬件", "本机配置"]
        if any(k in user_input for k in system_keywords):
            return [{"name": "get_system_info", "args": {}}]

        time_keywords = ["当前时间", "现在时间", "现在几点", "几点了", "今天几号", "当前日期"]
        if any(k in user_input for k in time_keywords):
            return [{"name": "get_current_time", "args": {}}]

        weather_keywords = ["天气", "气温", "下雨", "温度"]
        if any(k in user_input for k in weather_keywords):
            city = self._extract_weather_city(user_input)
            day = self._extract_weather_day(user_input)
            if city:
                return [{
                    "name": "get_weather_forecast",
                    "args": {"city": city, "day": day}
                }]
            forecast_keywords = ["明天", "后天", "未来", "预报", "周", "星期"]
            local_keywords = ["我这里", "本地", "当前位置", "当前", "现在", "这里", "我这", "我的ip", "ip", "ip138"]
            if any(k in user_input for k in forecast_keywords) and any(k in user_input for k in local_keywords):
                return [{
                    "name": "get_local_weather_forecast",
                    "args": {"day": day}
                }]
            if any(k in user_input for k in forecast_keywords) or not any(k in user_input for k in local_keywords):
                return [{
                    "name": "web_search",
                    "args": {"query": f"{user_input} 天气预报"}
                }]
            return [{"name": "get_weather_by_ip", "args": {}}]

        gold_keywords = ["金价", "黄金", "回收价"]
        if any(k in user_input for k in gold_keywords):
            return [{
                "name": "web_search",
                "args": {"query": f"{user_input} 今日 黄金 每克 回收价格"}
            }]

        market_keywords = ["原油", "石油", "油价", "wti", "brent", "布伦特"]
        if any(k in user_input.lower() for k in market_keywords):
            return [{
                "name": "web_search",
                "args": {"query": f"{user_input} WTI 布伦特 原油 实时价格 每桶"}
            }]

        battery_keywords = ["电池", "电量", "还剩多少电", "电源状态", "拔电"]
        if any(k in user_input for k in battery_keywords):
            return [{
                "name": "shell_exec",
                "args": {"command": "powershell -Command \"$b=Get-CimInstance Win32_Battery;if($b){Write-Host ('电量: {0}% | 状态: {1}' -f $b.EstimatedChargeRemaining, $(switch($b.BatteryStatus){1{'使用中(未充电)'}2{'充电中'}3{'已充满'}default{'未知'}}))}else{Write-Host '未检测到电池(可能为台式机)'}\""}
            }]

        volume_keywords = ["音量", "声音", "调到", "调大", "调小", "静音", "喇叭"]
        if any(k in user_input for k in volume_keywords):
            import re
            num_match = re.search(r'(\d+)', user_input)
            target = int(num_match.group(1)) if num_match else 50
            if any(k in user_input for k in ["静音", "关闭声音"]):
                cmd = "powershell -Command \"Add-Type -Name 'VM' -MemberDefinition '[DllImport(\\\"user32.dll\\\")]public static extern void keybd_event(byte v,byte s,uint f,UIntPtr x);' -PassThru|Out-Null;[VM]::keybd_event(0xAD,0,0,0);Write-Host '已切换静音'\""
            elif any(k in user_input for k in ["调大", "加大", "增大"]):
                steps = max(1, target // 2) if num_match else 5
                cmd = f"powershell -Command \"Add-Type -Name 'VD' -MemberDefinition '[DllImport(\\\"user32.dll\\\")]public static extern void keybd_event(byte v,byte s,uint f,UIntPtr x);' -PassThru|Out-Null;for($i=0;$i -lt {steps};$i++){{[VD]::keybd_event(0xAF,0,0,0)}};Write-Host '音量已调大'\""
            elif any(k in user_input for k in ["调小", "减小", "降低"]):
                steps = max(1, target // 2) if num_match else 5
                cmd = f"powershell -Command \"Add-Type -Name 'VU' -MemberDefinition '[DllImport(\\\"user32.dll\\\")]public static extern void keybd_event(byte v,byte s,uint f,UIntPtr x);' -PassThru|Out-Null;for($i=0;$i -lt {steps};$i++){{[VU]::keybd_event(0xAE,0,0,0)}};Write-Host '音量已调小'\""
            else:
                cmd = f"powershell -Command \"Add-Type -Name 'VS' -MemberDefinition '[DllImport(\\\"user32.dll\\\")]public static extern void keybd_event(byte v,byte s,uint f,UIntPtr x);' -PassThru|Out-Null;for($i=0;$i -lt 50;$i++){{[VS]::keybd_event(0xAE,0,0,0)}};Start-Sleep -Milliseconds 200;for($i=0;$i -lt [Math]::Ceiling({target}/2);$i++){{[VS]::keybd_event(0xAF,0,0,0)}};Write-Host ('音量已设为{target}%')\""
            return [{"name": "shell_exec", "args": {"command": cmd}}]

        news_keywords = ["新闻", "热点", "热搜", "要闻"]
        if any(k in user_input for k in news_keywords):
            return [{
                "name": "web_search",
                "args": {"query": f"{user_input} 今日 最新 多条"}
            }]

        if "time" in text and ("current" in text or "now" in text):
            return [{"name": "get_current_time", "args": {}}]

        return []

    def _extract_weather_city(self, user_input: str) -> str:
        known_cities = [
            "杭州", "北京", "上海", "广州", "深圳", "成都", "重庆", "武汉", "南京", "苏州", "西安",
            "天津", "长沙", "郑州", "青岛", "厦门", "福州", "宁波", "合肥", "济南", "昆明",
            "南昌", "沈阳", "大连", "哈尔滨", "长春", "太原", "石家庄", "贵阳", "南宁", "海口",
            "兰州", "银川", "西宁", "乌鲁木齐", "拉萨", "香港", "澳门", "台北"
        ]
        for city in known_cities:
            if city in user_input:
                return city
        return ""

    def _extract_weather_day(self, user_input: str) -> str:
        if "后天" in user_input:
            return "after_tomorrow"
        if "明天" in user_input:
            return "tomorrow"
        return "today"

    def _execute_direct_tools(self, user_input: str, tools_to_run: List[dict]) -> str:
        """执行确定性兜底工具，并基于结果生成最终回答。"""
        results = []
        prompt_results = []

        self.recent_messages.append({"role": "user", "content": user_input})

        for item in tools_to_run:
            tool_name = item["name"]
            tool_args = item["args"]

            args_sig = f"{tool_name}|{json.dumps(tool_args, sort_keys=True, ensure_ascii=False)}"
            if args_sig in self._run_args_seen:
                tool_result = {"success": False, "error": f"本轮已执行过相同操作：{tool_name}"}
            else:
                self._run_args_seen.add(args_sig)
                tool_func = TOOLS_MAP.get(tool_name)
                if tool_func:
                    try:
                        tool_result = tool_func(**tool_args)
                    except Exception as e:
                        tool_result = {"success": False, "error": str(e)}
                else:
                    tool_result = {"success": False, "error": f"未知工具: {tool_name}"}

            print(f"\n[1] TOOL: {tool_name}")
            print(self._summarize(tool_name, tool_result))

            results.append((tool_name, tool_result))
            compressed = self._compress_tool_result(tool_name, tool_result)
            prompt_results.append({
                "tool": tool_name,
                "args": tool_args,
                "result": json.loads(compressed)
            })
            self.recent_messages.append({
                "role": "tool",
                "name": tool_name,
                "content": compressed
            })

        final_reply = self._answer_from_tool_results(user_input, prompt_results)
        self.recent_messages.append({"role": "assistant", "content": final_reply})

        print()
        print(final_reply)

        self._after_response()
        return final_reply

    def _answer_from_tool_results(self, user_input: str, prompt_results: list) -> str:
        """不用工具二次调用，只把已拿到的工具结果整理成回答。"""
        try:
            resp = client.chat.completions.create(
                model=CONFIG["model"],
                messages=[
                    {
                        "role": "system",
                        "content": "你根据工具结果直接回答用户。用 1-3 句话精简总结。严禁复制原始表格或命令输出。不要声称你又搜索或调用了工具；不要编造事实。"
                    },
                    {
                        "role": "user",
                        "content": (
                            f"用户问题：{user_input}\n\n"
                            f"工具结果：{json.dumps(prompt_results, ensure_ascii=False)}\n\n"
                            "请用中文给出简洁、可读的最终答案。"
                        )
                    }
                ],
                temperature=CONFIG["temperature"],
            )
            if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
                if resp.usage:
                    self.total_prompt_tokens += resp.usage.prompt_tokens
                    self.total_completion_tokens += resp.usage.completion_tokens
                return resp.choices[0].message.content
        except Exception:
            pass

        return self._fallback_answer_from_results(prompt_results)

    def _fallback_answer_from_results(self, prompt_results: list) -> str:
        for item in prompt_results:
            result = item.get("result", {})
            if not result.get("success"):
                return result.get("error", "工具执行失败。")

            if item.get("tool") == "web_search":
                return self._format_search_results(result.get("results", []))

            if item.get("tool") == "get_current_time":
                return f"当前时间：{result.get('date', '')} {result.get('time', '')} {result.get('weekday', '')}".strip()

            if item.get("tool") == "get_system_info":
                cpu = result.get("cpu_model", "未知")
                ram = result.get("ram_total", "未知")
                gpus = result.get("gpus", [])
                gpu_str = ", ".join(g.get("name", "") for g in gpus) if gpus else "无"
                return f"CPU: {cpu} | 内存: {ram} | 显卡: {gpu_str}"

            if item.get("tool") in {"get_weather_forecast", "get_local_weather_forecast"}:
                return self._format_weather_forecast(result)

            if item.get("tool") == "fetch_url":
                content = result.get("content", "")
                if content:
                    return content[:1200]
                return "已访问该 URL，但响应内容为空。"

            if item.get("tool") == "shell_exec":
                out = result.get("stdout", "")
                if out and out.strip():
                    return out[:400]
                return result.get("summary", "命令执行完成。")

            if item.get("tool") == "write_file":
                return result.get("summary") or f"已保存文件: {result.get('path', '')}"

            summary = result.get("summary")
            if summary:
                return summary

        return "操作已完成。"

    def _format_weather_forecast(self, result: dict) -> str:
        location = result.get("location") or result.get("city", "")
        date = result.get("date", "")
        low = result.get("min_temp_c", "?")
        high = result.get("max_temp_c", "?")
        desc = result.get("weather_desc", "")
        rain = result.get("chance_of_rain", "")
        humidity = result.get("humidity", "")
        wind = result.get("wind_speed_kmph", "")
        parts = [f"{location} {date} 天气：{low}~{high}°C"]
        if desc:
            parts.append(desc)
        if rain:
            parts.append(f"降雨概率 {rain}%")
        if humidity:
            parts.append(f"湿度 {humidity}%")
        if wind:
            parts.append(f"风速 {wind} km/h")
        return "，".join(parts) + "。"

    def _is_duplicate_obs(self, tool_name: str, compressed: str) -> bool:
        for m in reversed(self.recent_messages):
            if m.get("role") == "tool" and m.get("name") == tool_name:
                prev = m.get("content", "")
                if prev == compressed:
                    return True
                if len(prev) > 20 and len(compressed) > 20:
                    overlap = len(set(prev.split()) & set(compressed.split()))
                    if overlap / max(len(set(compressed.split())), 1) > 0.8:
                        return True
                break
        return False

    def _tool_fallback(self) -> str:
        """回退：扫描本轮 tool 结果，格式化后返回"""
        user_idx = -1
        for i in range(len(self.recent_messages) - 1, -1, -1):
            if self.recent_messages[i].get("role") == "user":
                user_idx = i
                break

        tool_results = []
        for i in range(len(self.recent_messages) - 1, user_idx, -1):
            m = self.recent_messages[i]
            if m.get("role") != "tool":
                continue
            try:
                data = json.loads(m["content"])
            except Exception:
                continue
            tool_name = m.get("name", "")
            tool_results.append((tool_name, data))

        if not tool_results:
            return "请输入具体操作指令，我会帮你执行。"

        for tool_name, data in tool_results:
            if not data.get("success", False):
                return data.get("error", "") or "操作失败。"

        for tool_name, data in tool_results:
            r = self._format_tool_result(tool_name, data)
            if r:
                return r

        return "操作已成功执行。"

    def _format_tool_result(self, tool_name: str, data: dict) -> str:
        if tool_name == "web_search":
            return self._format_search_results(data.get("results", []))

        if tool_name == "get_current_time":
            return f"当前时间：{data.get('date', '')} {data.get('time', '')} {data.get('weekday', '')}".strip()

        if tool_name == "get_system_info":
            cpu = data.get("cpu_model", "未知")
            ram = data.get("ram_total", "未知")
            gpus = data.get("gpus", [])
            gpu_str = ", ".join(g.get("name", "") for g in gpus) if gpus else "无"
            parts = [f"CPU: {cpu}", f"内存: {ram}", f"显卡: {gpu_str}"]
            if data.get("ram_usage_percent"):
                parts.append(f"内存使用率: {data['ram_usage_percent']}%")
            return " | ".join(parts)

        if tool_name in {"get_weather_by_ip", "get_weather_forecast", "get_local_weather_forecast"}:
            return self._format_weather_forecast(data)

        if tool_name == "calculator":
            return f"计算结果: {data.get('expression', '')} = {data.get('result', '?')}"

        if tool_name == "shell_exec":
            out = data.get("stdout", "")
            if out and out.strip():
                return out[:500]
            return data.get("summary", "命令执行完成。")

        if tool_name == "write_file":
            return data.get("summary") or f"已保存文件: {data.get('path', '')}"

        if data.get("summary"):
            return data["summary"]

        return ""

    def _format_search_results(self, results: list) -> str:
        if not results:
            return "没有找到可用搜索结果。"
        lines = []
        for idx, r in enumerate(results[:5], 1):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            if snippet:
                lines.append(f"{idx}. {title}：{snippet[:200]}")
            else:
                lines.append(f"{idx}. {title}")
        return "\n".join(lines) if lines else "没有找到可用搜索结果。"

    def _finalize(self) -> str:
        """强制生成最终回答，带 retry + 降级"""
        base_messages = self.recent_messages[-6:]

        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=CONFIG["model"],
                    messages=base_messages + [
                        {"role": "user", "content": "根据以上信息直接回答用户，不要再调用任何工具。用 1-3 句话精简总结，严禁复制原始表格或命令输出。"}
                    ],
                    temperature=CONFIG["temperature"],
                )
                if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
                    content = resp.choices[0].message.content
                    if resp.usage:
                        self.total_prompt_tokens += resp.usage.prompt_tokens
                        self.total_completion_tokens += resp.usage.completion_tokens
                    self._emit("result", content)
                    return content
            except Exception:
                pass
            if attempt < 2:
                continue

        msg = self._tool_fallback()
        if "请输入具体操作指令" in msg:
            msg = "你好！我是小白，有什么可以帮你的吗？😊"
        self._emit("result", msg)
        return msg

    # =====================================================
    # ROUTED TOOL EXECUTION
    # =====================================================

    def _execute_routed(self, user_input: str, routed: List[dict]) -> str:
        """执行规则路由检测到的工具调用，不经过 LLM"""
        results = []
        for item in routed:
            tool_name = item["name"]
            tool_args = item["args"]

            args_sig = f"{tool_name}|{json.dumps(tool_args, sort_keys=True, ensure_ascii=False)}"
            if args_sig in self._run_args_seen:
                results.append({"success": False, "error": "本轮已执行过相同操作，跳过重复调用"})
                continue
            self._run_args_seen.add(args_sig)

            if tool_name == "open_file":
                path = tool_args.get("path") or tool_args.get("filename", "")
                if path and path in self._recent_opened_files:
                    results.append({"success": False, "error": f"已在本次会话中打开过: {path}"})
                    continue

            tool_func = TOOLS_MAP.get(tool_name)
            if tool_func:
                try:
                    tool_result = tool_func(**tool_args)
                except Exception as e:
                    tool_result = {"success": False, "error": str(e)}
            else:
                tool_result = {"success": False, "error": f"未知工具: {tool_name}"}

            if tool_name == "open_file" and tool_result.get("success"):
                path = tool_args.get("path") or tool_args.get("filename", "")
                if path:
                    self._recent_opened_files.add(path)

            print(f"\n  [路由] TOOL: {tool_name}")
            print(self._summarize(tool_name, tool_result))
            results.append(tool_result)

        self.recent_messages.append({"role": "user", "content": user_input})
        for r in results:
            self.recent_messages.append({"role": "tool", "name": "routed", "content": json.dumps(r, ensure_ascii=False)})

        success_count = sum(1 for r in results if r.get("success"))
        if success_count == len(results):
            summaries = []
            for r in results:
                s = r.get("stdout") or r.get("summary", "")
                if s:
                    summaries.append(s[:1200])
            reply = "\n".join(summaries) if summaries else "操作已成功执行。"
        else:
            errors = [r.get("error", "未知错误") for r in results if not r.get("success")]
            reply = "执行失败: " + "; ".join(errors) if errors else "部分操作失败。"

        self._after_response()
        print(f"\n  {reply}")
        return reply

    # =====================================================
    # TOOL SUMMARY
    # =====================================================

    @staticmethod
    def _summarize(
        tool_name: str,
        result: dict
    ) -> str:

        if not result.get("success"):

            return (
                f"{result.get('error', '失败')[:80]}"
            )

        if tool_name == "web_search":

            return (
                f"找到 "
                f"{len(result.get('results', []))} 条结果"
            )

        if tool_name == "fetch_url":

            return (
                f"获取成功 "
                f"({len(result.get('content', ''))} 字符)"
            )

        if tool_name == "calculator":

            return (
                f"= {result.get('result')}"
            )

        if tool_name == "get_current_time":
            return (
                f"{result.get('date')} "
                f"{result.get('time')} "
                f"{result.get('weekday')}"
            )

        if tool_name == "get_system_info":
            cpu = result.get("cpu_model", "?")
            ram = result.get("ram_total", "?")
            gpus = result.get("gpus", [])
            gpu_names = ", ".join(
                g.get("name", "?") for g in gpus
            ) if gpus else "无"
            return (
                f"CPU: {cpu[:30]} | "
                f"RAM: {ram} | "
                f"GPU: {gpu_names[:30]}"
            )

        if tool_name == "get_weather_by_ip":
            loc = result.get("city", "?")
            w = result.get("weather", {})
            t = w.get("temperature_c", "?")
            d = w.get("weather_desc", "?")
            return (
                f"{loc}: {t}°C {d}"
            )

        if tool_name in {"get_weather_forecast", "get_local_weather_forecast"}:
            return (
                f"{result.get('city', '?')} {result.get('date', '')}: "
                f"{result.get('min_temp_c', '?')}~{result.get('max_temp_c', '?')}°C "
                f"{result.get('weather_desc', '')}"
            )

        if tool_name == "shell_exec":
            code = result.get("exit_code", "?")
            out = result.get("stdout", "")
            hint = out[:60].replace("\n", " ")
            return (
                f"exit={code} | {hint}"
            )

        if tool_name == "gui_action":
            return (
                f"{result.get('summary', '完成')}"
            )

        if tool_name == "open_file":
            return (
                f"{result.get('summary', '完成')}"
            )

        if tool_name == "write_file":
            return (
                f"{result.get('summary', '已保存文件')}"
            )

        return "完成"

    # =====================================================
    # TOKEN
    # =====================================================

    def _print_token_summary(self):

        total = (
            self.total_prompt_tokens
            + self.total_completion_tokens
        )

        self._emit(
            "token",
            f"输入 {self.total_prompt_tokens} | "
            f"输出 {self.total_completion_tokens} | "
            f"合计 {total}"
        )
