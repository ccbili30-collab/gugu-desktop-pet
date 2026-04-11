"""Brain agent main loop for gugupet_v2.

Polls body events, runs reflex + LLM, dispatches commands.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from brain import autonomy, drives as drive_mod, llm_client, reflex
from brain.memory_retriever import format_context
from brain.memory_store import ensure
from brain.memory_writer import maybe_extract_and_store
from brain.prompts import autonomy_prompt, body_event_prompt, user_message_prompt
from bridge.dispatcher import dispatch
from bridge.event_adapter import event_to_brain_input
from bridge.protocol import (
    BodyEventName,
    BrainReaction,
    BrainIntentName,
)
from config import loader as cfg
from runtime.event_queue import pending_events
from runtime.models import RuntimeState
from runtime.state_store import (
    ensure_runtime_files,
    read_bridge_state,
    read_state,
    write_bridge_state,
    write_state,
)

_HISTORY_FILE = _ROOT / "runtime" / "pet_conversation_history.json"


def _read_recent_history(max_turns: int = 6) -> list[dict]:
    """Read the last N conversation turns from history file for prompt context."""
    try:
        import json as _json

        raw = _HISTORY_FILE.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        data = _json.loads(raw)
        items = data.get("items", []) if isinstance(data, dict) else []
        # 只取 owner/gugu 角色，过滤掉系统条目
        turns = [
            i
            for i in items
            if isinstance(i, dict) and i.get("role") in ("owner", "gugu")
        ]
        return turns[-max_turns:]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    # strip markdown fences
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _sanitize(text: str) -> str:
    """Clean LLM reply text — keep kaomoji brackets intact."""
    text = str(text or "").strip().replace("\n", " ")
    # Remove full-width stage directions （like this） only
    text = re.sub(r"（[^）]{1,20}）", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_reaction(raw_text: str, fallback_intent: str | None = None) -> BrainReaction:
    payload = _extract_json(raw_text)
    if isinstance(payload, dict):
        reply = _sanitize(str(payload.get("reply", "") or ""))
        kaomoji = str(payload.get("kaomoji", "") or "").strip()
        intent = str(
            payload.get("intent", fallback_intent or BrainIntentName.NONE)
        ).strip()
        params = payload.get("params", {})
        if not isinstance(params, dict):
            params = {}
        return BrainReaction(intent=intent, reply=reply, kaomoji=kaomoji, params=params)
    # Plain text reply — no action
    return BrainReaction(
        intent=fallback_intent or BrainIntentName.REPLY_ONLY,
        reply=_sanitize(raw_text),
        kaomoji="",
        params={},
    )


# ---------------------------------------------------------------------------
# Per-event processing
# ---------------------------------------------------------------------------


def _process_event(
    event,
    state: RuntimeState,
    current_drives: dict[str, float],
    pet_name: str,
    species: str,
) -> RuntimeState:
    now = time.time()

    # Drive impact
    current_drives.update(
        drive_mod.apply_event_impact(current_drives, event.name, event.payload)
    )

    # Reflex analysis
    emotion_hint, suggested_intent = reflex.analyse(event, current_drives)

    # Memory context
    query = str(event.payload.get("text", event.name) or event.name)
    mem_ctx = format_context(query) if cfg.llm_enabled() else ""

    # Assemble brain input
    brain_input = event_to_brain_input(
        event, current_drives, emotion_hint, mem_ctx, pet_name, species
    )

    # Mark busy
    if event.name == BodyEventName.USER_MESSAGE:
        user_text = event.payload.get("text", "")
        print(f"[brain] processing user_message id={event.id}: {user_text!r}")
        state.status = "busy_think"
        state.active_dialog_event_id = event.id
        state.chat_text = "..."
        state.chat_ts = now
        write_state(state)

    # Build prompt
    last_kaomoji = str(state.pet_text or "").strip()
    if event.name == BodyEventName.USER_MESSAGE:
        recent_history = _read_recent_history(max_turns=6)
        system, user = user_message_prompt(brain_input, last_kaomoji, recent_history)
        max_tok = int(cfg.llm().get("max_tokens_reply", 600))
    else:
        prompt_pair = body_event_prompt(brain_input, last_kaomoji)
        if prompt_pair is None:
            return state
        system, user = prompt_pair
        max_tok = int(cfg.llm().get("max_tokens_event", 200))

    # Call LLM
    reaction = BrainReaction(intent=BrainIntentName.NONE)
    if cfg.llm_enabled():
        result = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tok,
        )
        if result.get("ok"):
            reaction = _parse_reaction(
                str(result.get("text", "") or ""),
                fallback_intent=suggested_intent,
            )
            print(f"[brain] LLM ok  reply={reaction.reply!r}  intent={reaction.intent}")
        else:
            err = result.get("error", "unknown")
            body = str(result.get("body", ""))[:200]
            print(f"[brain] LLM failed: {err}  body={body}")
            # Provide a fallback reply so the user knows the AI is unreachable
            if event.name == BodyEventName.USER_MESSAGE:
                reaction = BrainReaction(
                    intent=BrainIntentName.REPLY_ONLY,
                    reply="咕…（AI暂时连不上，稍后再试）",
                )
    elif suggested_intent:
        reaction = BrainReaction(intent=suggested_intent, reply="", params={})

    # Dispatch commands
    dispatch(event, reaction)

    # Update state — fresh timestamp so body always sees new ts
    reply_ts = time.time()
    if reaction.reply:
        state.bubble_text = reaction.reply
        state.bubble_ts = reply_ts
        # All replies go to chat_text (head bubble), not pet_text
        state.chat_text = reaction.reply
        state.chat_ts = reply_ts
    elif event.name == BodyEventName.USER_MESSAGE:
        fallback = "咕？"
        state.chat_text = fallback
        state.chat_ts = reply_ts
        state.bubble_text = fallback
        state.bubble_ts = reply_ts
        print("[brain] empty reply for user_message, using fallback")

    # kaomoji always goes to pet_text (side bubble) — separate from reply
    if reaction.kaomoji:
        state.pet_text = reaction.kaomoji
        state.pet_ts = reply_ts

    state.status = "idle"
    state.active_dialog_event_id = 0
    state.brain_ts = reply_ts

    # Memory extraction for user messages
    if event.name == BodyEventName.USER_MESSAGE and reaction.reply:
        maybe_extract_and_store(brain_input.user_text, reaction.reply)

    return state


# ---------------------------------------------------------------------------
# Autonomy
# ---------------------------------------------------------------------------


def _maybe_autonomy(
    state: RuntimeState,
    current_drives: dict[str, float],
    pet_name: str,
    species: str,
) -> RuntimeState:
    if not cfg.llm_enabled():
        return state
    now = time.time()
    if not autonomy.should_act(
        state.last_autonomy_ts,
        state.next_autonomy_after,
        state.status,
        state.active_dialog_event_id,
        is_dragging=False,
    ):
        return state

    motive = autonomy.choose_motive(current_drives, state.last_owner_attention_ts)
    from runtime.state_store import read_status

    status = read_status()
    from bridge.protocol import BodyState

    bs = BodyState(
        position_x=status.window_x,
        position_y=status.window_y,
        floor_y=status.floor_y,
        work_left=status.work_left,
        work_top=status.work_top,
        work_right=status.work_right,
        work_bottom=status.work_bottom,
        facing=status.direction,
        pose=status.pet_state,
        airborne=status.airborne,
    )
    from bridge.protocol import BodyEvent

    dummy_event = BodyEvent(name="autonomy_tick", ts=now)
    mem_ctx = format_context(motive)
    from bridge.protocol import EmotionHint

    brain_input = event_to_brain_input(
        dummy_event, current_drives, EmotionHint.NEUTRAL, mem_ctx, pet_name, species
    )
    last_kaomoji = str(state.pet_text or "").strip()
    system, user = autonomy_prompt(brain_input, motive, last_kaomoji)
    result = llm_client.chat_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=int(cfg.llm().get("max_tokens_reply", 600)),
    )
    if result.get("ok"):
        reaction = _parse_reaction(str(result.get("text", "") or ""))
        dispatch(dummy_event, reaction)
        if reaction.reply:
            state.pet_text = reaction.reply
            state.pet_ts = now
        if reaction.kaomoji:
            state.pet_text = reaction.kaomoji
            state.pet_ts = now

    state.last_autonomy_ts = now
    state.next_autonomy_after = autonomy.next_cooldown(current_drives)
    state.dominant_drive = motive
    state.brain_ts = now
    return state


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run() -> None:
    config = cfg.load_raw()
    pet_name = cfg.pet_name(config)
    species = cfg.species(config)
    brain_cfg = cfg.brain(config)
    poll_interval = float(brain_cfg.get("poll_interval", 0.8))

    ensure_runtime_files()
    ensure()

    bridge = read_bridge_state()
    last_event_id = bridge.last_event_id

    state = read_state()
    current_drives = dict(state.drives) if state.drives else drive_mod.initial_drives()

    print(
        f"[brain] started  pet={pet_name}  llm={'on' if cfg.llm_enabled(config) else 'off'}"
    )

    while True:
        now = time.time()
        try:
            state = read_state()
            current_drives = dict(state.drives) if state.drives else current_drives

            # Drive drift
            from runtime.state_store import read_status

            status = read_status()
            in_dialog = (
                bool(state.active_dialog_event_id) or str(state.status) == "busy_think"
            )
            current_drives = drive_mod.tick_drift(
                current_drives,
                status.pet_state,
                not status.airborne,
                state.last_drive_update_ts,
                now,
                in_dialog=in_dialog,
            )
            state.drives = current_drives
            state.last_drive_update_ts = now
            state.dominant_drive = drive_mod.dominant_motive(
                current_drives,
                max(0.0, now - state.last_owner_attention_ts)
                if state.last_owner_attention_ts
                else 60.0,
            )

            # Process new events
            events = pending_events(last_event_id)
            for event in events:
                if event.name in (
                    BodyEventName.USER_MESSAGE,
                    BodyEventName.OWNER_TOUCH,
                    BodyEventName.OWNER_PET,
                    BodyEventName.OWNER_PING,
                    BodyEventName.WALL_HIT,
                    BodyEventName.GROUND_HIT,
                    BodyEventName.NEEDS_UPDATE,
                    BodyEventName.SLINGSHOT_LAUNCHED,
                ):
                    if event.name == BodyEventName.USER_MESSAGE:
                        state.last_owner_attention_ts = now
                    state = _process_event(
                        event, state, current_drives, pet_name, species
                    )
                last_event_id = event.id

            # Autonomy
            state = _maybe_autonomy(state, current_drives, pet_name, species)

            write_state(state)
            bridge.last_event_id = last_event_id
            write_bridge_state(bridge)

        except Exception as exc:
            import traceback

            print(f"[brain] error: {exc}")
            traceback.print_exc()

        time.sleep(poll_interval)


if __name__ == "__main__":
    run()
