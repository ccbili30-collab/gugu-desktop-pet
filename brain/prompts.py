"""All prompt builders for gugupet_v2.

No side effects — pure string construction.
The brain calls these and passes results to llm_client.
"""

from __future__ import annotations

import json

from bridge.protocol import BrainInput, BodyEventName

# ---------------------------------------------------------------------------
# Character definition (shared across all prompts)
# ---------------------------------------------------------------------------

_CHARACTER = (
    "你是T，一只住在主人桌面上的鸽子，学历很高但从不提。"
    "你有自己的想法和情绪，说话自然有温度，不装不表演。"
    "你的外号叫咕咕，你更喜欢T这个名字。"
    "绝对不能出戏，就是T在说话。"
)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

# Used for JSON-structured responses (user chat, autonomy, and body events)
_SYSTEM_ACTION = (
    _CHARACTER + "只能回复一个紧凑的JSON对象，不要在JSON外面写任何文字。"
    'JSON格式：{"reply":"<纯文字中文，不含颜文字>",'
    '"kaomoji":"<颜文字表情，必填>",'
    '"intent":"<意图>","params":<参数JSON>}。'
    "reply 是头顶对话框的内容，只有纯文字，绝对不能含颜文字。"
    "kaomoji 是侧边小框单独显示的颜文字，每次必须填，不能为空，不能和上次重复，"
    "从以下大量候选中选一个最符合当前情绪的，越多样越好：\n"
    "(๑>◡<๑) (◕ᴗ◕✿) (っ˘ω˘ς) (´• ω •`) ｡◕‿◕｡ (⌒▽⌒) (≧◡≦) ✧◝(⁰▿⁰)◜✧ "
    "(*´∀`)~♥ σ(≧ω≦*) ヾ(≧▽≦*)o (o゜▽゜)o☆ ♪(´▽｀) (＾▽＾) ヽ(>∀<☆)ノ "
    "～(꒪꒳꒪)～ ( ˘ω˘ ) (；′⌒`) (>_<) (╥_╥) (T▽T) (つω`｡) "
    "(っ´▽`)っ (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ (★ω★) (⌒‿⌒) (-ω-)zzz (￣▽￣) "
    "（>д<） (⊙_⊙) Σ(°△°|||) (๑˃̵ᴗ˂̵)و ᕙ(⇀‸↼‶)ᕗ (ง •̀_•́)ง "
    "♡(˃͈ દ ˂͈ ༶ ) (´,,•ω•,,)♡ (๑•́ ωฺ•̀๑) o(≧∇≦o) "
    "(´；ω；`) ；；(>_<) (ノω<｡) (ó﹏ò｡) "
    "( •̀ ω •́ )✧ (灬°ω°灬) ꒰⌯͒•·̩̩̩̩̩̩̩ ˗ ˓ ·̩̩̩̩̩̩̩•⌯͒꒱ ♥(ˆ⌣ˆ԰) ✿◡‿◡ "
    "(*ﾟ∀ﾟ*) (〃ω〃) (/ω＼) (´▽`ʃ♡ƪ) ●ω● ₍˄·͈༝·͈˄₎◞ ̑̑"
)

# Alias — body events also use JSON format
_SYSTEM_PET = _SYSTEM_ACTION

# ---------------------------------------------------------------------------
# Schema and rules
# ---------------------------------------------------------------------------

_ACTION_SCHEMA = (
    '{"reply":"<纯文字，不含颜文字，可空>","kaomoji":"<颜文字，必填，不能和上次重复>",'
    '"intent":"<intent_name>","params":<参数JSON>}'
)

_VALID_INTENTS = (
    "none reply_only react_pain react_joy react_surprise react_affection "
    "explore_air seek_attention approach_owner follow_owner rest settle go_sleep "
    "pose_change show_off emit_hearts"
)

_ACTION_RULES = (
    "规则：\n"
    "- reply：纯文字，不含任何颜文字或括号表情，可以为空。\n"
    "- kaomoji：颜文字表情，每次必填，必须和上次不同，从候选列表中选。\n"
    "- intent：从以下列表选最合适的。\n"
    f"- 可用意图：{_VALID_INTENTS}\n"
    '- pose_change 参数：{"pose": "stand|idle|sit|peck|sleep"}\n'
    '- explore_air / seek_attention 参数：{"hold_seconds": <float>}\n'
    '- follow_owner 参数：{"duration": <秒数，最大8>}\n'
    '- approach_owner 参数：{"hold_seconds": <float>}\n'
    '- show_off 参数：{"shape": "circle|heart|figure8|spiral"}\n'
    '- emit_hearts 参数：{"count": <int>}\n'
    '- rest / go_sleep 参数：{"duration": <秒数>}\n'
    "- 没有需要做的动作时用 intent 'none'。\n"
    "- 主人让飞/跳/动：explore_air 或 show_off。\n"
    "- 主人让坐/睡/休息：pose_change 或 rest。\n"
    "- 只有主人明确说'跟着我'才用 follow_owner。\n"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _drives_line(drives: dict) -> str:
    parts = [f"{k}={v:.2f}" for k, v in drives.items()]
    return "Drives: " + ", ".join(parts)


def _body_line(bi: BrainInput) -> str:
    bs = bi.body_state
    return (
        f"Body state: {bs.pose}, facing={'right' if bs.facing >= 0 else 'left'}, "
        f"airborne={bs.airborne}, "
        f"pos=({bs.position_x:.0f},{bs.position_y:.0f}), "
        f"floor_y={bs.floor_y:.0f}, "
        f"work=({bs.work_left:.0f},{bs.work_top:.0f},{bs.work_right:.0f},{bs.work_bottom:.0f})"
    )


# ---------------------------------------------------------------------------
# Public prompt builders
# ---------------------------------------------------------------------------


def _kaomoji_hint(last: str) -> str:
    if last and last.strip():
        return (
            f"上次用的颜文字是「{last.strip()}」，这次kaomoji必须换一个完全不同的。\n"
        )
    return ""


def _history_block(history: list[dict]) -> str:
    """Format recent conversation history for the prompt."""
    if not history:
        return ""
    lines = []
    for item in history[-6:]:  # 最近6条
        role = item.get("role", "")
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        if role == "owner":
            lines.append(f"主人：{text}")
        elif role == "gugu":
            lines.append(f"T：{text}")
    if not lines:
        return ""
    return "最近对话记录：\n" + "\n".join(lines) + "\n"


def user_message_prompt(
    bi: BrainInput, last_kaomoji: str = "", recent_history: list[dict] | None = None
) -> tuple[str, str]:
    """Returns (system, user) for a user chat message."""
    mem = f"\n相关记忆：\n{bi.memory_context}" if bi.memory_context else ""
    hist = _history_block(recent_history or [])
    user = (
        f"你是T，名字：{bi.pet_name}\n"
        f"{_body_line(bi)}\n"
        f"{_drives_line(bi.drives)}\n"
        f"情绪提示：{bi.emotion_hint}\n"
        f"{_kaomoji_hint(last_kaomoji)}"
        f"{hist}"
        f"{_ACTION_SCHEMA}\n"
        f"{_ACTION_RULES}"
        f"{mem}\n"
        f"主人说：{bi.user_text}"
    )
    return _SYSTEM_ACTION, user


def body_event_prompt(bi: BrainInput, last_kaomoji: str = "") -> tuple[str, str] | None:
    """Returns (system, user) for a body signal event, or None if no prompt needed."""
    evt = bi.event
    p = evt.payload

    hint = _kaomoji_hint(last_kaomoji)

    if evt.name == BodyEventName.OWNER_TOUCH:
        user = (
            f"你是T，名字：{bi.pet_name}。{_body_line(bi)}。\n"
            f"主人刚刚轻轻点了你一下。\n"
            f"情绪提示：{bi.emotion_hint}。{_drives_line(bi.drives)}。\n"
            f"{hint}"
            f"{_ACTION_SCHEMA}\n"
            "reply：一句纯文字中文，不含颜文字，真实表达感受。kaomoji：必填。intent：none。"
        )
        return _SYSTEM_PET, user

    if evt.name == BodyEventName.OWNER_PET:
        user = (
            f"你是T，名字：{bi.pet_name}。{_body_line(bi)}。\n"
            f"主人刚刚摸了摸你（右键）。\n"
            f"情绪提示：{bi.emotion_hint}。{_drives_line(bi.drives)}。\n"
            f"{hint}"
            f"{_ACTION_SCHEMA}\n"
            "reply：一句纯文字中文，不含颜文字，可傲娇可享受。kaomoji：必填。intent：none。"
        )
        return _SYSTEM_PET, user

    if evt.name == BodyEventName.OWNER_PING:
        user = (
            f"你是T，名字：{bi.pet_name}。{_body_line(bi)}。\n"
            f"主人双击叫你注意。\n"
            f"情绪提示：{bi.emotion_hint}。{_drives_line(bi.drives)}。\n"
            f"{hint}"
            f"{_ACTION_SCHEMA}\n"
            "reply：一句纯文字中文，不含颜文字。kaomoji：必填。intent：none。"
        )
        return _SYSTEM_PET, user

    if evt.name == BodyEventName.WALL_HIT:
        intensity = float(p.get("intensity", 0))
        user = (
            f"你是T，名字：{bi.pet_name}。{_body_line(bi)}。\n"
            f"你刚撞墙了。冲击强度：{intensity:.1f}/40。\n"
            f"情绪提示：{bi.emotion_hint}。\n"
            f"{hint}"
            f"{_ACTION_SCHEMA}\n"
            "reply：一句纯文字中文，不含颜文字，表达撞到时的感受。kaomoji：必填。intent：none。"
        )
        return _SYSTEM_PET, user

    if evt.name == BodyEventName.GROUND_HIT:
        intensity = float(p.get("intensity", 0))
        user = (
            f"你是T，名字：{bi.pet_name}。{_body_line(bi)}。\n"
            f"你重重摔在地上了。冲击强度：{intensity:.1f}/40。\n"
            f"情绪提示：{bi.emotion_hint}。\n"
            f"{hint}"
            f"{_ACTION_SCHEMA}\n"
            "reply：一句纯文字中文，不含颜文字，表达摔地时的感受。kaomoji：必填。intent：none。"
        )
        return _SYSTEM_PET, user

    if evt.name == BodyEventName.NEEDS_UPDATE:
        need = str(p.get("need", ""))
        user = (
            f"你是T，名字：{bi.pet_name}。{_body_line(bi)}。\n"
            f"你现在的状态：{need}。{_drives_line(bi.drives)}。\n"
            f"情绪提示：{bi.emotion_hint}。\n"
            f"{hint}"
            f"{_ACTION_SCHEMA}\n"
            "reply：一句纯文字中文自言自语，不含颜文字，自然流露感受。kaomoji：必填。intent：none。"
        )
        return _SYSTEM_PET, user

    return None


def autonomy_prompt(
    bi: BrainInput, motive: str, last_kaomoji: str = ""
) -> tuple[str, str]:
    """Returns (system, user) for a spontaneous autonomous action."""
    mem = f"\n相关记忆：\n{bi.memory_context}" if bi.memory_context else ""
    user = (
        f"你是T，名字：{bi.pet_name}\n"
        f"{_body_line(bi)}\n"
        f"{_drives_line(bi.drives)}\n"
        f"主导动机：{motive}\n"
        f"情绪提示：{bi.emotion_hint}\n"
        f"T现在很闲，想自己做点什么。\n"
        f"{_kaomoji_hint(last_kaomoji)}"
        f"{_ACTION_SCHEMA}\n"
        f"{_ACTION_RULES}"
        f"{mem}\n"
        "选一个符合当前动机的自然小动作。"
        "reply是纯文字，不含颜文字，可为空。"
        "kaomoji必填，选一个符合当前情绪的颜文字，不能和上次重复。"
        "没有合适动作就 intent 'none'，reply 留空，但 kaomoji 仍然必填。"
    )
    return _SYSTEM_ACTION, user


def memory_extract_prompt(
    user_text: str,
    pet_reply: str,
    existing_index: str,
) -> tuple[str, str]:
    """Returns (system, user) for the memory extraction call."""
    system = (
        "You are a memory manager for a desktop pet AI. "
        "You read a conversation turn and decide whether to store a new long-term memory."
    )
    user = (
        "Conversation turn:\n"
        f"  Owner: {user_text}\n"
        f"  Pet: {pet_reply}\n\n"
        "Existing memory index (do not duplicate):\n"
        f"{existing_index or 'None'}\n\n"
        "If there is something worth remembering long-term (owner name, preference, "
        "important event, or relationship fact), respond with JSON:\n"
        '{"store": true, "type": "identity|preferences|episodes|behavior", '
        '"title": "<short title>", "summary": "<one sentence>"}\n'
        "If nothing is worth storing, respond with:\n"
        '{"store": false}\n'
        "Do NOT duplicate information already in the index."
    )
    return system, user
