"""Build a distributable zip of gugupet_v2.

Run from the project root (where this file lives).
Creates gugupet_v2.zip at the specified path.
"""

import json
import os
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parent
OUT = Path(r"D:\Codex_work\gugupet_v2.zip")

EXCLUDE_NAMES = {
    "__pycache__",
    ".git",
    ".gitignore",
    "build_zip.py",
    "launcher.pid",
    "main.pid",
    "tests",
    "gugupet_v2",
    "debug_shortcut.py",
    "test_create.vbs",
}
EXCLUDE_EXTS = {".pyc", ".pyo", ".zip"}

RUNTIME_RESET = {
    "runtime/pet_action_events.json": {"next_event_id": 1, "events": []},
    "runtime/pet_action_command.json": {"seq": 0, "action": "none", "params": {}},
    "runtime/pet_action_status.json": {},
    "runtime/pet_conversation_history.json": {"entries": []},
    "runtime/pet_event_bridge_state.json": {"last_event_id": 0},
    "runtime/pet_first_launch.json": {"completed": False},
    "runtime/pet_manual_control.json": {
        "mode": "auto",
        "frame": "auto",
        "ground_lift_blocks": 7,
        "flight_sky_blocks": 24,
        "flight_side_blocks": 30,
    },
    "runtime/pet_ui_requests.json": {},
}

STATE_RESET = {
    "status": "idle",
    "bubble_text": "",
    "bubble_ts": 0.0,
    "chat_text": "",
    "chat_ts": 0.0,
    "pet_text": "",
    "pet_ts": 0.0,
    "brain_ts": 0.0,
    "active_dialog_event_id": 0,
    "brain_agent": "built_in",
    "pet_name": "咕咕",
    "pet_color": "",
    "drives": {"energy": 0.72, "social": 0.56, "curiosity": 0.68, "comfort": 0.74},
    "dominant_drive": "rest",
    "last_drive_update_ts": 0.0,
    "last_owner_attention_ts": 0.0,
    "last_autonomy_ts": 0.0,
    "next_autonomy_after": 20.0,
    "peek_trigger": 0.0,
}

CONFIG_TEMPLATE = """llm:
  enabled: false
  api_key: ''
  base_url: https://api.deepseek.com
  model: deepseek-chat
  timeout: 25.0
  temperature: 0.8
pet:
  name: 咕咕
  species: pigeon
drives:
  energy: 0.72
  social: 0.56
  curiosity: 0.68
  comfort: 0.74
brain:
  poll_interval: 0.8
  autonomy_min_idle: 14.0
  autonomy_cooldown_min: 18.0
  autonomy_cooldown_max: 34.0
body:
  pixel_size: 6
  window_width: 96
  window_height: 96
  fall_gravity: 1.2
  terminal_velocity: 28.0
  air_drag: 0.995
  wall_bounce_factor: 0.45
  ground_bounce_factor: 0.35
  ground_bounce_min_vy: 3.0
  fling_max_speed: 40.0
  drag_velocity_blend: 0.55
  drag_throw_sample_window: 0.18
  tick_ms: 50
memory:
  root: memory
  max_index_chars: 1200
  max_context_chars: 2400
  max_retrieved: 3
runtime:
  dir: runtime
  state_file: state.json
  event_file: pet_action_events.json
  command_file: pet_action_command.json
  status_file: pet_action_status.json
  bridge_file: pet_event_bridge_state.json
"""


def should_exclude(rel: str) -> bool:
    for part in Path(rel).parts:
        if part in EXCLUDE_NAMES:
            return True
    if Path(rel).suffix in EXCLUDE_EXTS:
        return True
    return False


def build():
    print(f"Building {OUT.name} from {SRC} ...")
    arc_root = "gugupet_v2"

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(SRC):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_NAMES]
            for fname in files:
                full = Path(root) / fname
                rel = full.relative_to(SRC).as_posix()
                if should_exclude(rel):
                    continue
                arc_name = f"{arc_root}/{rel}"
                if rel == "config.yaml":
                    zf.writestr(arc_name, CONFIG_TEMPLATE)
                elif rel == "state.json":
                    zf.writestr(
                        arc_name, json.dumps(STATE_RESET, ensure_ascii=False, indent=2)
                    )
                elif rel in RUNTIME_RESET:
                    zf.writestr(
                        arc_name,
                        json.dumps(RUNTIME_RESET[rel], ensure_ascii=False, indent=2),
                    )
                elif rel.startswith("memory/") and fname.endswith(".json"):
                    continue
                else:
                    zf.write(full, arc_name)

    size_kb = OUT.stat().st_size / 1024
    print(f"Done: {OUT}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    build()
