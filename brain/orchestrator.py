"""Brain orchestrator for gugupet_v2.

Coordinates reflex, LLM, drives, memory, and autonomy into a single
decision pipeline.  agent.py calls this instead of doing everything inline.
"""

from __future__ import annotations

import time
from typing import Any

from brain import autonomy as autonomy_mod
from brain import drives as drive_mod
from brain import llm_client
from brain import reflex
from brain.memory_retriever import format_context
from brain.memory_writer import maybe_extract_and_store
from brain.prompts import autonomy_prompt, body_event_prompt, user_message_prompt
from bridge.protocol import (
    BodyEvent,
    BodyEventName,
    BrainInput,
    BrainReaction,
    BrainIntentName,
)
from config import loader as cfg


class Orchestrator:
    """Single entry point for all brain decisions.

    Usage:
        orch = Orchestrator()
        reaction = orch.process_event(event, state, drives)
        reaction = orch.maybe_autonomy(state, drives)
    """

    def __init__(self) -> None:
        self._config = cfg.load_raw()

    def reload_config(self) -> None:
        self._config = cfg.load_raw()

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------

    def process_event(
        self,
        event: BodyEvent,
        drives: dict[str, float],
        pet_name: str,
        species: str,
        last_owner_attention_ts: float,
    ) -> BrainReaction:
        """Full pipeline: reflex → memory → LLM → reaction."""

        # 1. Drive impact
        updated_drives = drive_mod.apply_event_impact(drives, event.name, event.payload)
        drives.update(updated_drives)

        # 2. Reflex analysis
        emotion_hint, suggested_intent = reflex.analyse(event, drives)

        # 3. Memory context
        query = str(event.payload.get("text", event.name) or event.name)
        mem_ctx = format_context(query) if cfg.llm_enabled(self._config) else ""

        # 4. Assemble brain input
        from bridge.event_adapter import body_state_from_runtime

        body_state = body_state_from_runtime()
        user_text = (
            str(event.payload.get("text", "") or "")
            if event.name == BodyEventName.USER_MESSAGE
            else ""
        )

        brain_input = BrainInput(
            event=event,
            body_state=body_state,
            drives=drives,
            emotion_hint=emotion_hint,
            memory_context=mem_ctx,
            pet_name=pet_name,
            species=species,
            user_text=user_text,
        )

        # 5. Build prompt and call LLM
        reaction = self._call_llm(brain_input, suggested_intent)

        # 6. Post-process: memory extraction for user messages
        if event.name == BodyEventName.USER_MESSAGE and reaction.reply and user_text:
            maybe_extract_and_store(user_text, reaction.reply)

        return reaction

    # ------------------------------------------------------------------
    # Autonomy
    # ------------------------------------------------------------------

    def maybe_autonomy(
        self,
        drives: dict[str, float],
        pet_name: str,
        species: str,
        status: str,
        active_dialog_event_id: int,
        last_autonomy_ts: float,
        next_autonomy_after: float,
        last_owner_attention_ts: float,
    ) -> BrainReaction | None:
        """Return a spontaneous reaction if autonomy should fire, else None."""
        if not cfg.llm_enabled(self._config):
            return None
        if not autonomy_mod.should_act(
            last_autonomy_ts,
            next_autonomy_after,
            status,
            active_dialog_event_id,
            is_dragging=False,
        ):
            return None

        motive = autonomy_mod.choose_motive(drives, last_owner_attention_ts)
        mem_ctx = format_context(motive)

        from bridge.event_adapter import body_state_from_runtime
        from bridge.protocol import EmotionHint

        dummy_event = BodyEvent(name="autonomy_tick", ts=time.time())
        brain_input = BrainInput(
            event=dummy_event,
            body_state=body_state_from_runtime(),
            drives=drives,
            emotion_hint=EmotionHint.NEUTRAL,
            memory_context=mem_ctx,
            pet_name=pet_name,
            species=species,
        )
        system, user = autonomy_prompt(brain_input, motive)
        result = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=int(cfg.llm(self._config).get("max_tokens_reply", 180)),
        )
        if not result.get("ok"):
            return None
        from brain.agent import _parse_reaction

        reaction = _parse_reaction(str(result.get("text", "") or ""))
        reaction.params["_motive"] = motive
        return reaction

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        brain_input: BrainInput,
        suggested_intent: str | None,
    ) -> BrainReaction:
        event = brain_input.event
        if not cfg.llm_enabled(self._config):
            if suggested_intent:
                return BrainReaction(intent=suggested_intent, reply="", params={})
            return BrainReaction(intent=BrainIntentName.NONE)

        if event.name == BodyEventName.USER_MESSAGE:
            system, user = user_message_prompt(brain_input)
            max_tok = int(cfg.llm(self._config).get("max_tokens_reply", 260))
        else:
            pair = body_event_prompt(brain_input)
            if pair is None:
                if suggested_intent:
                    return BrainReaction(intent=suggested_intent, reply="", params={})
                return BrainReaction(intent=BrainIntentName.NONE)
            system, user = pair
            max_tok = int(cfg.llm(self._config).get("max_tokens_event", 100))

        result = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tok,
        )
        if not result.get("ok"):
            if suggested_intent:
                return BrainReaction(intent=suggested_intent, reply="", params={})
            return BrainReaction(intent=BrainIntentName.NONE)

        from brain.agent import _parse_reaction

        return _parse_reaction(str(result.get("text", "") or ""), suggested_intent)
