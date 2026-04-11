"""Event queue helpers for gugupet_v2.

The body writes events; the brain reads and consumes them.
All access goes through these functions.
"""

from __future__ import annotations

import time
from typing import Any

from bridge.protocol import BodyEvent, BodyEventName
from runtime.state_store import read_event_log, write_event_log


_LOW_PRIORITY = {
    BodyEventName.OWNER_TOUCH,
    BodyEventName.OWNER_PET,
    BodyEventName.OWNER_PING,
    BodyEventName.IDLE_TICK,
    BodyEventName.STATE_TICK,
}
LOW_PRIORITY_TTL = 2.5


def push_event(name: str, payload: dict[str, Any] | None = None) -> int:
    """Append one event to the runtime queue.  Returns the assigned event id."""
    log = read_event_log()
    event_id = log.next_event_id
    log.events.append(
        {
            "id": event_id,
            "type": name,
            "ts": time.time(),
            "payload": payload or {},
        }
    )
    log.next_event_id = event_id + 1
    write_event_log(log)
    return event_id


def pending_events(last_event_id: int) -> list[BodyEvent]:
    """Return new events since last_event_id, compressed and sorted."""
    log = read_event_log()
    raw = [
        item
        for item in log.events
        if isinstance(item, dict) and int(item.get("id", 0) or 0) > last_event_id
    ]
    raw.sort(key=lambda e: int(e.get("id", 0) or 0))
    return [
        BodyEvent(
            id=int(e.get("id", 0)),
            name=str(e.get("type", "") or ""),
            ts=float(e.get("ts", 0.0) or 0.0),
            payload=dict(e.get("payload", {}) or {}),
        )
        for e in _compress(raw)
    ]


def _compress(events: list[dict]) -> list[dict]:
    """Keep only the latest of each low-priority type; always keep high-priority."""
    now = time.time()
    latest_user_id = max(
        (
            int(e.get("id", 0))
            for e in events
            if e.get("type") == BodyEventName.USER_MESSAGE
        ),
        default=0,
    )
    seen_low: dict[str, dict] = {}
    high: list[dict] = []
    latest_user: dict | None = None

    for e in events:
        etype = str(e.get("type", "") or "")
        eid = int(e.get("id", 0) or 0)
        ets = float(e.get("ts", 0.0) or 0.0)

        if etype in _LOW_PRIORITY:
            if latest_user_id:
                continue
            if ets > 0 and (now - ets) > LOW_PRIORITY_TTL:
                continue
            seen_low[etype] = e
        elif etype == BodyEventName.USER_MESSAGE:
            if eid == latest_user_id:
                latest_user = e
        else:
            high.append(e)

    result = high[:]
    if latest_user is not None:
        result.append(latest_user)
    result.extend(seen_low.values())
    result.sort(key=lambda e: int(e.get("id", 0) or 0))
    return result
