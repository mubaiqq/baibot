
"""
Advanced Memory System
- Retrieval Memory
- Memory Merge
- Context Compression
- Automatic Forgetting
"""

import json
import hashlib
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

MEMORIES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "memories"
)

os.makedirs(MEMORIES_DIR, exist_ok=True)

user_id_cache = {}

CURRENT_SESSION_ID = ""


# =========================================================
# USER
# =========================================================

def _get_user_id() -> str:

    global user_id_cache

    pid = os.getpid()

    if pid not in user_id_cache:

        raw = f"user-{pid}"

        user_id_cache[pid] = hashlib.md5(
            raw.encode()
        ).hexdigest()[:12]

    return user_id_cache[pid]


def _memory_path():

    uid = _get_user_id()

    return os.path.join(
        MEMORIES_DIR,
        f"{uid}.json"
    )


# =========================================================
# LOAD / SAVE
# =========================================================

def _load():

    path = _memory_path()

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, IOError):
            pass

    return {
        "sessions": {},
        "memories": []
    }


def _save(data):

    path = _memory_path()

    with open(path, "w", encoding="utf-8") as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# SESSION
# =========================================================

def new_session():

    global CURRENT_SESSION_ID

    sid = uuid.uuid4().hex[:8]

    CURRENT_SESSION_ID = sid

    data = _load()

    data["sessions"][sid] = {
        "created_at": datetime.now().isoformat(),
        "summary": "",
        "message_count": 0,
    }

    _save(data)

    print(f"📋 新会话: {sid}")

    return sid


def ensure_session():

    global CURRENT_SESSION_ID

    if CURRENT_SESSION_ID:
        return CURRENT_SESSION_ID

    data = _load()

    sessions = data.get("sessions", {})

    if sessions:

        CURRENT_SESSION_ID = max(
            sessions.keys(),
            key=lambda k: sessions[k].get(
                "created_at",
                ""
            )
        )

    else:

        CURRENT_SESSION_ID = new_session()

    return CURRENT_SESSION_ID


def record_message():

    sid = ensure_session()

    data = _load()

    if sid in data["sessions"]:

        data["sessions"][sid]["message_count"] += 1

    _save(data)


# =========================================================
# MEMORY CLEAN
# =========================================================

def _forget_stale(data):

    now = datetime.now()

    cutoff = now - timedelta(days=30)

    kept = []

    for m in data["memories"]:

        try:

            last_access = datetime.fromisoformat(
                m.get(
                    "last_access",
                    m["created_at"]
                )
            )

        except Exception:

            last_access = now

        # 太久不用
        if last_access < cutoff:
            continue

        # 低价值
        if (
            m.get("importance", 0.5) < 0.2
            and m.get("access_count", 1) <= 1
        ):
            continue

        kept.append(m)

    data["memories"] = kept


# =========================================================
# SIMILARITY
# =========================================================

def _token_similarity(a: str, b: str):

    sa = set(a.lower().split())
    sb = set(b.lower().split())

    if not sa or not sb:
        return 0

    return len(sa & sb) / len(sa | sb)


def _find_similar_memory(
    data,
    content
):

    best = None
    best_score = 0

    for m in data["memories"]:

        score = _token_similarity(
            content,
            m["content"]
        )

        score *= (
            m.get("importance", 0.5) + 0.5
        )

        if score > 0.35 and score > best_score:

            best = m
            best_score = score

    return best


# =========================================================
# MEMORY MERGE
# =========================================================

def _merge_contents(old, new):

    old = old.strip()
    new = new.strip()

    if old == new:
        return old

    if len(new) > len(old):
        return new

    return old


def merge_or_create_memory(memory):

    data = _load()

    _forget_stale(data)

    existing = _find_similar_memory(
        data,
        memory["content"]
    )

    now = datetime.now().isoformat()

    if existing:

        existing["content"] = _merge_contents(
            existing["content"],
            memory["content"]
        )

        existing["importance"] = max(
            existing.get("importance", 0.5),
            memory.get("importance", 0.5)
        )

        existing["last_access"] = now

        existing["access_count"] = (
            existing.get("access_count", 1) + 1
        )

    else:

        data["memories"].append({
            "id": uuid.uuid4().hex[:12],
            "type": memory.get(
                "type",
                "episodic"
            ),
            "content": memory["content"],
            "importance": memory.get(
                "importance",
                0.5
            ),
            "created_at": now,
            "last_access": now,
            "access_count": 1,
        })

    _save(data)


# =========================================================
# RETRIEVAL
# =========================================================

def retrieve_relevant_memories(
    query: str,
    top_k: int = 5
):

    data = _load()

    scored = []

    for m in data["memories"]:

        score = _token_similarity(
            query,
            m["content"]
        )

        score += (
            m.get("importance", 0.5) * 0.3
        )

        if score > 0.1:

            scored.append(
                (score, m)
            )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    results = []

    for _, memory in scored[:top_k]:

        memory["access_count"] = (
            memory.get("access_count", 1) + 1
        )

        memory["last_access"] = (
            datetime.now().isoformat()
        )

        results.append(memory)

    _save(data)

    return results


# =========================================================
# MEMORY EXTRACTION
# =========================================================

def extract_memories_from_conversation(
    messages: List[dict]
):

    memories = []

    for msg in messages:

        if msg["role"] != "user":
            continue

        text = msg["content"].strip()

        if len(text) < 4:
            continue

        profile_keywords = [
            "我喜欢",
            "我使用",
            "我开发",
            "我习惯",
            "我偏好",
            "我希望",
            "我想",
            "我需要",
            "我讨厌",
            "我是",
            "我会",
        ]

        is_profile = any(
            kw in text
            for kw in profile_keywords
        )

        memories.append({
            "type": (
                "profile"
                if is_profile
                else "episodic"
            ),
            "content": text[:120],
            "importance": (
                0.75
                if is_profile
                else 0.35
            )
        })

    return memories


# =========================================================
# SUMMARY
# =========================================================

def summarize_messages(messages):

    parts = []

    for m in messages:

        role = m["role"]

        content = str(
            m.get("content", "")
        )[:120]

        parts.append(
            f"{role}: {content}"
        )

    text = "\n".join(parts)

    if len(text) > 1000:
        text = text[:1000]

    return text


def get_session_summary():

    sid = ensure_session()

    data = _load()

    session = data["sessions"].get(
        sid,
        {}
    )

    summary = session.get(
        "summary",
        ""
    )

    return (
        f"会话 ID: {sid}\n"
        f"摘要:\n{summary}"
    )


def save_session_summary(summary):

    sid = ensure_session()

    data = _load()

    if sid in data["sessions"]:

        data["sessions"][sid]["summary"] = summary

    _save(data)
