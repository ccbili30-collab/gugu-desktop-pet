"""Pixel-art desktop pet with simple physics and idle behaviors."""

from __future__ import annotations


import json

import math

import random

import re

import subprocess

import time

import tkinter as tk

import tkinter.font as tkfont

from datetime import datetime

from pathlib import Path


from PIL import Image, ImageDraw, ImageFont


from pet.pigeon_sprite import FRAMES, FRAME_GROUND_ROWS

from pet.openclaw_pet import extract_json_payload, read_pet_profile

from service_runtime import ensure_single_instance, read_json, runtime_file, write_json

from shared.platform import RECT, POINT, get_work_area, get_cursor_pos, generate_pet

from shared.particles import HeartParticle, TextParticle, TrailParticle, SpeechBubble


PROJECT_ROOT = Path(__file__).resolve().parents[1]


PIXEL_SIZE = 6

WINDOW_WIDTH = 400

WINDOW_HEIGHT = 300

TICK_MS = 16

RIGHT_CLICK_MULTI_WINDOW = 0.55

CHAT_PANEL_REFRESH_MS = 1200

FALL_GRAVITY = 0.6

TERMINAL_VELOCITY = 18.0

FLIGHT_HORIZONTAL_DAMPING = 0.97

FLIGHT_BOB_MAX = 3.2

FLIGHT_CURSOR_STEER = 0.085

FLING_MAX_SPEED = 80.0

DRAG_CONTINUE_FLIGHT_CHANCE = 0.45

FLING_CURVE_DISTANCE = 16.0

FLING_CURVE_RISE = 11.0

TRAIL_LIMIT = 260

LONG_FLIGHT_HOVER_THRESHOLD = 6.5

HOVER_IDLE_LAND_DELAY = 18.0

HOVER_CLICK_EXTEND = 8.0

DRAG_VELOCITY_BLEND = 0.55

DRAG_THROW_SAMPLE_WINDOW = 0.18

DRAG_THROW_MIN_SPEED = 0.48

WALL_BOUNCE_FACTOR = 0.45

GROUND_BOUNCE_FACTOR = 0.35

GROUND_BOUNCE_MIN_VY = 0.96

AIR_DRAG = 0.9984

HEART_QUEUE_CAP = 12

# --- 弹弓特效常量 ---
SLINGSHOT_MAX_PULL = 120  # 最大拉弦距离（像素）—— 短距即满力
SLINGSHOT_LAUNCH_SCALE = 0.9  # 拉伸距离→发射速度系数
SLINGSHOT_MAX_LAUNCH_SPEED = 38.0  # 发射最大速度（像素/tick）
SLINGSHOT_PANIC_INTERVAL = 80  # 惊慌状态切换间隔（ms）
SLINGSHOT_RECOIL_STEPS = 6  # 弦收回动画帧数
SLINGSHOT_STRING_COLOR = "#A8D8EA"  # 弦线颜色（淡蓝）
SLINGSHOT_STRING_WIDTH = 2  # 弦线宽度

HEART_EMIT_INTERVAL = 0.18

TOUCH_SIGNAL_COOLDOWN = 0.9

PET_SIGNAL_COOLDOWN = 1.2

SLEEP_WAKE_CLICK_WINDOW = 1.8

SLEEP_WAKE_REQUIRED_CLICKS = 3

WAKE_SHAKE_DURATION = 1.0

MANUAL_AWAKE_DURATION = 18.0

PET_BUBBLE_DURATION = 5.0

CHAT_BUBBLE_DURATION = 5.0

SLEEP_PARTICLE_COLOR = "#000000"

CHAT_BUBBLE_WRAP_WIDTH = 236

PET_BUBBLE_LEFT = 12

PET_BUBBLE_TOP_MIN = 48

PET_BUBBLE_TOP_OFFSET = 10

PET_BUBBLE_WRAP_WIDTH = 76

PET_BUBBLE_BOTTOM_MARGIN = 8

SLEEP_IDLE_DELAY = 180.0

GROUND_PADDING = 2

FLOOR_OFFSET = 0

FLY_LIFT_PX = 18

SPRITE_WIDTH = 16 * PIXEL_SIZE

SPRITE_HEIGHT = 16 * PIXEL_SIZE

CONTROL_FILE = runtime_file("pet_manual_control.json")

COMMAND_FILE = runtime_file("pet_action_command.json")

STATUS_FILE = runtime_file("pet_action_status.json")

EVENT_FILE = runtime_file("pet_action_events.json")

STATE_FILE = PROJECT_ROOT / "state.json"

CONFIG_FILE = PROJECT_ROOT / "config.yaml"

HISTORY_FILE = runtime_file("pet_conversation_history.json")

FIRST_LAUNCH_FILE = runtime_file("pet_first_launch.json")

UI_REQUEST_FILE = runtime_file("pet_ui_requests.json")

DEFAULT_CONTROL = {
    "mode": "auto",
    "frame": "auto",
    "use_full_screen_bounds": True,
    "ground_lift_blocks": 0,
    "flight_sky_blocks": 10,
    "flight_side_blocks": 12,
}

DEFAULT_COMMAND = {
    "seq": 0,
    "action": "none",
    "params": {},
    "source": "manual",
    "issued_at": 0.0,
}

DEFAULT_EVENT_LOG = {
    "next_event_id": 1,
    "events": [],
}

DEFAULT_BRAIN_STATE = {
    "status": "sleep",
    "bubble_text": "",
    "bubble_ts": 0.0,
    "chat_text": "",
    "chat_ts": 0.0,
    "pet_text": "",
    "pet_ts": 0.0,
    "brain_ts": 0.0,
    "active_dialog_event_id": 0,
}

DEFAULT_HISTORY = {
    "items": [],
}

DEFAULT_FIRST_LAUNCH = {
    "completed": False,
    "intro_done": False,
    "shortcut_created": False,
}

DEFAULT_UI_REQUESTS = {
    "chat_focus_seq": 0,
    "chat_focus_ts": 0.0,
}

BORED_TIMEOUT = 300.0

TIRED_TIMEOUT = 25.0

BRAIN_STALE_TIMEOUT = 20.0


PIXEL_COLORS = {
    "B": "#909090",
    "D": "#707070",
    "H": "#4A4A4A",
    "G": "#3CB371",
    "E": "#FFFFFF",
    "W": "#000000",
    "O": "#FF6600",
    "L": "#FF8C00",
    "T": "#B0B0C0",
    ".": None,
}


class DesktopPet:
    def __init__(self) -> None:

        self.pet = generate_pet("user123")

        self.root = tk.Tk()

        self.root.title("Desktop Pet")

        self.root.overrideredirect(True)

        self.root.wm_attributes("-topmost", True)

        self.root.wm_attributes("-transparentcolor", "magenta")

        self.screen_w = self.root.winfo_screenwidth()

        self.screen_h = self.root.winfo_screenheight()

        # Use full screen bounds instead of work area so the pet can use the whole desktop.

        self.work_left, self.work_top, self.work_right, self.work_bottom = (
            0,
            0,
            self.screen_w,
            self.screen_h,
        )

        self.base_floor_y = self.work_bottom - WINDOW_HEIGHT + FLOOR_OFFSET

        self.floor_y = self.base_floor_y

        self.base_ground_y = WINDOW_HEIGHT - GROUND_PADDING

        self.ground_y = self.base_ground_y

        self.win_x = max(self.work_left - 86, self.work_right - 86 - SPRITE_WIDTH - 40)

        self.win_y = self.floor_y

        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{self.win_x}+{self.win_y}")

        self.canvas = tk.Canvas(
            self.root,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            bg="magenta",
            highlightthickness=0,
        )

        self.canvas.pack()

        self.bubble_font = tkfont.Font(family="Microsoft YaHei UI", size=10)
        self.kaomoji_font = tkfont.Font(family="Microsoft YaHei UI", size=10)

        self.dialog_font = tkfont.Font(family="Microsoft YaHei UI", size=10)

        self.dialog_visible = False

        self.dialog_entry: tk.Entry | None = None

        self.dialog_shell: tk.Frame | None = None

        self.dialog_window_item: int | None = None

        self.dialog_tail_item: int | None = None

        self.history_window: tk.Toplevel | None = None

        self.history_canvas: tk.Canvas | None = None

        self.history_messages_frame: tk.Frame | None = None

        self.history_canvas_window: int | None = None

        self.history_input: tk.Text | None = None

        self.history_refresh_job: str | None = None

        self.last_history_signature: tuple[tuple[str, str, int], ...] = ()

        self.build_dialog_ui()

        self.anim_frame = 0

        self.state = "stand"

        self.direction = 1

        self.command_pose_frame: str | None = None

        self.walk_timer = 0

        self.peck_timer = 0

        self.peck_count = 0

        self.sit_timer = 0

        self.next_action_time = time.time() + random.uniform(0.8, 1.6)

        self.base_pet_x = 86.0

        self.pet_x = self.base_pet_x

        self.pet_y = 0.0

        self.pet_min_x = 18.0

        self.pet_max_x = WINDOW_WIDTH - SPRITE_WIDTH - 14.0

        self.hearts: list[HeartParticle] = []

        self.sleep_texts: list[TextParticle] = []

        self.flight_trails: list[TrailParticle] = []

        self.bubbles: dict[str, SpeechBubble] = {}

        self.heart_queue = 0

        self.next_heart_emit = 0.0

        self.drag_data = {"x": 0, "y": 0, "dragging": False}

        self.drag_dx = 0.0

        self.drag_dy = 0.0

        self.drag_velocity_x = 0.0

        self.drag_velocity_y = 0.0

        self.last_drag_sample_ts = 0.0

        self.last_drag_pointer_x = 0

        self.last_drag_pointer_y = 0

        self.drag_samples: list[tuple[float, float, float]] = []

        self.drag_moved = False

        # --- 弹弓状态 ---
        self.slingshot_active = False  # 是否正在拉弦
        self.slingshot_anchor_x = 0.0  # 鸟的中心位置（屏幕坐标，拉弦起点）
        self.slingshot_anchor_y = 0.0
        self.slingshot_mouse_x = 0.0  # 当前鼠标位置（屏幕坐标）
        self.slingshot_mouse_y = 0.0
        self.slingshot_pull_x = 0.0  # 拉伸向量 x
        self.slingshot_pull_y = 0.0  # 拉伸向量 y
        self.slingshot_panic_job: str | None = None  # 惊慌切换的 after job
        self.slingshot_recoil: int = 0  # 弦收回动画剩余帧数（>0表示正在收回）
        self.slingshot_recoil_x = 0.0  # 收回动画：当前弦末端 x
        self.slingshot_recoil_y = 0.0  # 收回动画：当前弦末端 y

        self.fall_velocity = 0.0

        self.flight_velocity_x = 0.0

        self.flight_bob_phase = random.uniform(0.0, math.tau)

        self.flight_bob_offset = 0.0

        self.is_falling = False

        self.airborne_started_at = 0.0

        self.hover_started_at = 0.0

        self.active_program: str | None = None

        self.program_data: dict[str, object] = {}

        self.last_command_seq = 0

        self.last_completed_seq = 0

        self.command_state = "idle"

        self.last_owner_ping_ts = time.time()

        self.last_chat_bubble_ts = 0.0

        self.last_pet_bubble_ts = 0.0

        self.bubble_queue: list[str] = []

        self.bubble_queue_next_at: float = 0.0

        self.bubble_queue: list[str] = []  # pending segments to show one by one

        self.bubble_queue_next_at: float = 0.0  # when to show next segment

        self.brain_state = DEFAULT_BRAIN_STATE.copy()

        self.busy_started_at = 0.0

        self.mood = "alert"

        self.mood_flags = {"tired": False, "bored": False}

        self.relax_until = 0.0

        self.waiting_for_brain = False

        self.waiting_until = 0.0

        self.pending_single_click_job: str | None = None

        self.last_touch_signal_ts = 0.0

        self.last_pet_signal_ts = 0.0

        self.sleep_click_count = 0

        self.last_sleep_click_ts = 0.0

        self.manual_awake_until = 0.0

        self.speed_scale = 1.0  # 当前活动倍速，tick 开头更新
        self.physics_scale = 1.0  # 物理速率倍率
        self.flight_speed_scale = 1.0  # 飞行速度倍率
        self._tick_ms = TICK_MS  # 当前帧间隔（由 fps_target 决定）
        self._last_tick_ts = 0.0  # 上一帧的时间戳（用于 delta-time）
        self._dt_scale = 1.0  # 帧率归一化因子：实际dt / 基准dt(50ms)

        self.next_sleep_particle_at = time.time() + random.uniform(2.0, 4.0)

        self.last_ground_lift_blocks = 0

        self.pending_right_click_job: str | None = None

        self.right_click_count = 0

        self.last_right_click_ts = 0.0

        self.last_history_chat_ts = 0.0

        self.last_social_bother_ts = 0.0  # last time we did a social bother

        self.social_bother_active = False  # currently in a bother follow_cursor burst

        self.force_sleeping = False  # true while in a commanded deep sleep

        self.force_sleep_wake_cooldown = 0.0  # don't auto-sleep again until this ts

        self.first_launch_state = read_json(FIRST_LAUNCH_FILE, DEFAULT_FIRST_LAUNCH)

        self.first_launch_stage = (
            "sleep" if not self.first_launch_state.get("completed", False) else "done"
        )

        self.first_launch_stage_started_at = 0.0

        self.first_launch_hops_remaining = 0

        self.first_launch_next_hop_at = 0.0

        write_json(COMMAND_FILE, read_json(COMMAND_FILE, DEFAULT_COMMAND))

        write_json(EVENT_FILE, read_json(EVENT_FILE, DEFAULT_EVENT_LOG))

        write_json(HISTORY_FILE, read_json(HISTORY_FILE, DEFAULT_HISTORY))

        write_json(FIRST_LAUNCH_FILE, self.first_launch_state)

        write_json(UI_REQUEST_FILE, read_json(UI_REQUEST_FILE, DEFAULT_UI_REQUESTS))

        self.write_runtime_status("idle")

        self.canvas.bind("<Button-1>", self.on_click)

        self.canvas.bind("<B1-Motion>", self.on_drag)

        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.canvas.bind("<ButtonPress-3>", self.on_slingshot_press)
        self.canvas.bind("<B3-Motion>", self.on_slingshot_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_slingshot_release)

        self.canvas.bind("<Double-Button-1>", self.on_double_click)

        self.tick()

    def current_control(self) -> dict[str, object]:

        control = read_json(CONTROL_FILE, DEFAULT_CONTROL)

        mode = str(control.get("mode", "auto")).lower()

        frame = str(control.get("frame", control.get("action", "auto"))).lower()

        if mode == "manual":
            mode = "frame"

        if mode not in {"auto", "frame"}:
            mode = "auto"

        try:
            ground_lift_blocks = int(control.get("ground_lift_blocks", 0))

        except (TypeError, ValueError):
            ground_lift_blocks = 0

        try:
            flight_sky_blocks = int(
                control.get("flight_sky_blocks", DEFAULT_CONTROL["flight_sky_blocks"])
            )

        except (TypeError, ValueError):
            flight_sky_blocks = int(DEFAULT_CONTROL["flight_sky_blocks"])

        try:
            flight_side_blocks = int(
                control.get("flight_side_blocks", DEFAULT_CONTROL["flight_side_blocks"])
            )

        except (TypeError, ValueError):
            flight_side_blocks = int(DEFAULT_CONTROL["flight_side_blocks"])

        try:
            speed_scale = float(control.get("speed_scale", 1.0) or 1.0)

        except (TypeError, ValueError):
            speed_scale = 1.0

        speed_scale = max(0.05, min(5.0, speed_scale))

        try:
            flight_speed_scale = float(control.get("flight_speed_scale", 1.0) or 1.0)
        except (TypeError, ValueError):
            flight_speed_scale = 1.0
        flight_speed_scale = max(0.3, min(4.0, flight_speed_scale))

        try:
            physics_scale = float(control.get("physics_scale", 1.0) or 1.0)
        except (TypeError, ValueError):
            physics_scale = 1.0
        physics_scale = max(0.3, min(4.0, physics_scale))

        try:
            fps_target = float(control.get("fps_target", 62) or 62)
        except (TypeError, ValueError):
            fps_target = 62.0
        fps_target = max(10.0, min(120.0, fps_target))

        try:
            anim_speed = float(control.get("anim_speed", 1.0) or 1.0)
        except (TypeError, ValueError):
            anim_speed = 1.0
        anim_speed = max(0.2, min(4.0, anim_speed))

        return {
            "mode": mode,
            "frame": frame,
            "use_full_screen_bounds": bool(control.get("use_full_screen_bounds", True)),
            "ground_lift_blocks": max(-20, min(20, ground_lift_blocks)),
            "flight_sky_blocks": max(2, min(24, flight_sky_blocks)),
            "flight_side_blocks": max(2, min(30, flight_side_blocks)),
            "speed_scale": speed_scale,
            "flight_speed_scale": flight_speed_scale,
            "physics_scale": physics_scale,
            "fps_target": fps_target,
            "anim_speed": anim_speed,
        }

    def current_command(self) -> dict[str, object]:

        command = read_json(COMMAND_FILE, DEFAULT_COMMAND)

        try:
            seq = int(command.get("seq", 0))

        except (TypeError, ValueError):
            seq = 0

        action = str(command.get("action", "none")).lower()

        params = command.get("params", {})

        if not isinstance(params, dict):
            params = {}

        return {
            "seq": max(0, seq),
            "action": action,
            "params": params,
            "source": str(command.get("source", "manual")),
            "issued_at": float(command.get("issued_at", 0.0) or 0.0),
        }

    def current_brain_state(self, now: float) -> dict[str, object]:

        state = read_json(STATE_FILE, DEFAULT_BRAIN_STATE)

        status = str(state.get("status", "sleep")).lower()

        status_aliases = {
            "busyread": "busy_read",
            "busywrite": "busy_write",
            "busybrowse": "busy_browse",
            "busythink": "busy_think",
        }

        status = status_aliases.get(status, status)

        try:
            bubble_ts = float(state.get("bubble_ts", 0.0) or 0.0)

        except (TypeError, ValueError):
            bubble_ts = 0.0

        try:
            brain_ts = float(state.get("brain_ts", 0.0) or 0.0)

        except (TypeError, ValueError):
            brain_ts = 0.0

        try:
            chat_ts = float(state.get("chat_ts", bubble_ts) or bubble_ts)

        except (TypeError, ValueError):
            chat_ts = bubble_ts

        try:
            pet_ts = float(state.get("pet_ts", 0.0) or 0.0)

        except (TypeError, ValueError):
            pet_ts = 0.0

        active_dialog_event_id = int(state.get("active_dialog_event_id", 0) or 0)

        chat_text = str(state.get("chat_text", state.get("bubble_text", ""))).strip()

        if brain_ts <= 0.0:
            brain_ts = bubble_ts

        if active_dialog_event_id and chat_text == "...":
            status = "busy_think"

        elif brain_ts <= 0.0 or (now - brain_ts) > BRAIN_STALE_TIMEOUT:
            status = "sleep"

        drives = state.get("drives", {})

        if not isinstance(drives, dict):
            drives = {}

        return {
            "status": status,
            "bubble_text": str(state.get("bubble_text", "")),
            "bubble_ts": bubble_ts,
            "chat_text": chat_text,
            "chat_ts": chat_ts,
            "pet_text": str(state.get("pet_text", "")),
            "pet_ts": pet_ts,
            "brain_ts": brain_ts,
            "active_dialog_event_id": active_dialog_event_id,
            "drives": drives,
        }

    def build_dialog_ui(self) -> None:

        shell = tk.Frame(self.root, bg="magenta", highlightthickness=0, bd=0)

        body = tk.Frame(
            shell,
            bg="#FFFFFF",
            highlightbackground="#BFE6C9",
            highlightthickness=2,
            bd=0,
        )

        body.pack()

        self.dialog_text_var = tk.StringVar(value="")

        entry = tk.Entry(
            body,
            textvariable=self.dialog_text_var,
            font=("Microsoft YaHei UI", 10),
            relief="flat",
            bd=2,
            bg="#FFFFFF",
            fg="#1E3A2B",
            insertbackground="#1E3A2B",
            width=8,
        )

        entry.grid(row=0, column=0, padx=(12, 6), pady=10)

        entry.bind("<Return>", self.submit_dialog)

        entry.bind("<Escape>", lambda _event: self.close_dialog())

        entry.bind("<KeyRelease>", lambda _event: self.update_dialog_layout())

        send = tk.Label(
            body,
            text="发送",
            bg="#95EC69",
            fg="#17301E",
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=10,
            pady=6,
            cursor="hand2",
        )

        send.grid(row=0, column=1, padx=(0, 10), pady=6)

        send.bind("<Button-1>", self.submit_dialog)

        self.dialog_shell = shell

        self.dialog_entry = entry

        self.dialog_send = send

        self.dialog_window_item = self.canvas.create_window(
            0, 0, window=shell, anchor="nw", state="hidden", tags="dialog_ui"
        )

        self.dialog_tail_item = self.canvas.create_polygon(
            0,
            0,
            0,
            0,
            0,
            0,
            fill="#FFFFFF",
            outline="#BFE6C9",
            width=2,
            state="hidden",
            tags="dialog_ui",
        )

    def update_dialog_layout(self) -> None:

        if not self.dialog_entry:
            return

        content = (
            self.dialog_text_var.get().strip()
            if hasattr(self, "dialog_text_var")
            else ""
        )

        width_chars = max(8, min(22, len(content) + 2))

        self.dialog_entry.configure(width=width_chars)

        self.root.update_idletasks()

        if self.dialog_visible:
            self.position_dialog()

    def sync_brain_state(self, now: float) -> None:

        self.brain_state = self.current_brain_state(now)

        chat_text = str(self.brain_state.get("chat_text", "")).strip()

        chat_ts = float(self.brain_state.get("chat_ts", 0.0) or 0.0)

        pet_text = str(self.brain_state.get("pet_text", "")).strip()

        pet_ts = float(self.brain_state.get("pet_ts", 0.0) or 0.0)

        if chat_text and chat_ts > self.last_chat_bubble_ts:
            self.last_chat_bubble_ts = chat_ts

            if chat_text == "...":
                self.set_bubble("chat", "...", duration=20.0)

            else:
                self.bubble_queue.clear()  # cancel any pending queue

                self.enqueue_chat_reply(chat_text)

                if chat_ts > self.last_history_chat_ts:
                    self.last_history_chat_ts = chat_ts

                    self.append_history("gugu", chat_text, chat_ts)

                self.waiting_for_brain = False

                self.waiting_until = 0.0

        if pet_text and pet_ts > self.last_pet_bubble_ts:
            self.last_pet_bubble_ts = pet_ts

            self.set_bubble("pet", pet_text, duration=PET_BUBBLE_DURATION)

        if self.waiting_for_brain and now >= self.waiting_until > 0:
            if int(self.brain_state.get("active_dialog_event_id", 0) or 0):
                self.waiting_until = now + 20.0

            else:
                self.waiting_for_brain = False

                self.waiting_until = 0.0

                chat_bubble = self.bubbles.get("chat")

                if chat_bubble and chat_bubble.text == "...":
                    self.clear_bubble("chat")

    def should_sleep(self, control: dict[str, object]) -> bool:

        if control["mode"] == "frame":
            return False

        if self.waiting_for_brain:
            return False

        if self.state == "wake" or time.time() < self.manual_awake_until:
            return False

        if self.active_program or self.drag_data["dragging"] or self.is_falling:
            return False

        if self.dialog_visible:
            return False

        if self.first_launch_pending():
            return self.first_launch_stage in {"sleep", "wake_pending"}

        if self.force_sleeping:
            return True

        # Low energy + low comfort forces sleep to recover

        drives = self.brain_state.get("drives", {})

        if isinstance(drives, dict):
            try:
                energy = float(drives.get("energy", 1.0) or 1.0)

                comfort = float(drives.get("comfort", 1.0) or 1.0)

                if energy < 0.15 and comfort < 0.25:
                    return True

            except (TypeError, ValueError):
                pass

        if (time.time() - self.last_owner_ping_ts) < SLEEP_IDLE_DELAY:
            return False

        return str(self.brain_state.get("status", "sleep")) == "sleep"

    def should_pause_for_brain(self, control: dict[str, object]) -> bool:

        # Only used for the thinking animation frame (idle1), not for freezing movement.

        return False

    def is_thinking(self) -> bool:
        """True while waiting for brain reply 鈥?used for the '!' animation only."""

        return (
            self.waiting_for_brain
            or str(self.brain_state.get("status", "")) == "busy_think"
        )

    def emit_event(self, event_type: str, payload: dict[str, object]) -> int:

        log = read_json(EVENT_FILE, DEFAULT_EVENT_LOG)

        try:
            next_event_id = int(log.get("next_event_id", 1))

        except (TypeError, ValueError):
            next_event_id = 1

        events = log.get("events", [])

        if not isinstance(events, list):
            events = []

        low_priority_types = {"owner_touch", "owner_pet", "owner_ping"}

        if event_type == "user_message":
            events = [
                item
                for item in events
                if isinstance(item, dict)
                and str(item.get("type", "")).strip() not in low_priority_types
            ]

        elif event_type in low_priority_types and self.waiting_for_brain:
            return 0

        events.append(
            {
                "id": next_event_id,
                "type": event_type,
                "payload": payload,
                "ts": time.time(),
            }
        )

        log["next_event_id"] = next_event_id + 1

        log["events"] = events[-40:]

        write_json(EVENT_FILE, log)

        return next_event_id

    def emit_pain_signal(self, source: str, intensity: float) -> None:

        now = time.time()

        if now - self.last_pet_signal_ts < PET_SIGNAL_COOLDOWN:
            return

        self.last_pet_signal_ts = now

        self.emit_event(
            "pet_pain",
            {
                "pet_state": self.state,
                "mood": self.mood,
                "source": source,
                "intensity": round(max(0.0, intensity), 2),
                "summary": f"The pet felt pain from a {source} impact.",
            },
        )

    def append_history(self, role: str, text: str, ts: float | None = None) -> None:

        cleaned = str(text).strip()

        if not cleaned or cleaned == "...":
            return

        history = read_json(HISTORY_FILE, DEFAULT_HISTORY)

        items = history.get("items", [])

        if not isinstance(items, list):
            items = []

        entry_ts = float(ts or time.time())

        role_name = "主人" if role == "owner" else "咕咕"

        entry = {
            "role": role,
            "name": role_name,
            "text": cleaned[:500],
            "ts": entry_ts,
        }

        if items:
            last = items[-1]

            if isinstance(last, dict):
                if (
                    str(last.get("role", "")) == role
                    and str(last.get("text", "")) == cleaned
                ):
                    return

        items.append(entry)

        history["items"] = items[-80:]

        write_json(HISTORY_FILE, history)

        self.refresh_history_panel()

    def history_items(self) -> list[dict[str, object]]:

        history = read_json(HISTORY_FILE, DEFAULT_HISTORY)

        items = history.get("items", [])

        if not isinstance(items, list):
            return []

        return [item for item in items if isinstance(item, dict)]

    def first_launch_pending(self) -> bool:

        return not bool(self.first_launch_state.get("completed", False))

    def save_first_launch_state(self) -> None:

        write_json(FIRST_LAUNCH_FILE, self.first_launch_state)

    def request_control_panel_chat(self) -> None:

        request = read_json(UI_REQUEST_FILE, DEFAULT_UI_REQUESTS)

        try:
            seq = int(request.get("chat_focus_seq", 0) or 0) + 1

        except (TypeError, ValueError):
            seq = 1

        request["chat_focus_seq"] = seq

        request["chat_focus_ts"] = time.time()

        write_json(UI_REQUEST_FILE, request)

    def ensure_desktop_shortcut(self) -> bool:

        shortcut_path = Path.home() / "Desktop" / "Gugu Pet Control.lnk"

        target_path = PROJECT_ROOT / "start.bat"

        if not target_path.exists():
            return False

        command = (
            "$shell = New-Object -ComObject WScript.Shell; "
            f"$shortcut = $shell.CreateShortcut('{str(shortcut_path).replace("'", "''")}'); "
            f"$shortcut.TargetPath = '{str(target_path).replace("'", "''")}'; "
            f"$shortcut.WorkingDirectory = '{str(PROJECT_ROOT).replace("'", "''")}'; "
            "$shortcut.WindowStyle = 1; "
            "$shortcut.Description = 'Gugu Pet Control'; "
            "$shortcut.Save()"
        )

        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
                creationflags=0x08000000,
            )

        except OSError:
            return False

        return result.returncode == 0

    def current_agent_binding(self) -> tuple[str, Path, Path | None]:

        agent_id = "gugu"

        sessions_dir = Path.home() / ".openclaw" / "agents" / agent_id / "sessions"

        if CONFIG_FILE.exists():
            try:
                for raw_line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
                    line = raw_line.strip()

                    if not line or line.startswith("#") or ":" not in line:
                        continue

                    key, value = line.split(":", 1)

                    key = key.strip()

                    value = value.strip().strip('"').strip("'")

                    if key == "agent_id" and value:
                        agent_id = value

                    elif key == "agent_sessions_path" and value:
                        sessions_dir = Path(value)

            except Exception:
                pass

        session_id = ""

        try:
            session_id = str(read_pet_profile(agent_id).get("session_id", "")).strip()

        except Exception:
            session_id = ""

        session_file = sessions_dir / f"{session_id}.jsonl" if session_id else None

        return agent_id, sessions_dir, session_file

    def extract_message_text(self, content: object) -> tuple[str, bool]:

        if isinstance(content, str):
            return content.strip(), False

        if not isinstance(content, list):
            return "", False

        parts: list[str] = []

        has_tool_call = False

        for item in content:
            if not isinstance(item, dict):
                continue

            item_type = str(item.get("type", "")).strip()

            if item_type == "text":
                parts.append(str(item.get("text", "")))

            elif item_type == "toolCall":
                has_tool_call = True

        return "\n".join(part for part in parts if part).strip(), has_tool_call

    def parse_session_timestamp(
        self, payload: dict[str, object], message: dict[str, object]
    ) -> float:

        raw_ts = message.get("timestamp", payload.get("timestamp", 0.0))

        if isinstance(raw_ts, (int, float)):
            ts = float(raw_ts)

            return ts / 1000.0 if ts > 1e10 else ts

        if isinstance(raw_ts, str):
            try:
                return datetime.fromisoformat(raw_ts.replace("Z", "+00:00")).timestamp()

            except Exception:
                return 0.0

        return 0.0

    def normalize_session_item(
        self, role: str, text: str, ts: float
    ) -> dict[str, object] | None:

        cleaned = str(text).strip()

        if not cleaned:
            return None

        if role == "user":
            if "Owner says:" in cleaned:
                owner_text = cleaned.split("Owner says:", 1)[1].strip()

                if owner_text:
                    return {
                        "role": "owner",
                        "name": "主人",
                        "text": owner_text[:500],
                        "ts": ts,
                    }

            # Drop non-owner system descriptions. Body should report facts,

            # and only AI-authored language should appear in history.

            return None

        cleaned = self.clean_display_reply(cleaned)

        if not cleaned:
            return None

        payload = extract_json_payload(cleaned)

        if isinstance(payload, dict):
            reply = self.clean_display_reply(
                str(payload.get("reply", "") or payload.get("say", "")).strip()
            )

            if reply:
                cleaned = reply

        if not cleaned or cleaned == "...":
            return None

        return {"role": "gugu", "name": "咕咕", "text": cleaned[:1200], "ts": ts}

    def clean_display_reply(self, text: str) -> str:
        cleaned = str(text or "").strip().replace("\n", " ")
        if not cleaned:
            return ""

        # Collapse whitespace only — do NOT strip brackets (kaomoji use them)
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Remove internal prompt/meta fragments that leaked into the reply
        meta_fragments = (
            "follow_cursor action",
            "现在想飞出去转转",
            "主人叫我了",
            "主人让我飞",
        )
        if any(f.lower() in cleaned.lower() for f in meta_fragments):
            parts = re.split(r"(?<=[。！？!?~])", cleaned)
            kept = [
                p.strip()
                for p in parts
                if p.strip() and not any(f.lower() in p.lower() for f in meta_fragments)
            ]
            cleaned = " ".join(kept).strip()

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def session_history_items(self) -> list[dict[str, object]]:

        _agent_id, _sessions_dir, session_file = self.current_agent_binding()

        if not session_file or not session_file.exists():
            return []

        items: list[dict[str, object]] = []

        try:
            with session_file.open(encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()

                    if not line:
                        continue

                    try:
                        payload = json.loads(line)

                    except Exception:
                        continue

                    if (
                        not isinstance(payload, dict)
                        or payload.get("type") != "message"
                    ):
                        continue

                    message = payload.get("message", {})

                    if not isinstance(message, dict):
                        continue

                    role = str(message.get("role", "")).strip()

                    if role not in {"user", "assistant"}:
                        continue

                    text, has_tool_call = self.extract_message_text(
                        message.get("content", [])
                    )

                    if role == "assistant" and has_tool_call:
                        continue

                    ts = self.parse_session_timestamp(payload, message)

                    item = self.normalize_session_item(role, text, ts)

                    if item is not None:
                        items.append(item)

        except Exception:
            return []

        return items[-80:]

    def combined_history_items(self) -> list[dict[str, object]]:

        session_items = self.session_history_items()

        local_items = self.history_items()

        merged: list[dict[str, object]] = list(session_items)

        for item in local_items:
            role = str(item.get("role", ""))

            text = str(item.get("text", ""))

            ts = float(item.get("ts", 0.0) or 0.0)

            duplicate = False

            for existing in session_items:
                if str(existing.get("role", "")) != role:
                    continue

                if str(existing.get("text", "")) != text:
                    continue

                if abs(float(existing.get("ts", 0.0) or 0.0) - ts) <= 20.0:
                    duplicate = True

                    break

            if duplicate:
                continue

            merged.append(item)

        merged.sort(key=lambda item: float(item.get("ts", 0.0) or 0.0))

        return merged[-80:]

    def refresh_history_panel(self) -> None:

        if (
            not self.history_window
            or not self.history_window.winfo_exists()
            or not self.history_messages_frame
            or not self.history_canvas
        ):
            return

        items = self.combined_history_items()

        signature = tuple(
            (
                str(item.get("role", "")),
                str(item.get("text", "")),
                int(float(item.get("ts", 0.0) or 0.0)),
            )
            for item in items
        )

        if signature == self.last_history_signature:
            return

        self.last_history_signature = signature

        current_view = self.history_canvas.yview()

        at_bottom = not current_view or current_view[1] >= 0.96

        for child in self.history_messages_frame.winfo_children():
            child.destroy()

        for item in items:
            text = str(item.get("text", "")).strip()

            if not text:
                continue

            role = str(item.get("role", ""))

            row = tk.Frame(self.history_messages_frame, bg="#ECE5DD")

            row.pack(fill="x", pady=4, padx=8)

            if role == "system":
                chip = tk.Label(
                    row,
                    text=text,
                    bg="#E8DDCA",
                    fg="#6E6050",
                    font=("Microsoft YaHei UI", 9),
                    padx=10,
                    pady=4,
                )

                chip.pack(anchor="center")

                continue

            is_owner = role == "owner"

            bubble_wrap = 240

            bubble = tk.Label(
                row,
                text=text,
                wraplength=bubble_wrap,
                justify="left",
                anchor="w",
                bg="#95EC69" if is_owner else "#FFFFFF",
                fg="#1F1F1F",
                font=("Microsoft YaHei UI", 10),
                padx=12,
                pady=8,
                bd=0,
                relief="flat",
            )

            name = tk.Label(
                row,
                text="主人" if is_owner else "咕咕",
                bg="#ECE5DD",
                fg="#8A7A68",
                font=("Microsoft YaHei UI", 8),
            )

            if is_owner:
                name.pack(anchor="e", padx=(90, 6))

                bubble.pack(anchor="e", padx=(70, 0))

            else:
                name.pack(anchor="w", padx=(6, 90))

                bubble.pack(anchor="w", padx=(0, 70))

        self.history_messages_frame.update_idletasks()

        self.history_canvas.configure(scrollregion=self.history_canvas.bbox("all"))

        if at_bottom:
            self.history_canvas.yview_moveto(1.0)

    def schedule_history_refresh(self) -> None:

        if not self.history_window or not self.history_window.winfo_exists():
            self.history_refresh_job = None

            return

        self.refresh_history_panel()

        self.history_refresh_job = self.history_window.after(
            CHAT_PANEL_REFRESH_MS, self.schedule_history_refresh
        )

    def open_history_panel(self) -> None:

        self.request_control_panel_chat()

        return

        if self.history_window and self.history_window.winfo_exists():
            self.history_window.deiconify()

            self.history_window.lift()

            self.refresh_history_panel()

            if not self.history_refresh_job:
                self.schedule_history_refresh()

            if self.history_input:
                self.history_input.focus_set()

            return

        window = tk.Toplevel(self.root)

        window.title("咕咕聊天")

        window.wm_attributes("-topmost", True)

        window.configure(bg="#F5F1E8")

        window.geometry("420x560+80+120")

        window.minsize(360, 420)

        window.protocol("WM_DELETE_WINDOW", self.close_history_panel)

        shell = tk.Frame(window, bg="#F5F1E8", padx=12, pady=12)

        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg="#F5F1E8")

        header.pack(fill="x")

        tk.Label(
            header,
            text="咕咕",
            bg="#F5F1E8",
            fg="#3D352C",
            font=("Microsoft YaHei UI", 12, "bold"),
        ).pack(side="left")

        tk.Label(
            header,
            text="宸插悓姝?OpenClaw 褰撳墠浼氳瘽",
            bg="#F5F1E8",
            fg="#8A7A68",
            font=("Microsoft YaHei UI", 8),
        ).pack(side="left", padx=10, pady=(4, 0))

        tk.Button(
            header,
            text="鍏抽棴",
            command=self.close_history_panel,
            bg="#E8DDCA",
            fg="#3D352C",
            relief="flat",
            cursor="hand2",
            font=("Microsoft YaHei UI", 9),
            padx=10,
            pady=4,
        ).pack(side="right")

        body = tk.Frame(shell, bg="#F5F1E8")

        body.pack(fill="both", expand=True, pady=(10, 0))

        message_card = tk.Frame(
            body,
            bg="#ECE5DD",
            highlightbackground="#D9CDB8",
            highlightthickness=1,
            bd=0,
        )

        message_card.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(message_card)

        scrollbar.pack(side="right", fill="y")

        canvas = tk.Canvas(
            message_card,
            bg="#ECE5DD",
            highlightthickness=0,
            bd=0,
            yscrollcommand=scrollbar.set,
        )

        canvas.pack(fill="both", expand=True)

        scrollbar.configure(command=canvas.yview)

        messages_frame = tk.Frame(canvas, bg="#ECE5DD")

        canvas_window = canvas.create_window((0, 0), window=messages_frame, anchor="nw")

        messages_frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(canvas_window, width=event.width),
        )

        composer = tk.Frame(shell, bg="#F5F1E8")

        composer.pack(fill="x", pady=(10, 0))

        input_box = tk.Text(
            composer,
            height=3,
            wrap="word",
            bg="#FFFFFF",
            fg="#1F1F1F",
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            font=("Microsoft YaHei UI", 10),
            highlightbackground="#D9CDB8",
            highlightthickness=1,
        )

        input_box.pack(side="left", fill="both", expand=True)

        input_box.bind("<Return>", self.submit_history_message)

        send_button = tk.Button(
            composer,
            text="发送",
            command=self.submit_history_message,
            bg="#95EC69",
            fg="#17301E",
            relief="flat",
            cursor="hand2",
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=10,
        )

        send_button.pack(side="left", padx=(10, 0))

        self.history_window = window

        self.history_canvas = canvas

        self.history_messages_frame = messages_frame

        self.history_canvas_window = canvas_window

        self.history_input = input_box

        self.refresh_history_panel()

        self.schedule_history_refresh()

        self.history_input.focus_set()

    def close_history_panel(self) -> None:

        if (
            self.history_refresh_job
            and self.history_window
            and self.history_window.winfo_exists()
        ):
            self.history_window.after_cancel(self.history_refresh_job)

        self.history_refresh_job = None

        if self.history_window and self.history_window.winfo_exists():
            self.history_window.destroy()

        self.history_window = None

        self.history_canvas = None

        self.history_messages_frame = None

        self.history_canvas_window = None

        self.history_input = None

        self.last_history_signature = ()

    def send_chat_message(self, text: str) -> bool:

        cleaned = str(text).strip()

        if not cleaned:
            return False

        self.append_history("owner", cleaned)

        self.record_owner_attention()

        self.waiting_for_brain = True

        self.waiting_until = time.time() + 20.0

        if self.state != "fly":
            self.state = "idle"

        now = time.time()

        current_state = read_json(STATE_FILE, DEFAULT_BRAIN_STATE)

        current_state["status"] = "busy_think"

        current_state["bubble_text"] = "..."

        current_state["bubble_ts"] = now

        current_state["chat_text"] = "..."

        current_state["chat_ts"] = now

        current_state["brain_ts"] = now

        current_state["active_dialog_event_id"] = 0

        event_id = self.emit_event(
            "user_message",
            {
                "text": cleaned[:200],
                "pet_state": self.state,
                "mood": self.mood,
                "summary": f"Owner spoke to the pet while it was in {self.state}.",
            },
        )

        current_state["active_dialog_event_id"] = event_id

        write_json(STATE_FILE, current_state)

        self.last_chat_bubble_ts = now

        self.set_bubble("chat", "...", duration=20.0)

        self.refresh_history_panel()

        return True

    def submit_history_message(self, _event: tk.Event | None = None) -> str | None:

        if not self.history_input:
            return None

        text = self.history_input.get("1.0", "end").strip()

        if not text:
            return "break"

        if self.send_chat_message(text):
            self.history_input.delete("1.0", "end")

        return "break"

    def add_bubble(
        self, text: str, duration: float = 2.0, kind: str = "speech"
    ) -> None:

        cleaned = str(text).strip()

        if not cleaned:
            return

        channel = "pet" if kind == "pet" else "chat"

        self.bubbles[channel] = SpeechBubble(
            cleaned, duration=duration, channel=channel
        )

    def set_bubble(self, channel: str, text: str, duration: float) -> None:

        cleaned = str(text).strip()

        if not cleaned:
            self.clear_bubble(channel)

            return

        self.bubbles[channel] = SpeechBubble(
            cleaned, duration=duration, channel=channel
        )

    def enqueue_chat_reply(self, text: str) -> None:

        import re as _re

        cleaned = str(text).strip()

        if not cleaned:
            return

        segments = [
            s.strip()
            for s in _re.split(r"(?<=[\u3002\uff01\uff1f!?~])", cleaned)
            if s.strip()
        ]

        if not segments:
            segments = [cleaned]

        if len(segments) == 1:
            self.set_bubble("chat", segments[0], CHAT_BUBBLE_DURATION)

            return

        self.bubble_queue = segments[:]

        self.bubble_queue_next_at = 0.0

    def tick_bubble_queue(self, now: float) -> None:

        if not self.bubble_queue:
            return

        if now < self.bubble_queue_next_at:
            return

        segment = self.bubble_queue.pop(0)

        duration = max(2.5, len(segment) * 0.12)

        self.set_bubble("chat", segment, duration)

        self.bubble_queue_next_at = now + duration + 0.6

    def enqueue_chat_reply(self, text: str) -> None:
        """Split a long reply into segments and queue them for sequential display."""

        import re

        cleaned = str(text).strip()

        if not cleaned:
            return

        # Split on sentence-ending punctuation, keeping the delimiter

        segments = [
            s.strip()
            for s in re.split(r"(?<=[!?~\u3002\uff01\uff1f\uff5e])", cleaned)
            if s.strip()
        ]

        if not segments:
            segments = [cleaned]

        # If only one short segment just show it immediately

        if len(segments) == 1:
            self.set_bubble("chat", segments[0], CHAT_BUBBLE_DURATION)

            return

        # Queue all segments; first fires immediately

        self.bubble_queue = segments[:]

        self.bubble_queue_next_at = 0.0  # show first one right away

    def tick_bubble_queue(self, now: float) -> None:
        """Pop the next queued bubble segment when ready."""

        if not self.bubble_queue:
            return

        if now < self.bubble_queue_next_at:
            return

        segment = self.bubble_queue.pop(0)

        duration = max(2.5, len(segment) * 0.12)  # ~0.12s per char, min 2.5s

        self.set_bubble("chat", segment, duration)

        # Next segment fires after this one finishes, plus a short gap

        self.bubble_queue_next_at = now + duration + 0.6

    def clear_bubble(self, channel: str) -> None:

        self.bubbles.pop(channel, None)

    def handle_sleep_interaction(self) -> None:

        now = time.time()

        if now - self.last_sleep_click_ts > SLEEP_WAKE_CLICK_WINDOW:
            self.sleep_click_count = 0

        self.last_sleep_click_ts = now

        self.sleep_click_count += 1

        self.emit_sleep_particles(count=3)

        if self.sleep_click_count >= SLEEP_WAKE_REQUIRED_CLICKS:
            self.sleep_click_count = 0

            self.start_wake_sequence()

    def start_wake_sequence(self) -> None:

        now = time.time()

        self.state = "wake"

        self.manual_awake_until = now + MANUAL_AWAKE_DURATION

        self.next_action_time = self.manual_awake_until

        if self.first_launch_pending():
            self.first_launch_stage = "wake_pending"

            self.first_launch_stage_started_at = now

    def start_high_jump(self) -> None:

        target_y = max(self.work_top + 42, self.floor_y - 180)

        target_x = self.clamp_window_x(
            self.win_x + (34 if self.direction >= 0 else -34)
        )

        curve = self.create_flight_curve(
            target_x=target_x,
            target_y=target_y,
            hold_seconds=0.0,
            duration_scale=0.85,
        )

        self.start_program("fly_to", curve)

        self.state = "fly"

        self.is_falling = False

    def start_intro_hop(self) -> None:

        self.state = "fly"

        self.is_falling = True

        self.flight_velocity_x = 0.0

        self.fall_velocity = -7.8

        self.first_launch_stage = "intro_hop"

        self.first_launch_stage_started_at = time.time()

    def finish_first_launch(self) -> None:

        self.first_launch_state["intro_done"] = True

        self.first_launch_state["completed"] = True

        if not self.first_launch_state.get("shortcut_created", False):
            self.first_launch_state["shortcut_created"] = self.ensure_desktop_shortcut()

        self.save_first_launch_state()

        self.first_launch_stage = "done"

        self.first_launch_stage_started_at = 0.0

        self.manual_awake_until = time.time() + MANUAL_AWAKE_DURATION

        self.state = "stand"

        self.next_action_time = time.time() + 0.8

    def update_first_launch_flow(self, now: float) -> bool:

        if not self.first_launch_pending():
            return False

        if self.first_launch_stage in {"sleep", "wake_pending"}:
            if (
                self.first_launch_stage == "wake_pending"
                and (now - self.first_launch_stage_started_at) >= WAKE_SHAKE_DURATION
            ):
                self.first_launch_stage = "intro_prompt"

                self.first_launch_stage_started_at = now

                self.state = "stand"

                self.emit_event(
                    "first_launch_prompt",
                    {
                        "pet_state": self.state,
                        "mood": self.mood,
                        "summary": "Pet woke up for the first time and wants to greet the owner.",
                    },
                )

            return True

        if self.first_launch_stage == "intro_prompt":
            self.state = "stand"

            if (now - self.first_launch_stage_started_at) >= 1.8:
                self.first_launch_stage = "intro_reply"

                self.first_launch_stage_started_at = now

                self.emit_event(
                    "first_launch_reply",
                    {
                        "pet_state": self.state,
                        "mood": self.mood,
                        "summary": "Pet is waiting for the owner to introduce themselves.",
                    },
                )

            return True

        if self.first_launch_stage == "intro_reply":
            self.state = "stand"

            if (now - self.first_launch_stage_started_at) >= 1.6:
                self.first_launch_hops_remaining = 2

                self.first_launch_next_hop_at = now

                self.first_launch_stage = "intro_hop_wait"

                self.first_launch_stage_started_at = now

            return True

        if self.first_launch_stage == "intro_hop_wait":
            self.state = "stand"

            if self.first_launch_hops_remaining <= 0:
                self.finish_first_launch()

                return True

            if now >= self.first_launch_next_hop_at:
                self.first_launch_hops_remaining -= 1

                self.start_intro_hop()

            return True

        if self.first_launch_stage == "intro_hop":
            if not self.is_falling and self.win_y >= (self.floor_y - 0.5):
                self.state = "stand"

                self.first_launch_stage = "intro_hop_wait"

                self.first_launch_stage_started_at = now

                self.first_launch_next_hop_at = now + 0.28

            return True

        return False

    def emit_sleep_particles(self, count: int = 2) -> None:

        symbols = ["z", "Z"]

        base_x = self.pet_x + 64

        base_y = self.pet_y + 10

        for index in range(max(1, count)):
            symbol = symbols[index % len(symbols)]

            self.sleep_texts.append(
                TextParticle(base_x, base_y, symbol, SLEEP_PARTICLE_COLOR, (10, 14))
            )

        self.sleep_texts = [
            particle for particle in self.sleep_texts if particle.is_alive()
        ][-12:]

    def emit_flight_trail(
        self,
        window_x: float,
        window_y: float,
        color: str,
        radius: float = 3.0,
        decay: float = 0.045,
    ) -> None:

        anchor_x, anchor_y = self.flight_anchor_screen(window_x, window_y)

        self.flight_trails.append(
            TrailParticle(anchor_x, anchor_y, color=color, radius=radius, decay=decay)
        )

        self.flight_trails = [
            particle for particle in self.flight_trails if particle.is_alive()
        ][-TRAIL_LIMIT:]

    def write_runtime_status(self, state: str) -> None:

        frame = self.command_pose_frame or self.frame_name()

        write_json(
            STATUS_FILE,
            {
                "active_program": self.active_program or "none",
                "command_state": state,
                "last_command_seq": self.last_command_seq,
                "last_completed_seq": self.last_completed_seq,
                "window_x": int(self.win_x),
                "window_y": int(self.win_y),
                "pet_screen_x": int(self.win_x + self.pet_x + (SPRITE_WIDTH / 2)),
                "pet_screen_y": int(self.win_y + self.pet_y + SPRITE_HEIGHT),
                "floor_y": int(self.floor_y),
                "screen_width": int(self.screen_w),
                "screen_height": int(self.screen_h),
                "work_left": int(self.work_left),
                "work_top": int(self.work_top),
                "work_right": int(self.work_right),
                "work_bottom": int(self.work_bottom),
                "direction": self.direction,
                "frame": frame,
                "pet_state": self.state,
                "brain_status": self.brain_state.get("status", "sleep"),
                "mood": self.mood,
                "dialog_open": self.dialog_visible,
                "grounded": (not self.drag_data["dragging"])
                and (not self.is_falling)
                and int(self.win_y) >= int(self.floor_y),
                "updated_at": time.time(),
            },
        )

    def apply_floor_control(self, control: dict[str, object]) -> None:

        lift_blocks = int(control["ground_lift_blocks"])

        lift_px = lift_blocks * PIXEL_SIZE

        if lift_px >= 0:
            self.floor_y = self.base_floor_y

            self.ground_y = self.base_ground_y - lift_px

        else:
            max_window_drop = max(
                0, (self.work_bottom - WINDOW_HEIGHT) - self.base_floor_y
            )

            window_drop = min(max_window_drop, -lift_px)

            self.floor_y = self.base_floor_y + window_drop

            self.ground_y = self.base_ground_y

        if (
            lift_blocks != self.last_ground_lift_blocks
            and not self.drag_data["dragging"]
            and not self.is_falling
            and self.active_program is None
        ):
            self.win_y = self.floor_y

            self.update_window_position()

        self.last_ground_lift_blocks = lift_blocks

    def apply_bounds_control(self, control: dict[str, object]) -> None:

        if bool(control.get("use_full_screen_bounds", True)):
            self.work_left, self.work_top, self.work_right, self.work_bottom = (
                0,
                0,
                self.screen_w,
                self.screen_h,
            )

        else:
            self.work_left, self.work_top, self.work_right, self.work_bottom = (
                get_work_area()
            )

        self.base_floor_y = self.work_bottom - WINDOW_HEIGHT + FLOOR_OFFSET

        self.floor_y = self.base_floor_y

        self.clamp_window()

    def apply_frame_preview(self, frame_name: str) -> None:

        frame_states = {
            "stand1": ("stand", 1),
            "stand2": ("stand", 1),
            "idle1": ("idle", 1),
            "idle2": ("idle", 1),
            "sleep": ("sleep", 1),
            "sit": ("sit", 1),
            "peck": ("peck", 1),
            "walk_left1": ("walk_left", -1),
            "walk_left2": ("walk_left", -1),
            "walk_right1": ("walk_right", 1),
            "walk_right2": ("walk_right", 1),
            "fly_left1": ("fly", -1),
            "fly_left2": ("fly", -1),
            "fly_right1": ("fly", 1),
            "fly_right2": ("fly", 1),
        }

        state, direction = frame_states.get(frame_name, ("stand", self.direction))

        self.state = state

        self.direction = direction

        self.flight_velocity_x = 0.0

        if self.state == "fly":
            self.is_falling = False

            self.fall_velocity = 0.0

    def update_window_position(self) -> None:

        self.root.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{int(self.win_x)}+{int(self.win_y)}"
        )

    def clamp_window(self) -> None:

        # win_x is the window's top-left corner; sprite is at pet_x offset inside

        pet_offset_x = self.pet_x

        max_x = self.work_right - pet_offset_x - SPRITE_WIDTH

        min_x = self.work_left - pet_offset_x

        self.win_x = min(max(self.win_x, min_x), max_x)

        # Vertical: allow win_y to go negative so sprite can reach screen top

        min_y = self.work_top - self.pet_y

        self.win_y = max(self.win_y, min_y)

    def clamp_window_x(self, x: float) -> float:

        pet_offset_x = self.pet_x

        return min(
            max(x, self.work_left - pet_offset_x),
            self.work_right - pet_offset_x - SPRITE_WIDTH,
        )

    def clamp_window_y(self, y: float) -> float:

        # Allow window y to go negative so sprite top can reach work_top

        min_y = self.work_top - self.pet_y

        return min(max(y, min_y), self.floor_y)

    def clamp_value(self, value: float, min_value: float, max_value: float) -> float:

        return max(min_value, min(max_value, value))

    def smoothstep(self, value: float) -> float:

        t = self.clamp_value(value, 0.0, 1.0)

        return t * t * (3.0 - (2.0 * t))

    def quadratic_bezier(self, p0: float, p1: float, p2: float, t: float) -> float:

        inv = 1.0 - t

        return (inv * inv * p0) + (2.0 * inv * t * p1) + (t * t * p2)

    def flight_anchor_offsets(self) -> tuple[float, float]:

        anchor_x = self.base_pet_x + (SPRITE_WIDTH * 0.5)

        anchor_y = self.frame_top_y("fly_right1") + (SPRITE_HEIGHT * 0.48)

        return anchor_x, anchor_y

    def flight_anchor_screen(
        self, window_x: float | None = None, window_y: float | None = None
    ) -> tuple[float, float]:

        anchor_x, anchor_y = self.flight_anchor_offsets()

        wx = self.win_x if window_x is None else float(window_x)

        wy = self.win_y if window_y is None else float(window_y)

        return wx + anchor_x, wy + anchor_y

    def window_target_for_anchor(
        self, anchor_screen_x: float, anchor_screen_y: float
    ) -> tuple[float, float]:

        offset_x, offset_y = self.flight_anchor_offsets()

        return (
            self.clamp_window_x(anchor_screen_x - offset_x),
            self.clamp_window_y(anchor_screen_y - offset_y),
        )

    def dedupe_path_points(
        self, points: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:

        deduped: list[tuple[float, float]] = []

        last_key: tuple[int, int] | None = None

        for px, py in points:
            key = (int(round(px)), int(round(py)))

            if key == last_key:
                continue

            deduped.append((px, py))

            last_key = key

        return deduped

    def find_text_font_path(self) -> Path | None:

        font_dir = Path("C:/Windows/Fonts")

        for candidate in (
            "msyh.ttc",
            "msyhbd.ttc",
            "simhei.ttf",
            "arial.ttf",
            "segoeui.ttf",
        ):
            path = font_dir / candidate

            if path.exists():
                return path

        return None

    def create_flight_curve(
        self,
        target_x: float,
        target_y: float,
        hold_seconds: float = 0.0,
        arc_bias: float = 1.0,
        duration_scale: float = 1.0,
        sway_scale: float = 1.0,
    ) -> dict[str, float]:

        start_x = float(self.win_x)

        start_y = float(self.win_y)

        delta_x = target_x - start_x

        delta_y = target_y - start_y

        distance = math.hypot(delta_x, delta_y)

        arc_height = (
            max(
                46.0,
                min(220.0, 58.0 + (abs(delta_x) * 0.24) + (max(0.0, delta_y) * 0.14)),
            )
            * arc_bias
        )

        control_x = (
            start_x
            + (delta_x * 0.5)
            + (
                self.choose_flight_direction(1 if delta_x >= 0 else -1)
                * min(42.0, abs(delta_x) * 0.08)
                * sway_scale
            )
        )

        control_y = min(start_y, target_y) - arc_height

        control_y = self.clamp_value(
            control_y, float(self.work_top), float(self.floor_y)
        )

        duration = self.clamp_value(
            (0.55 + (distance / 380.0)) * max(0.18, duration_scale), 0.12, 1.8
        )

        return {
            "start_x": start_x,
            "start_y": start_y,
            "control_x": control_x,
            "control_y": control_y,
            "target_x": target_x,
            "target_y": target_y,
            "started_at": time.time(),
            "duration": duration,
            "hold_seconds": hold_seconds,
            "last_x": start_x,
            "last_y": start_y,
        }

    def create_heart_path(self, scale: float = 1.0) -> list[tuple[float, float]]:

        base_scale = self.clamp_value(scale, 0.6, 1.8)

        size = 6.2 * base_scale

        center_x, current_anchor_y = self.flight_anchor_screen()

        _anchor_offset_x, anchor_offset_y = self.flight_anchor_offsets()

        ground_anchor_y = self.floor_y + anchor_offset_y

        center_y = min(current_anchor_y, ground_anchor_y - (90.0 * base_scale))

        points: list[tuple[float, float]] = []

        for step in range(1, 25):
            t = (math.tau * step) / 24.0

            x_norm = 16.0 * (math.sin(t) ** 3)

            y_norm = -(
                (13.0 * math.cos(t))
                - (5.0 * math.cos(2.0 * t))
                - (2.0 * math.cos(3.0 * t))
                - math.cos(4.0 * t)
            )

            px, py = self.window_target_for_anchor(
                center_x + (x_norm * size), center_y + (y_norm * size)
            )

            points.append((px, py))

        return self.dedupe_path_points(points)

    def create_circle_path(self, scale: float = 1.0) -> list[tuple[float, float]]:

        base_scale = self.clamp_value(scale, 0.6, 1.8)

        radius = 60.0 * base_scale

        center_x, current_anchor_y = self.flight_anchor_screen()

        _anchor_offset_x, anchor_offset_y = self.flight_anchor_offsets()

        ground_anchor_y = self.floor_y + anchor_offset_y

        center_y = min(current_anchor_y - 18.0, ground_anchor_y - (radius + 24.0))

        points: list[tuple[float, float]] = []

        for step in range(1, 33):
            t = (math.tau * step) / 32.0

            px, py = self.window_target_for_anchor(
                center_x + (math.cos(t) * radius),
                center_y + (math.sin(t) * radius),
            )

            points.append((px, py))

        return self.dedupe_path_points(points)

    def create_figure8_path(self, scale: float = 1.0) -> list[tuple[float, float]]:

        base_scale = self.clamp_value(scale, 0.6, 1.8)

        width = 78.0 * base_scale

        height = 48.0 * base_scale

        center_x, current_anchor_y = self.flight_anchor_screen()

        _anchor_offset_x, anchor_offset_y = self.flight_anchor_offsets()

        ground_anchor_y = self.floor_y + anchor_offset_y

        center_y = min(current_anchor_y - 16.0, ground_anchor_y - (height + 26.0))

        points: list[tuple[float, float]] = []

        for step in range(1, 37):
            t = (math.tau * step) / 36.0

            x_norm = math.sin(t)

            y_norm = math.sin(t) * math.cos(t)

            px, py = self.window_target_for_anchor(
                center_x + (x_norm * width),
                center_y + (y_norm * height * 2.0),
            )

            points.append((px, py))

        return self.dedupe_path_points(points)

    def create_spiral_path(self, scale: float = 1.0) -> list[tuple[float, float]]:

        base_scale = self.clamp_value(scale, 0.7, 1.8)

        center_x, current_anchor_y = self.flight_anchor_screen()

        _anchor_offset_x, anchor_offset_y = self.flight_anchor_offsets()

        ground_anchor_y = self.floor_y + anchor_offset_y

        center_y = min(current_anchor_y - 24.0, ground_anchor_y - (96.0 * base_scale))

        max_radius = 74.0 * base_scale

        turns = 2.2

        steps = 42

        points: list[tuple[float, float]] = []

        for step in range(1, steps + 1):
            progress = step / steps

            angle = math.tau * turns * progress

            radius = max_radius * progress

            px, py = self.window_target_for_anchor(
                center_x + (math.cos(angle) * radius),
                center_y + (math.sin(angle) * radius),
            )

            points.append((px, py))

        return self.dedupe_path_points(points)

    def create_wave_path(self, scale: float = 1.0) -> list[tuple[float, float]]:

        base_scale = self.clamp_value(scale, 0.7, 1.8)

        anchor_x, current_anchor_y = self.flight_anchor_screen()

        _anchor_offset_x, anchor_offset_y = self.flight_anchor_offsets()

        ground_anchor_y = self.floor_y + anchor_offset_y

        start_x = self.clamp_value(
            anchor_x - (110.0 * base_scale),
            self.work_left + 36.0,
            self.work_right - 260.0,
        )

        base_y = min(current_anchor_y - 18.0, ground_anchor_y - (72.0 * base_scale))

        amplitude = 34.0 * base_scale

        length = 220.0 * base_scale

        points: list[tuple[float, float]] = []

        for step in range(1, 31):
            progress = step / 30.0

            angle = progress * math.tau * 2.2

            px, py = self.window_target_for_anchor(
                start_x + (progress * length),
                base_y + (math.sin(angle) * amplitude),
            )

            points.append((px, py))

        return self.dedupe_path_points(points)

    def create_shape_path(
        self, shape: str, scale: float = 1.0
    ) -> list[tuple[float, float]]:

        normalized = str(shape).strip().lower()

        if normalized == "heart":
            return self.create_heart_path(scale)

        if normalized in {"circle", "loop"}:
            return self.create_circle_path(scale)

        if normalized in {"figure8", "figure_8", "8", "infinity"}:
            return self.create_figure8_path(scale)

        if normalized == "spiral":
            return self.create_spiral_path(scale)

        if normalized in {"wave", "sine"}:
            return self.create_wave_path(scale)

        return []

    def create_text_path(
        self, text: str, scale: float = 1.0
    ) -> list[tuple[float, float]]:

        cleaned = re.sub(r"\s+", " ", str(text).strip())

        if not cleaned:
            return []

        cleaned = cleaned[:8]

        font_path = self.find_text_font_path()

        if font_path is None:
            return []

        base_scale = self.clamp_value(scale, 0.7, 1.8)

        image_w = 240

        image_h = 124

        font_size = int(
            max(28, min(72, (58 - (max(0, len(cleaned) - 2) * 6)) * base_scale))
        )

        image = Image.new("L", (image_w, image_h), 0)

        draw = ImageDraw.Draw(image)

        font = ImageFont.truetype(str(font_path), font_size)

        bbox = draw.textbbox((0, 0), cleaned, font=font, stroke_width=0)

        text_w = bbox[2] - bbox[0]

        text_h = bbox[3] - bbox[1]

        text_x = max(8, (image_w - text_w) // 2)

        text_y = max(8, (image_h - text_h) // 2)

        draw.text((text_x, text_y), cleaned, font=font, fill=255)

        anchor_x, current_anchor_y = self.flight_anchor_screen()

        _anchor_offset_x, anchor_offset_y = self.flight_anchor_offsets()

        ground_anchor_y = self.floor_y + anchor_offset_y

        screen_left = self.clamp_value(
            anchor_x - (image_w / 2),
            self.work_left + 14,
            self.work_right - image_w - 14,
        )

        screen_top = self.clamp_value(
            min(current_anchor_y - 54, ground_anchor_y - image_h - 34),
            self.work_top + 18,
            max(self.work_top + 18, ground_anchor_y - image_h - 18),
        )

        cell = max(5, int(round(6.0 * base_scale)))

        points: list[tuple[float, float]] = []

        for row_index, y in enumerate(range(0, image_h, cell)):
            row_points: list[tuple[float, float]] = []

            for x in range(0, image_w, cell):
                crop = image.crop(
                    (x, y, min(image_w, x + cell), min(image_h, y + cell))
                )

                if crop.getbbox() is None:
                    continue

                anchor_target_x = screen_left + x + (cell * 0.5)

                anchor_target_y = screen_top + y + (cell * 0.5)

                row_points.append(
                    self.window_target_for_anchor(anchor_target_x, anchor_target_y)
                )

            if row_index % 2 == 1:
                row_points.reverse()

            points.extend(row_points)

        points = self.dedupe_path_points(points)

        if len(points) > 120:
            points = points[::2]

        return points

    def create_drag_glide_curve(self, control: dict[str, object]) -> dict[str, float]:

        preferred = (
            1
            if self.drag_velocity_x > 0
            else -1
            if self.drag_velocity_x < 0
            else self.direction
        )

        self.direction = self.choose_flight_direction(preferred)

        launch_speed, glide_speed = self.flight_arc(control, scale=0.9)

        fling_vx = self.clamp_value(
            self.drag_velocity_x, -FLING_MAX_SPEED, FLING_MAX_SPEED
        )

        fling_vy = self.clamp_value(
            self.drag_velocity_y, -FLING_MAX_SPEED, FLING_MAX_SPEED
        )

        horizontal_distance = self.clamp_value(
            (fling_vx * FLING_CURVE_DISTANCE) + (self.direction * glide_speed * 18.0),
            -280.0,
            280.0,
        )

        target_x = self.clamp_window_x(self.win_x + horizontal_distance)

        target_y = self.clamp_window_y(
            min(self.floor_y - 12.0, self.win_y + max(72.0, abs(fling_vy) * 18.0))
        )

        fling_strength = min(1.0, (abs(fling_vx) + abs(fling_vy)) / 18.0)

        motion = self.create_flight_curve(
            target_x,
            target_y,
            0.0,
            arc_bias=0.54,
            duration_scale=0.86 + (fling_strength * 0.14),
            sway_scale=0.18,
        )

        motion["control_x"] = self.clamp_window_x(
            self.win_x + (horizontal_distance * 0.46)
        )

        motion["control_y"] = self.clamp_window_y(
            min(self.win_y, target_y)
            - max(52.0, abs(fling_vy) * FLING_CURVE_RISE, abs(launch_speed) * 10.0)
        )

        motion["residual_vx"] = (
            fling_vx
            if abs(fling_vx) > 1.0
            else self.direction * max(1.8, glide_speed * 0.7)
        )

        motion["residual_vy"] = max(0.8, abs(fling_vy) * 0.24, abs(launch_speed) * 0.14)

        return motion

    def advance_curve_motion(self, motion: dict[str, float]) -> bool:

        target_x = float(motion.get("target_x", self.win_x))

        target_y = float(motion.get("target_y", self.win_y))

        started_at = float(motion.get("started_at", time.time()))

        duration = max(0.2, float(motion.get("duration", 0.8)))

        control_x = float(motion.get("control_x", (self.win_x + target_x) * 0.5))

        control_y = float(motion.get("control_y", min(self.win_y, target_y) - 72.0))

        progress = self.smoothstep((time.time() - started_at) / duration)

        last_x = float(motion.get("last_x", self.win_x))

        last_y = float(motion.get("last_y", self.win_y))

        next_x = self.quadratic_bezier(
            float(motion.get("start_x", self.win_x)), control_x, target_x, progress
        )

        next_y = self.quadratic_bezier(
            float(motion.get("start_y", self.win_y)), control_y, target_y, progress
        )

        self.direction = 1 if next_x >= last_x else -1

        self.state = "fly"

        self.is_falling = False

        self.flight_velocity_x = next_x - last_x

        self.fall_velocity = next_y - last_y

        self.win_x = self.clamp_window_x(next_x)

        self.win_y = self.clamp_window_y(next_y)

        motion["last_x"] = self.win_x

        motion["last_y"] = self.win_y

        trail_color = str(motion.get("trail_color", "") or "").strip()

        if trail_color:
            trail_radius = float(motion.get("trail_radius", 3.0) or 3.0)

            trail_decay = float(motion.get("trail_decay", 0.04) or 0.04)

            self.emit_flight_trail(
                self.win_x, self.win_y, trail_color, trail_radius, trail_decay
            )

        self.update_window_position()

        return progress >= 0.999

    def update_flight_bob(self, now: float) -> None:

        if not self.hover_is_buzzing():
            self.flight_bob_offset *= 0.7

            if abs(self.flight_bob_offset) < 0.2:
                self.flight_bob_offset = 0.0

            return

        amplitude = min(FLIGHT_BOB_MAX, 5.8)

        self.flight_bob_phase += 0.62

        self.flight_bob_offset = math.sin(self.flight_bob_phase) * amplitude

    def is_hovering_flight(self) -> bool:

        return self.active_program == "hover"

    def hover_is_buzzing(self) -> bool:

        return self.is_hovering_flight() and bool(self.program_data.get("buzzing"))

    def update_airborne_state(self, now: float) -> None:

        airborne = (
            self.drag_data["dragging"]
            or self.is_falling
            or self.win_y < (self.floor_y - 0.5)
            or self.state == "fly"
            or self.active_program in {"fly_to", "fly_path", "follow_cursor", "hover"}
        )

        if airborne:
            if self.airborne_started_at <= 0.0:
                self.airborne_started_at = now

            if self.is_hovering_flight() and self.hover_started_at <= 0.0:
                self.hover_started_at = now

        else:
            self.airborne_started_at = 0.0

            self.hover_started_at = 0.0

    def airborne_duration(self, now: float) -> float:

        if self.airborne_started_at <= 0.0:
            return 0.0

        return max(0.0, now - self.airborne_started_at)

    def start_hover_program(
        self,
        target_x: float | None = None,
        target_y: float | None = None,
        duration: float = HOVER_IDLE_LAND_DELAY,
        *,
        buzzing: bool = False,
        send_tired: bool = False,
        source: str = "hover",
    ) -> None:

        now = time.time()

        hover_x = self.clamp_window_x(
            self.win_x if target_x is None else float(target_x)
        )

        hover_y = self.clamp_window_y(
            self.win_y if target_y is None else float(target_y)
        )

        self.start_program(
            "hover",
            {
                "target_x": hover_x,
                "target_y": hover_y,
                "until": now + max(1.0, duration),
                "entered_at": now,
                "buzzing": bool(buzzing),
                "source": source,
            },
        )

        self.hover_started_at = now

        self.state = "fly"

        self.is_falling = False

        self.flight_velocity_x = 0.0

        self.fall_velocity = 0.0

        self.win_x = hover_x

        self.win_y = hover_y

        self.update_window_position()

        if send_tired and not self.mood_flags["tired"]:
            self.mood = "tired"

            self.mood_flags["tired"] = True

            self.emit_event(
                "pet_need",
                {
                    "need": "tired",
                    "pet_state": "hover",
                    "summary": "鸽子连续动作过久，现在有点疲惫",
                },
            )

    def extend_hover(self, seconds: float = HOVER_CLICK_EXTEND) -> None:

        if not self.is_hovering_flight():
            return

        now = time.time()

        current_until = float(self.program_data.get("until", now))

        self.program_data["until"] = max(current_until, now) + max(0.6, seconds)

    def record_drag_sample(self, now: float, raw_vx: float, raw_vy: float) -> None:

        self.drag_samples.append((now, raw_vx, raw_vy))

        cutoff = now - DRAG_THROW_SAMPLE_WINDOW

        self.drag_samples = [
            sample for sample in self.drag_samples if sample[0] >= cutoff
        ]

    def release_throw_velocity(self) -> tuple[float, float]:

        if not self.drag_samples:
            return self.drag_velocity_x, self.drag_velocity_y

        latest_ts = self.drag_samples[-1][0]

        weighted_vx = 0.0

        weighted_vy = 0.0

        total_weight = 0.0

        for sample_ts, sample_vx, sample_vy in self.drag_samples:
            age = max(0.0, latest_ts - sample_ts)

            weight = max(0.15, 1.0 - (age / max(0.05, DRAG_THROW_SAMPLE_WINDOW)))

            weighted_vx += sample_vx * weight

            weighted_vy += sample_vy * weight

            total_weight += weight

        if total_weight <= 0.0:
            return self.drag_velocity_x, self.drag_velocity_y

        fling_vx = weighted_vx / total_weight

        fling_vy = weighted_vy / total_weight

        if (
            abs(fling_vx) < DRAG_THROW_MIN_SPEED
            and abs(fling_vy) < DRAG_THROW_MIN_SPEED
        ):
            return self.drag_velocity_x, self.drag_velocity_y

        return (
            self.clamp_value(fling_vx, -FLING_MAX_SPEED, FLING_MAX_SPEED),
            self.clamp_value(fling_vy, -FLING_MAX_SPEED, FLING_MAX_SPEED),
        )

    def maybe_rest_after_flight(
        self,
        *,
        target_x: float | None = None,
        target_y: float | None = None,
        source: str = "flight",
    ) -> bool:

        now = time.time()

        if self.win_y >= self.floor_y:
            return False

        if self.airborne_duration(now) < LONG_FLIGHT_HOVER_THRESHOLD:
            return False

        self.start_hover_program(
            target_x=target_x,
            target_y=target_y,
            duration=HOVER_IDLE_LAND_DELAY,
            buzzing=True,
            send_tired=True,
            source=source,
        )

        return True

    def set_control_values(self, **updates: int) -> None:

        control = read_json(CONTROL_FILE, DEFAULT_CONTROL)

        for key, value in updates.items():
            control[key] = int(value)

        write_json(CONTROL_FILE, control)

    def record_owner_attention(self) -> None:

        self.last_owner_ping_ts = time.time()

        self.mood_flags["bored"] = False

        if self.mood == "bored":
            self.mood = "alert"

    def cancel_active_program(self, state: str = "idle") -> None:

        self.active_program = None

        self.program_data = {}

        self.command_pose_frame = None

        self.command_state = state

    def complete_active_program(self) -> None:

        if self.last_command_seq > self.last_completed_seq:
            self.last_completed_seq = self.last_command_seq

        self.cancel_active_program("completed")

    def start_program(self, name: str, data: dict[str, object]) -> None:

        self.active_program = name

        self.program_data = data

        self.command_pose_frame = None

        self.command_state = "running"

    def current_state_summary(self) -> str:

        if self.state == "fly":
            return "椋炶"

        if self.state in {"walk_left", "walk_right"}:
            return "琛岃蛋"

        if self.state == "peck":
            return "鍟勫湴"

        if self.state == "sit":
            return "鍧愪笅"

        if self.state == "idle":
            return "鏀炬澗"

        return "绔欑珛"

    def current_state_summary(self) -> str:

        if self.state == "fly":
            return "椋炶"

        if self.state in {"walk_left", "walk_right"}:
            return "琛岃蛋"

        if self.state == "peck":
            return "鍟勫湴"

        if self.state == "sit":
            return "鍧愪笅"

        if self.state == "idle":
            return "鏀炬澗"

        if self.state == "sleep":
            return "鐫＄湢"

        return "绔欑珛"

    def open_dialog(self) -> None:

        if self.dialog_window and self.dialog_window.winfo_exists():
            self.position_dialog()

            if self.dialog_entry:
                self.dialog_entry.focus_set()

                self.dialog_entry.selection_range(0, "end")

            return

        window = tk.Toplevel(self.root)

        window.title("和咕咕说话")

        window.wm_attributes("-topmost", True)

        window.configure(bg="#FFF8EE")

        window.resizable(False, False)

        window.protocol("WM_DELETE_WINDOW", self.close_dialog)

        shell = tk.Frame(window, bg="#FFF8EE", padx=10, pady=10)

        shell.pack(fill="both", expand=True)

        self.dialog_label = tk.Label(
            shell,
            text="和咕咕说点什么",
            bg="#FFF8EE",
            fg="#4A3D31",
            font=("Microsoft YaHei UI", 10),
        )

        self.dialog_label.pack(anchor="w")

        self.dialog_entry = tk.Entry(shell, font=("Microsoft YaHei UI", 10), width=28)

        self.dialog_entry.pack(fill="x", pady=(8, 8))

        self.dialog_entry.bind("<Return>", self.submit_dialog)

        self.dialog_entry.bind("<Escape>", lambda _event: self.close_dialog())

        button_row = tk.Frame(shell, bg="#FFF8EE")

        button_row.pack(fill="x")

        tk.Button(
            button_row,
            text="发送",
            command=self.submit_dialog,
            bg="#E8D5B6",
            fg="#4A3D31",
            relief="flat",
            cursor="hand2",
            font=("Bahnschrift SemiBold", 10),
            padx=12,
            pady=6,
        ).pack(side="left")

        tk.Button(
            button_row,
            text="鍏抽棴",
            command=self.close_dialog,
            bg="#F1E5D3",
            fg="#4A3D31",
            relief="flat",
            cursor="hand2",
            font=("Bahnschrift SemiBold", 10),
            padx=12,
            pady=6,
        ).pack(side="left", padx=8)

        self.dialog_window = window

        self.position_dialog()

        self.dialog_entry.focus_set()

    def position_dialog(self) -> None:

        if not self.dialog_window or not self.dialog_window.winfo_exists():
            return

        dialog_w = 300

        dialog_h = 110

        pet_center_x = self.win_x + self.pet_x + (SPRITE_WIDTH / 2)

        pet_top_y = self.win_y + self.pet_y

        right_x = pet_center_x + 26

        left_x = pet_center_x - dialog_w - 26

        top_y = pet_top_y - dialog_h - 18

        if right_x + dialog_w <= self.screen_w - 12:
            dialog_x = right_x

        elif left_x >= 12:
            dialog_x = left_x

        else:
            dialog_x = max(
                12, min(pet_center_x - (dialog_w / 2), self.screen_w - dialog_w - 12)
            )

        dialog_y = max(self.work_top + 12, top_y)

        self.dialog_window.geometry(
            f"{dialog_w}x{dialog_h}+{int(dialog_x)}+{int(dialog_y)}"
        )

    def close_dialog(self) -> None:

        if self.dialog_window and self.dialog_window.winfo_exists():
            self.dialog_window.destroy()

        self.dialog_window = None

        self.dialog_entry = None

        self.dialog_label = None

    def submit_dialog(self, _event: tk.Event | None = None) -> None:

        if not self.dialog_entry:
            return

        text = self.dialog_entry.get().strip()

        if not text:
            self.close_dialog()

            return

        self.append_history("owner", text)

        self.record_owner_attention()

        self.waiting_for_brain = True

        self.waiting_until = time.time() + 20.0

        if self.state != "fly":
            self.state = "idle"

        now = time.time()

        current_state = read_json(STATE_FILE, DEFAULT_BRAIN_STATE)

        current_state["status"] = "busy_think"

        current_state["bubble_text"] = "..."

        current_state["bubble_ts"] = now

        current_state["brain_ts"] = now

        current_state["active_dialog_event_id"] = 0

        event_id = self.emit_event(
            "user_message",
            {
                "text": text[:200],
                "pet_state": self.state,
                "mood": self.mood,
                "summary": f"Owner spoke to the pet while it was in {self.state}.",
            },
        )

        current_state["active_dialog_event_id"] = event_id

        write_json(STATE_FILE, current_state)

        self.last_brain_bubble_ts = now

        self.remove_bubbles("thinking")

        self.add_bubble("...", duration=15.0, kind="thinking")

        self.close_dialog()

    def open_dialog(self) -> None:

        if self.dialog_visible:
            self.position_dialog()

            if self.dialog_entry:
                self.dialog_entry.focus_set()

            return

        self.dialog_visible = True

        self.update_dialog_layout()

        self.position_dialog()

        self.canvas.itemconfigure("dialog_ui", state="normal")

        if self.dialog_entry:
            self.dialog_entry.focus_set()

    def position_dialog(self) -> None:

        if not self.dialog_visible or self.dialog_window_item is None:
            return

        self.root.update_idletasks()

        dialog_w = self.dialog_shell.winfo_reqwidth() if self.dialog_shell else 206

        dialog_h = self.dialog_shell.winfo_reqheight() if self.dialog_shell else 44

        pet_mid_y = self.pet_y + 34

        dialog_x = self.pet_x + SPRITE_WIDTH - 18

        dialog_x = max(
            self.pet_x + SPRITE_WIDTH - 24, min(dialog_x, WINDOW_WIDTH - dialog_w - 10)
        )

        dialog_y = max(
            18, min(pet_mid_y - (dialog_h / 2), WINDOW_HEIGHT - dialog_h - 18)
        )

        tail_mid_y = dialog_y + min(26, dialog_h - 10)

        tail = [
            dialog_x - 2,
            tail_mid_y,
            dialog_x + 12,
            tail_mid_y - 7,
            dialog_x + 12,
            tail_mid_y + 7,
        ]

        self.canvas.coords(self.dialog_window_item, dialog_x, dialog_y)

        if self.dialog_tail_item is not None:
            self.canvas.coords(self.dialog_tail_item, *tail)

            self.canvas.itemconfigure(self.dialog_tail_item, state="normal")

    def close_dialog(self) -> None:

        self.dialog_visible = False

        if self.dialog_window_item is not None:
            self.canvas.itemconfigure(self.dialog_window_item, state="hidden")

        if self.dialog_tail_item is not None:
            self.canvas.itemconfigure(self.dialog_tail_item, state="hidden")

        if self.dialog_entry:
            self.dialog_entry.delete(0, "end")

        if hasattr(self, "dialog_text_var"):
            self.dialog_text_var.set("")

    def submit_dialog(self, _event: tk.Event | None = None) -> None:

        if not self.dialog_entry:
            return

        text = self.dialog_entry.get().strip()

        if not text:
            self.close_dialog()

            return

        self.send_chat_message(text)

        self.close_dialog()

    def refresh_pet_needs(self, now: float) -> None:

        busy_now = self.active_program is not None or self.state in {
            "fly",
            "walk_left",
            "walk_right",
        }

        if busy_now:
            if self.busy_started_at <= 0:
                self.busy_started_at = now

            elif (
                now - self.busy_started_at >= TIRED_TIMEOUT
                and not self.mood_flags["tired"]
            ):
                self.mood = "tired"

                self.mood_flags["tired"] = True

                self.emit_event(
                    "pet_need",
                    {
                        "need": "tired",
                        "pet_state": self.state,
                        "summary": f"鸽子连续动作过久，现在有点疲惫",
                    },
                )

        else:
            self.busy_started_at = 0.0

            if self.mood_flags["tired"]:
                self.mood_flags["tired"] = False

                if self.mood == "tired":
                    self.mood = "alert"

        if (
            now - self.last_owner_ping_ts >= BORED_TIMEOUT
            and not self.mood_flags["bored"]
        ):
            self.mood = "bored"

            self.mood_flags["bored"] = True

            self.emit_event(
                "pet_need",
                {
                    "need": "bored",
                    "pet_state": self.state,
                    "summary": "瓒呰繃浜斿垎閽熸病浜虹悊楦藉瓙锛屽畠寮€濮嬫棤鑱婁簡",
                },
            )

        elif self.mood != "tired" and not self.mood_flags["bored"]:
            self.mood = "alert"

    def dispatch_command(
        self, command: dict[str, object], control: dict[str, object]
    ) -> None:

        if control["mode"] == "frame":
            return

        seq = int(command["seq"])

        if seq <= self.last_command_seq:
            return

        self.last_command_seq = seq

        self.cancel_active_program("accepted")

        action = str(command["action"])

        params = dict(command["params"])

        self.handle_command(action, params, control)

    def handle_command(
        self, action: str, params: dict[str, object], control: dict[str, object]
    ) -> None:

        if action == "none":
            self.last_completed_seq = self.last_command_seq

            self.command_state = "idle"

            return

        if action == "show_bubble":
            text = str(params.get("text", "")).strip()

            if text:
                try:
                    duration_ms = float(params.get("duration_ms", 4500) or 4500)

                except (TypeError, ValueError):
                    duration_ms = 4500.0

                self.set_bubble("chat", text, duration=duration_ms / 1000.0)

            self.last_completed_seq = self.last_command_seq

            self.command_state = "idle"

            return

        if action == "walk_by":
            try:
                dx = float(params.get("dx", 0))

            except (TypeError, ValueError):
                dx = 0.0

            target_x = self.clamp_window_x(self.win_x + dx)

            if abs(target_x - self.win_x) < 1:
                self.complete_active_program()

                return

            self.start_program("walk_by", {"target_x": target_x, "speed": 3.2})

            return

        if action == "walk_to":
            try:
                target_x = float(params.get("x", self.win_x))

            except (TypeError, ValueError):
                target_x = self.win_x

            target_x = self.clamp_window_x(target_x)

            if abs(target_x - self.win_x) < 1:
                self.complete_active_program()

                return

            self.start_program("walk_to", {"target_x": target_x, "speed": 3.2})

            return

        if action == "fly_to":
            try:
                target_x = float(params.get("x", self.win_x))

            except (TypeError, ValueError):
                target_x = self.win_x

            try:
                target_y = float(params.get("y", self.win_y))

            except (TypeError, ValueError):
                target_y = self.win_y

            try:
                hold_seconds = float(params.get("hold_seconds", 0.0) or 0.0)

            except (TypeError, ValueError):
                hold_seconds = 0.0

            target_x = self.clamp_window_x(target_x)

            target_y = self.clamp_window_y(target_y)

            self.start_program(
                "fly_to",
                self.create_flight_curve(
                    target_x, target_y, max(0.0, min(12.0, hold_seconds))
                ),
            )

            return

        if action == "fly_shape":
            shape = str(params.get("shape", "")).strip().lower()

            try:
                scale = float(params.get("scale", 1.0) or 1.0)

            except (TypeError, ValueError):
                scale = 1.0

            points = self.create_shape_path(shape, scale)

            if points:
                shape_styles = {
                    "heart": {
                        "trail_color": "#FF8FB8",
                        "trail_radius": 3.8,
                        "trail_decay": 0.03,
                        "duration_scale": 0.42,
                        "arc_bias": 0.34,
                        "sway_scale": 0.22,
                    },
                    "circle": {
                        "trail_color": "#7CC7FF",
                        "trail_radius": 3.4,
                        "trail_decay": 0.026,
                        "duration_scale": 0.34,
                        "arc_bias": 0.24,
                        "sway_scale": 0.12,
                    },
                    "loop": {
                        "trail_color": "#7CC7FF",
                        "trail_radius": 3.4,
                        "trail_decay": 0.026,
                        "duration_scale": 0.34,
                        "arc_bias": 0.24,
                        "sway_scale": 0.12,
                    },
                    "figure8": {
                        "trail_color": "#9AD6FF",
                        "trail_radius": 3.2,
                        "trail_decay": 0.024,
                        "duration_scale": 0.31,
                        "arc_bias": 0.21,
                        "sway_scale": 0.1,
                    },
                    "figure_8": {
                        "trail_color": "#9AD6FF",
                        "trail_radius": 3.2,
                        "trail_decay": 0.024,
                        "duration_scale": 0.31,
                        "arc_bias": 0.21,
                        "sway_scale": 0.1,
                    },
                    "8": {
                        "trail_color": "#9AD6FF",
                        "trail_radius": 3.2,
                        "trail_decay": 0.024,
                        "duration_scale": 0.31,
                        "arc_bias": 0.21,
                        "sway_scale": 0.1,
                    },
                    "infinity": {
                        "trail_color": "#9AD6FF",
                        "trail_radius": 3.2,
                        "trail_decay": 0.024,
                        "duration_scale": 0.31,
                        "arc_bias": 0.21,
                        "sway_scale": 0.1,
                    },
                    "spiral": {
                        "trail_color": "#B4A6FF",
                        "trail_radius": 3.0,
                        "trail_decay": 0.02,
                        "duration_scale": 0.27,
                        "arc_bias": 0.18,
                        "sway_scale": 0.08,
                    },
                    "wave": {
                        "trail_color": "#7FE0E0",
                        "trail_radius": 3.0,
                        "trail_decay": 0.022,
                        "duration_scale": 0.26,
                        "arc_bias": 0.16,
                        "sway_scale": 0.08,
                    },
                    "sine": {
                        "trail_color": "#7FE0E0",
                        "trail_radius": 3.0,
                        "trail_decay": 0.022,
                        "duration_scale": 0.26,
                        "arc_bias": 0.16,
                        "sway_scale": 0.08,
                    },
                }

                style = shape_styles.get(shape, shape_styles["circle"])

                self.start_program(
                    "fly_path",
                    {
                        "points": points,
                        "index": 0,
                        "shape": shape,
                        "scale": scale,
                        **style,
                    },
                )

                return

            self.complete_active_program()

            return

        if action == "write_text":
            text = str(params.get("text", "")).strip()

            if not text:
                self.complete_active_program()

                return

            try:
                scale = float(params.get("scale", 1.0) or 1.0)

            except (TypeError, ValueError):
                scale = 1.0

            points = self.create_text_path(text, scale)

            if points:
                self.start_program(
                    "fly_path",
                    {
                        "points": points,
                        "index": 0,
                        "shape": "text",
                        "text": text[:8],
                        "scale": scale,
                        "trail_color": "#8FD8FF",
                        "trail_radius": 3.2,
                        "trail_decay": 0.022,
                        "duration_scale": 0.24,
                        "arc_bias": 0.16,
                        "sway_scale": 0.08,
                    },
                )

                return

            self.complete_active_program()

            return

        if action == "follow_cursor":
            try:
                duration = float(params.get("duration", 12.0) or 12.0)

            except (TypeError, ValueError):
                duration = 12.0

            try:
                x_offset = float(params.get("x_offset", 26.0) or 26.0)

            except (TypeError, ValueError):
                x_offset = 26.0

            try:
                y_offset = float(params.get("y_offset", -40.0) or -40.0)

            except (TypeError, ValueError):
                y_offset = -96.0

            self.start_program(
                "follow_cursor",
                {
                    "until": time.time() + max(1.0, min(60.0, duration)),
                    "x_offset": max(-160.0, min(160.0, x_offset)),
                    "y_offset": max(-220.0, min(80.0, y_offset)),
                },
            )

            return

        if action == "stop_follow":
            if self.active_program == "follow_cursor":
                self.complete_active_program()

            elif (
                self.active_program == "hover"
                and str(self.program_data.get("source", "")) == "follow_cursor"
            ):
                self.state = "fly"

                self.is_falling = True

                self.flight_velocity_x = 0.0

                self.fall_velocity = 0.8

                self.complete_active_program()

            else:
                self.last_completed_seq = self.last_command_seq

                self.command_state = "idle"

            return

        if action == "say":
            text = str(params.get("text", "")).strip()

            if text:
                self.set_bubble("chat", text, duration=CHAT_BUBBLE_DURATION)

            self.complete_active_program()

            return

        if action == "set_ground":
            if "blocks" in params:
                try:
                    blocks = int(params["blocks"])

                except (TypeError, ValueError):
                    blocks = int(control["ground_lift_blocks"])

            else:
                try:
                    blocks = int(control["ground_lift_blocks"]) + int(
                        params.get("delta_blocks", 0)
                    )

                except (TypeError, ValueError):
                    blocks = int(control["ground_lift_blocks"])

            self.set_control_values(ground_lift_blocks=max(-20, min(20, blocks)))

            self.complete_active_program()

            return

        if action == "set_flight_profile":
            sky_blocks = int(control["flight_sky_blocks"])

            side_blocks = int(control["flight_side_blocks"])

            try:
                if "sky_blocks" in params:
                    sky_blocks = int(params["sky_blocks"])

                else:
                    sky_blocks += int(params.get("sky_delta", 0))

            except (TypeError, ValueError):
                pass

            try:
                if "side_blocks" in params:
                    side_blocks = int(params["side_blocks"])

                else:
                    side_blocks += int(params.get("side_delta", 0))

            except (TypeError, ValueError):
                pass

            self.set_control_values(
                flight_sky_blocks=max(2, min(24, sky_blocks)),
                flight_side_blocks=max(2, min(30, side_blocks)),
            )

            self.complete_active_program()

            return

        if action == "emote_hearts":
            try:
                count = int(params.get("count", 5))

            except (TypeError, ValueError):
                count = 5

            self.heart_queue = min(self.heart_queue + max(1, count), HEART_QUEUE_CAP)

            self.next_heart_emit = min(self.next_heart_emit, time.time())

            self.complete_active_program()

            return

        if action == "set_pose":
            pose = str(params.get("pose", "")).strip().lower()

            try:
                duration = float(params.get("duration", 0.0) or 0.0)

            except (TypeError, ValueError):
                duration = 0.0

            duration = max(0.0, min(30.0, duration))

            if pose == "idle":
                self.state = "idle"

                self.relax_until = time.time() + max(1.5, duration or 4.0)

                self.next_action_time = self.relax_until

                self.complete_active_program()

                return

            if pose == "stand":
                self.state = "stand"

                self.next_action_time = time.time() + max(0.8, duration or 3.0)

                self.complete_active_program()

                return

            if pose == "sit":
                self.state = "sit"

                self.sit_timer = max(int((duration or 4.0) * 20), 24)

                self.complete_active_program()

                return

            if pose == "peck":
                self.state = "peck"

                self.peck_count = max(1, int(duration or 2.0))

                self.peck_timer = random.randint(7, 10)

                self.complete_active_program()

                return

            if pose == "sleep":
                self.state = "sleep"

                self.complete_active_program()

                return

        if action == "force_sleep":
            # Deep sleep: stay asleep until energy AND comfort are both restored

            self.force_sleeping = True

            self.state = "sleep"

            self.cancel_active_program("force_sleep")

            self.set_bubble("chat", "zZz...", duration=4.0)

            self.last_completed_seq = self.last_command_seq

            self.command_state = "idle"

            return

        self.last_completed_seq = self.last_command_seq

        self.cancel_active_program("unknown_action")

    def step_active_program(self) -> None:

        if self.active_program == "walk_by" or self.active_program == "walk_to":
            target_x = float(self.program_data.get("target_x", self.win_x))

            speed = float(self.program_data.get("speed", 3.2))

            delta = target_x - self.win_x

            if abs(delta) <= speed:
                self.win_x = target_x

                self.state = "stand"

                self.update_window_position()

                self.complete_active_program()

                return

            self.direction = 1 if delta > 0 else -1

            self.state = "walk_right" if self.direction > 0 else "walk_left"

            self.win_x = self.clamp_window_x(
                self.win_x
                + (speed * self.direction * self._dt_scale * self.speed_scale)
            )

            self.win_y = self.floor_y

            self.update_window_position()

            return

        if self.active_program == "fly_to":
            target_x = float(self.program_data.get("target_x", self.win_x))

            target_y = float(self.program_data.get("target_y", self.win_y))

            hold_seconds = float(self.program_data.get("hold_seconds", 0.0))

            if self.advance_curve_motion(self.program_data):
                self.win_x = target_x

                self.win_y = target_y

                self.is_falling = False

                self.state = "stand" if int(self.win_y) >= int(self.floor_y) else "fly"

                self.update_window_position()

                if hold_seconds > 0 and self.win_y < self.floor_y:
                    self.start_hover_program(
                        target_x=target_x,
                        target_y=target_y,
                        duration=hold_seconds,
                        buzzing=False,
                        send_tired=False,
                        source="fly_to_hold",
                    )

                    return

                if self.maybe_rest_after_flight(
                    target_x=target_x, target_y=target_y, source="fly_to"
                ):
                    return

                if self.win_y < self.floor_y:
                    self.is_falling = True

                    self.flight_velocity_x = self.clamp_value(
                        self.flight_velocity_x * 0.9, -7.0, 7.0
                    )

                    self.fall_velocity = max(0.4, self.fall_velocity * 0.25)

                self.complete_active_program()

                return

            return

        if self.active_program == "fly_path":
            points = self.program_data.get("points", [])

            if not isinstance(points, list) or not points:
                self.complete_active_program()

                return

            index = int(self.program_data.get("index", 0) or 0)

            if index >= len(points):
                if self.win_y < self.floor_y:
                    self.is_falling = True

                self.complete_active_program()

                return

            segment = self.program_data.get("segment")

            if not isinstance(segment, dict):
                target_x, target_y = points[index]

                arc_bias = float(self.program_data.get("arc_bias", 0.38) or 0.38)

                duration_scale = float(
                    self.program_data.get("duration_scale", 0.4) or 0.4
                )

                sway_scale = float(self.program_data.get("sway_scale", 0.12) or 0.12)

                segment = self.create_flight_curve(
                    float(target_x),
                    float(target_y),
                    0.0,
                    arc_bias=arc_bias,
                    duration_scale=duration_scale,
                    sway_scale=sway_scale,
                )

                trail_color = str(
                    self.program_data.get("trail_color", "") or ""
                ).strip()

                if trail_color:
                    segment["trail_color"] = trail_color

                    segment["trail_radius"] = float(
                        self.program_data.get("trail_radius", 3.0) or 3.0
                    )

                    segment["trail_decay"] = float(
                        self.program_data.get("trail_decay", 0.04) or 0.04
                    )

                self.program_data["segment"] = segment

            if self.advance_curve_motion(segment):
                self.program_data["index"] = index + 1

                self.program_data["segment"] = None

                if index + 1 >= len(points):
                    if self.maybe_rest_after_flight(source="fly_path"):
                        return

                    if self.win_y < self.floor_y:
                        self.is_falling = True

                    self.complete_active_program()

            return

        if self.active_program == "hover":
            target_x = float(self.program_data.get("target_x", self.win_x))

            target_y = float(self.program_data.get("target_y", self.win_y))

            until = float(self.program_data.get("until", 0.0))

            self.win_x = self.clamp_window_x(target_x)

            self.win_y = self.clamp_window_y(target_y)

            self.state = "fly"

            self.is_falling = False

            self.flight_velocity_x = 0.0

            self.fall_velocity = 0.0

            self.update_window_position()

            if time.time() >= until:
                self.state = "fly"

                self.is_falling = True

                self.flight_velocity_x = 0.0

                self.fall_velocity = 0.8

                self.complete_active_program()

            return

        if self.active_program == "follow_cursor":
            until = float(self.program_data.get("until", 0.0))

            if time.time() >= until:
                if self.maybe_rest_after_flight(source="follow_cursor"):
                    return

                self.complete_active_program()

                return

            cursor_x, cursor_y = get_cursor_pos()

            target_x = self.clamp_window_x(
                cursor_x
                - (WINDOW_WIDTH / 2)
                + float(self.program_data.get("x_offset", 26.0))
            )

            target_y = self.clamp_window_y(
                cursor_y
                - (WINDOW_HEIGHT / 2)
                + float(self.program_data.get("y_offset", -96.0))
            )

            is_social_bother = self.program_data.get("source") == "social_bother"
            dt = self._dt_scale
            fs = self.flight_speed_scale  # 飞行速度倍率

            if is_social_bother:
                # 社交骚扰：高速平滑追踪，最终完全贴合鼠标
                delta_x = target_x - self.win_x
                delta_y = target_y - self.win_y
                steer = 0.35 * dt * fs

                self.flight_velocity_x = self.clamp_value(
                    (self.flight_velocity_x * (0.6**dt)) + (delta_x * steer),
                    -9.0 * fs,
                    9.0 * fs,
                )
                self.fall_velocity = self.clamp_value(
                    (self.fall_velocity * (0.6**dt)) + (delta_y * steer),
                    -9.0 * fs,
                    9.0 * fs,
                )

                self.win_x = self.clamp_window_x(
                    self.win_x + self.flight_velocity_x * dt
                )
                self.win_y = self.clamp_window_y(self.win_y + self.fall_velocity * dt)
            else:
                # brain 指令的 follow_cursor：保持平滑追踪手感
                delta_x = target_x - self.win_x
                delta_y = target_y - self.win_y

                self.flight_velocity_x = self.clamp_value(
                    (self.flight_velocity_x * (0.82**dt))
                    + (delta_x * FLIGHT_CURSOR_STEER * dt * fs),
                    -3.4 * fs,
                    3.4 * fs,
                )

                self.fall_velocity = self.clamp_value(
                    (self.fall_velocity * (0.78**dt))
                    + (delta_y * (FLIGHT_CURSOR_STEER * 0.9) * dt * fs),
                    -2.8 * fs,
                    2.8 * fs,
                )

                self.win_x = self.clamp_window_x(
                    self.win_x + self.flight_velocity_x * dt
                )
                self.win_y = self.clamp_window_y(self.win_y + self.fall_velocity * dt)

            self.direction = 1 if self.flight_velocity_x >= 0 else -1

            self.state = "fly"

            self.is_falling = False

            self.update_window_position()

    def choose_flight_direction(self, preferred: int = 0) -> int:

        max_x = self.work_right - self.pet_x - SPRITE_WIDTH

        min_x = self.work_left - self.pet_x

        left_room = self.win_x - min_x

        right_room = max_x - self.win_x

        if left_room < 80:
            return 1

        if right_room < 80:
            return -1

        if preferred in (-1, 1):
            return preferred

        return random.choice([-1, 1])

    def flight_arc(
        self, control: dict[str, object], scale: float = 1.0
    ) -> tuple[float, float]:

        # Use full-screen movement space 鈥?fly across the whole screen.

        screen_w = self.work_right - self.work_left

        available_sky = max(PIXEL_SIZE * 2, (self.floor_y - self.work_top) * 0.92)

        available_side = max(PIXEL_SIZE * 2, screen_w * 0.70)

        sky_px = max(PIXEL_SIZE * 2, available_sky * scale)

        side_px = max(PIXEL_SIZE * 2, available_side * scale)

        launch_speed = -((2 * FALL_GRAVITY * sky_px) ** 0.5)

        launch_speed = max(-TERMINAL_VELOCITY, min(-2.2, launch_speed))

        airtime_ticks = max(6.0, (2 * abs(launch_speed)) / FALL_GRAVITY)

        glide_speed = max(0.6, side_px / airtime_ticks)

        return launch_speed, glide_speed

    def start_random_flight(self, control: dict[str, object]) -> None:

        self.direction = self.choose_flight_direction()

        launch_speed, glide_speed = self.flight_arc(
            control, scale=random.uniform(0.9, 1.15)
        )

        self.state = "fly"

        self.is_falling = True

        self.fall_velocity = launch_speed

        self.flight_velocity_x = self.direction * glide_speed * self.flight_speed_scale

        self.next_action_time = time.time() + random.uniform(0.8, 1.4)

    def start_falling(self, control: dict[str, object]) -> None:

        self.clamp_window()

        if self.win_y < self.floor_y:
            self.start_drag_glide(control)

        else:
            self.win_y = self.floor_y

            self.is_falling = False

            self.flight_velocity_x = 0.0

        self.update_window_position()

    def start_drag_glide(self, control: dict[str, object]) -> None:

        release_vx, release_vy = self.release_throw_velocity()

        preferred = 1 if release_vx > 0 else -1 if release_vx < 0 else self.direction

        self.direction = self.choose_flight_direction(preferred)

        fling_vx = self.clamp_value(release_vx, -FLING_MAX_SPEED, FLING_MAX_SPEED)

        fling_vy = self.clamp_value(release_vy, -FLING_MAX_SPEED, FLING_MAX_SPEED)

        if abs(fling_vx) > 1.0 or fling_vy < -0.8:
            self.drag_velocity_x = fling_vx

            self.drag_velocity_y = fling_vy

            self.state = "fly"

            self.is_falling = False

            self.start_program(
                "fling_glide",
                {
                    "motion": self.create_drag_glide_curve(control),
                    "fling_vx": fling_vx,
                    "fling_vy": fling_vy,
                },
            )

            self.next_action_time = time.time() + random.uniform(0.6, 1.1)

            return

        launch_speed, glide_speed = self.flight_arc(control, scale=0.8)

        self.state = "fly"

        self.is_falling = True

        if random.random() < DRAG_CONTINUE_FLIGHT_CHANCE or fling_vy < -2.0:
            self.fall_velocity = fling_vy if fling_vy < -1.5 else launch_speed * 0.6

            if abs(fling_vx) > 1.2:
                self.flight_velocity_x = fling_vx

            else:
                self.flight_velocity_x = self.direction * max(0.58, glide_speed * 0.9)

        else:
            self.fall_velocity = max(
                0.26, abs(fling_vy) * 0.22, abs(launch_speed) * 0.12
            )

            self.flight_velocity_x = (
                fling_vx
                if abs(fling_vx) > 0.8
                else self.direction * max(1.6, glide_speed * 0.7)
            )

        self.drag_samples = []

        self.next_action_time = time.time() + random.uniform(0.6, 1.1)

    def update_window_physics(self) -> None:

        if self.drag_data["dragging"]:
            return

        # 弹弓拉弦中：锁死鸟的位置，不运行物理
        if self.slingshot_active:
            self.is_falling = False
            self.fall_velocity = 0.0
            self.flight_velocity_x = 0.0
            return

        if self.win_y < self.floor_y or self.is_falling:
            self.is_falling = True

            self.state = "fly"

            # dt_scale：帧率归一化（120fps时≈0.16，20fps时=1.0）
            dt = self._dt_scale
            # 活动倍速：用户控制时间流速
            ts = self.speed_scale * dt
            # 阻力条：越小→几乎无阻力→甩出去永远弹；越大→立刻停
            # inertia 0.3=羽毛 1.0=正常 4.0=石头
            inertia = self.physics_scale
            drag_coeff = 0.03 * (inertia**2.5)
            drag_base = max(0.55, 1.0 - drag_coeff)
            drag = drag_base**dt

            # --- 水平运动 ---

            if abs(self.flight_velocity_x) > 0.1:
                self.flight_velocity_x *= drag

                self.win_x += self.flight_velocity_x * ts

                self.direction = 1 if self.flight_velocity_x >= 0 else -1

                min_x = self.work_left - self.pet_x

                max_x = self.work_right - self.pet_x - SPRITE_WIDTH

                if self.win_x <= min_x:
                    self.win_x = min_x

                    impact_speed = abs(self.flight_velocity_x)

                    self.flight_velocity_x = (
                        abs(self.flight_velocity_x) * WALL_BOUNCE_FACTOR
                    )

                    if impact_speed >= 8.0:
                        self.emit_pain_signal("wall", impact_speed)

                elif self.win_x >= max_x:
                    self.win_x = max_x

                    impact_speed = abs(self.flight_velocity_x)

                    self.flight_velocity_x = (
                        -abs(self.flight_velocity_x) * WALL_BOUNCE_FACTOR
                    )

                    if impact_speed >= 8.0:
                        self.emit_pain_signal("wall", impact_speed)

            else:
                self.flight_velocity_x = 0.0

            # --- 垂直运动：重力恒定（不受惯性条影响）---

            self.fall_velocity += FALL_GRAVITY * ts

            self.fall_velocity = min(self.fall_velocity, TERMINAL_VELOCITY)

            if self.fall_velocity < 0:
                self.fall_velocity *= drag

            self.win_y += self.fall_velocity * ts

            # --- 钀藉湴妫€娴嬶細寮硅烦鎴栧仠涓?---

            if self.win_y >= self.floor_y:
                self.win_y = self.floor_y

                landing_speed = abs(self.fall_velocity)

                if abs(self.fall_velocity) > GROUND_BOUNCE_MIN_VY:
                    # 寮硅烦

                    self.fall_velocity = -abs(self.fall_velocity) * GROUND_BOUNCE_FACTOR

                    self.flight_velocity_x *= 0.85

                    if landing_speed >= 10.0:
                        self.emit_pain_signal("ground", landing_speed)

                else:
                    # 閫熷害澶皬锛屽仠涓?

                    self.fall_velocity = 0.0

                    self.flight_velocity_x = 0.0

                    self.is_falling = False

                    self.state = "stand"

                    self.next_action_time = time.time() + random.uniform(0.4, 0.9)

            # --- 椤堕儴杈圭晫 ---

            top_min = self.work_top - self.pet_y

            if self.win_y < top_min:
                self.win_y = top_min

                self.fall_velocity = abs(self.fall_velocity) * 0.3

            self.update_window_position()

    def maybe_social_bother(self, now: float) -> bool:
        """When social drive is high, randomly follow the cursor for a short burst.

        Returns True if a bother was triggered (caller should skip normal idle)."""

        # Read social drive from brain state

        drives = self.brain_state.get("drives", {})

        if not isinstance(drives, dict):
            return False

        try:
            social = float(drives.get("social", 0.0) or 0.0)

        except (TypeError, ValueError):
            return False

        # Only bother when social > 0.65, not sleeping, not already in a program

        if social < 0.65:
            return False

        if self.state == "sleep":
            return False

        if self.active_program:
            return False

        if self.drag_data["dragging"]:
            return False

        # Cooldown: higher social = shorter cooldown (min 12s, max 45s)

        cooldown = max(12.0, 45.0 - (social - 0.65) / 0.35 * 33.0)

        if now - self.last_social_bother_ts < cooldown:
            return False

        # Probability gate: social 0.65鈫?.0 maps to 15%鈫?5% chance per check

        chance = 0.15 + (social - 0.65) / 0.35 * 0.40

        if random.random() > chance:
            return False

        # Trigger a short follow_cursor burst (3鈥? seconds)

        duration = random.uniform(3.0, 8.0)

        # x_offset/y_offset 让鸟中心精确对准鼠标光标
        # 鸟中心在窗口内 x = base_pet_x + SPRITE_WIDTH/2 = 86 + 48 = 134
        # target_x = cursor_x - WINDOW_WIDTH/2 + x_offset，令 win_x + 134 = cursor_x
        # → x_offset = WINDOW_WIDTH/2 - (base_pet_x + SPRITE_WIDTH/2) = 200 - 134 = 66
        # y 同理，SPRITE_HEIGHT=96，鸟中心 y ≈ pet_y + 48，但 pet_y 动态变化，用近似值
        bother_x_offset = WINDOW_WIDTH / 2 - (self.base_pet_x + SPRITE_WIDTH / 2)
        bother_y_offset = WINDOW_HEIGHT / 2 - (self.pet_y + SPRITE_HEIGHT / 2) + 30

        self.start_program(
            "follow_cursor",
            {
                "until": now + duration,
                "x_offset": bother_x_offset,
                "y_offset": bother_y_offset,
                "source": "social_bother",
            },
        )

        self.last_social_bother_ts = now

        self.social_bother_active = True

        # Emit a chat bubble to signal the bother

        bother_lines = [
            "理我理我！",
            "主人～",
            "咕？",
            "陪我玩嘛～",
            "咕咕咕！",
            "主人你看我！",
        ]

        self.set_bubble("chat", random.choice(bother_lines), duration=3.5)

        return True

    def update_idle_behavior(self, now: float, control: dict[str, object]) -> None:

        if self.state == "sleep":
            return

        if self.relax_until > now and self.state != "fly":
            self.state = "idle"

            return

        if self.state in ("idle", "stand") and now >= self.next_action_time:
            min_x = self.work_left - self.pet_x

            max_x = self.work_right - self.pet_x - SPRITE_WIDTH

            if self.win_x <= min_x + 12:
                self.state = "walk_right"

                self.direction = 1

                self.walk_timer = random.randint(18, 34)

            elif self.win_x >= max_x - 12:
                self.state = "walk_left"

                self.direction = -1

                self.walk_timer = random.randint(18, 34)

            else:
                action = random.choices(
                    ["walk", "walk", "walk", "peck", "sit", "idle", "stand", "fly"],
                    weights=[3, 3, 2, 2, 1, 1, 2, 1],
                    k=1,
                )[0]

                if action == "walk":
                    self.state = random.choice(["walk_left", "walk_right"])

                    self.direction = -1 if self.state == "walk_left" else 1

                    self.walk_timer = random.randint(16, 36)

                elif action == "peck":
                    self.state = "peck"

                    self.peck_timer = random.randint(8, 12)

                    self.peck_count = random.randint(2, 4)

                elif action == "sit":
                    self.state = "sit"

                    self.sit_timer = random.randint(28, 52)

                elif action == "fly":
                    self.start_random_flight(control)

                elif action == "stand":
                    self.state = "stand"

                    self.next_action_time = now + random.uniform(0.8, 1.5)

                else:
                    self.state = "idle"

                    self.next_action_time = now + random.uniform(0.6, 1.2)

        if self.state in ("walk_left", "walk_right"):
            self.win_x = self.clamp_window_x(
                self.win_x + (self.direction * 2.4 * self._dt_scale * self.speed_scale)
            )

            self.win_y = self.floor_y

            self.update_window_position()

            self.walk_timer -= 1

            at_edge = int(self.win_x) in (
                int(self.work_left - self.pet_x),
                int(self.work_right - self.pet_x - SPRITE_WIDTH),
            )

            if self.walk_timer <= 0 or at_edge:
                self.state = random.choice(["stand", "idle"])

                self.next_action_time = now + random.uniform(0.2, 0.8)

        elif self.state == "peck":
            self.peck_timer -= 1

            if self.peck_timer <= 0:
                self.peck_count -= 1

                if self.peck_count <= 0:
                    self.state = random.choice(["stand", "idle"])

                    self.next_action_time = now + random.uniform(0.4, 1.0)

                else:
                    self.peck_timer = random.randint(7, 10)

        elif self.state == "sit":
            self.sit_timer -= 1

            if self.sit_timer <= 0:
                self.state = random.choice(["stand", "idle"])

                self.next_action_time = now + random.uniform(0.4, 1.0)

    def emit_queued_heart(self, now: float) -> None:

        if self.heart_queue <= 0 or now < self.next_heart_emit:
            return

        self.hearts.append(HeartParticle(self.pet_x + 48, self.pet_y + 12))

        self.heart_queue -= 1

        self.next_heart_emit = now + HEART_EMIT_INTERVAL

    def draw_pixel_art(self, art_name: str, x: float, y: float) -> None:

        art = FRAMES.get(art_name, FRAMES["idle1"])

        self.canvas.delete("pet")

        for row_i, row in enumerate(art):
            for col_i, pixel in enumerate(row):
                px_color = PIXEL_COLORS.get(pixel)

                if not px_color:
                    continue

                sx = x + col_i * PIXEL_SIZE

                sy = y + row_i * PIXEL_SIZE

                self.canvas.create_rectangle(
                    sx,
                    sy,
                    sx + PIXEL_SIZE,
                    sy + PIXEL_SIZE,
                    fill=px_color,
                    outline="",
                    tags="pet",
                )

    def draw_hearts(self) -> None:

        self.canvas.delete("heart")

        for heart in self.hearts:
            if heart.is_alive():
                self.canvas.create_text(
                    heart.x,
                    heart.y,
                    text="♥",
                    fill="#FF4D6D",
                    font=("Arial", heart.size),
                    tags="heart",
                )

    def draw_sleep_particles(self) -> None:

        self.canvas.delete("sleep_text")

        for particle in self.sleep_texts:
            if particle.is_alive():
                self.canvas.create_text(
                    particle.x,
                    particle.y,
                    text=particle.text,
                    fill="#000000",
                    font=("Terminal", max(10, particle.size)),
                    tags="sleep_text",
                )

    def draw_flight_trails(self) -> None:

        self.canvas.delete("flight_trail")

        for particle in self.flight_trails:
            if not particle.is_alive():
                continue

            canvas_x = particle.screen_x - self.win_x

            canvas_y = particle.screen_y - self.win_y

            radius = max(1.1, particle.radius * particle.life)

            if (
                canvas_x < -12
                or canvas_x > WINDOW_WIDTH + 12
                or canvas_y < -12
                or canvas_y > WINDOW_HEIGHT + 12
            ):
                continue

            self.canvas.create_oval(
                canvas_x - radius,
                canvas_y - radius,
                canvas_x + radius,
                canvas_y + radius,
                fill=particle.color,
                outline="",
                tags="flight_trail",
            )

    def draw_slingshot_string(self) -> None:
        """绘制弹弓弦线：拉弦时画从锚点到鼠标的淡蓝色线；收回时做动画。"""
        self.canvas.delete("slingshot_string")

        # --- 拉弦中：画实线 ---
        if self.slingshot_active and (
            abs(self.slingshot_pull_x) > 2 or abs(self.slingshot_pull_y) > 2
        ):
            # 锚点转窗口坐标
            ax = self.slingshot_anchor_x - self.win_x
            ay = self.slingshot_anchor_y - self.win_y
            # 鼠标端（锚点 + 拉伸向量）
            ex = ax + self.slingshot_pull_x
            ey = ay + self.slingshot_pull_y

            # 拉伸比例（0~1）控制透明度模拟：越拉越粗
            dist = math.sqrt(self.slingshot_pull_x**2 + self.slingshot_pull_y**2)
            ratio = min(dist / SLINGSHOT_MAX_PULL, 1.0)
            width = max(1, int(SLINGSHOT_STRING_WIDTH + ratio * 2))

            self.canvas.create_line(
                ax,
                ay,
                ex,
                ey,
                fill=SLINGSHOT_STRING_COLOR,
                width=width,
                smooth=True,
                tags="slingshot_string",
            )
            return

        # --- 弦收回动画 ---
        if self.slingshot_recoil > 0:
            progress = self.slingshot_recoil / SLINGSHOT_RECOIL_STEPS  # 1.0→0.0
            ax = self.slingshot_anchor_x - self.win_x
            ay = self.slingshot_anchor_y - self.win_y
            # 末端从拉伸位置线性回到锚点
            ex = ax + self.slingshot_pull_x * progress
            ey = ay + self.slingshot_pull_y * progress

            self.canvas.create_line(
                ax,
                ay,
                ex,
                ey,
                fill=SLINGSHOT_STRING_COLOR,
                width=SLINGSHOT_STRING_WIDTH,
                smooth=True,
                tags="slingshot_string",
            )
            self.slingshot_recoil -= 1

    def draw_bubbles(self) -> None:

        self.canvas.delete("bubble_group")

        self.bubbles = {
            channel: bubble
            for channel, bubble in self.bubbles.items()
            if bubble.is_alive()
        }

        if not self.bubbles:
            return

        pet_center_x = self.pet_x + (SPRITE_WIDTH / 2)

        pet_top_y = self.pet_y

        max_text_width = min(WINDOW_WIDTH - 44, CHAT_BUBBLE_WRAP_WIDTH)

        def draw_box(
            text: str,
            x: float,
            y: float,
            tail_points: list[float] | None,
            fill: str,
            outline: str,
            wrap_width: float | None = None,
            font_override=None,
        ) -> None:

            text_wrap_width = max_text_width if wrap_width is None else wrap_width
            used_font = font_override if font_override is not None else self.bubble_font

            temp_text = self.canvas.create_text(
                0,
                0,
                text=text,
                fill="#333333",
                font=used_font,
                width=text_wrap_width,
                anchor="nw",
                tags="bubble_group",
            )

            bbox = self.canvas.bbox(temp_text)

            if bbox is None:
                self.canvas.delete(temp_text)

                return

            text_width = (bbox[2] - bbox[0]) + 16

            bubble_h = (bbox[3] - bbox[1]) + 14

            bx = max(8, min(x, WINDOW_WIDTH - text_width - 8))

            by = max(6, min(y, WINDOW_HEIGHT - bubble_h - 8))

            self.canvas.coords(temp_text, bx + 8, by + 7)

            self.canvas.create_rectangle(
                bx,
                by,
                bx + text_width,
                by + bubble_h,
                fill=fill,
                outline=outline,
                width=2,
                tags="bubble_group",
            )

            if tail_points:
                self.canvas.create_polygon(
                    *tail_points,
                    fill=fill,
                    outline=outline,
                    width=2,
                    tags="bubble_group",
                )

            self.canvas.tag_raise(temp_text)

        chat_bubble = self.bubbles.get("chat")

        if chat_bubble:
            temp_text = self.canvas.create_text(
                0,
                0,
                text=chat_bubble.text,
                font=self.bubble_font,
                width=CHAT_BUBBLE_WRAP_WIDTH,
                anchor="nw",
            )

            bbox = self.canvas.bbox(temp_text)

            self.canvas.delete(temp_text)

            if bbox is not None:
                text_width = (bbox[2] - bbox[0]) + 16

                bubble_h = (bbox[3] - bbox[1]) + 14

                bx = pet_center_x - (text_width / 2)

                by = max(26, pet_top_y - bubble_h - 10)

                tail = [
                    pet_center_x - 8,
                    by + bubble_h,
                    pet_center_x,
                    by + bubble_h + 10,
                    pet_center_x + 8,
                    by + bubble_h,
                ]

                draw_box(
                    chat_bubble.text,
                    bx,
                    by,
                    tail,
                    "#FFFFFF",
                    "#838383",
                    wrap_width=CHAT_BUBBLE_WRAP_WIDTH,
                )

        pet_bubble = self.bubbles.get("pet")

        if pet_bubble:
            temp_text = self.canvas.create_text(
                0,
                0,
                text=pet_bubble.text,
                font=self.kaomoji_font,
                width=80,
                anchor="nw",
            )

            bbox = self.canvas.bbox(temp_text)

            self.canvas.delete(temp_text)

            if bbox is not None:
                bx = PET_BUBBLE_LEFT

                bubble_h = (bbox[3] - bbox[1]) + 14

                by = max(PET_BUBBLE_TOP_MIN, pet_top_y + PET_BUBBLE_TOP_OFFSET)

                by = min(by, WINDOW_HEIGHT - bubble_h - PET_BUBBLE_BOTTOM_MARGIN)

                draw_box(
                    pet_bubble.text,
                    bx,
                    by,
                    None,
                    "#FFF6E6",
                    "#C6AA7A",
                    wrap_width=80,
                    font_override=self.kaomoji_font,
                )

    def frame_top_y(self, frame_name: str) -> float:

        ground_row = FRAME_GROUND_ROWS.get(frame_name, 15)

        lift_px = FLY_LIFT_PX if frame_name.startswith("fly_") else 0

        if frame_name.startswith("fly_"):
            lift_px += int(self.flight_bob_offset)

        return self.ground_y - ((ground_row + 1) * PIXEL_SIZE) - lift_px

    def frame_name(self) -> str:

        if self.command_pose_frame:
            return self.command_pose_frame

        if self.state == "wake":
            return "stand1" if (self.anim_frame // 3) % 2 == 0 else "stand2"

        if self.state == "sleep":
            return "sleep"

        if self.state == "idle":
            return "idle1" if (self.anim_frame // 10) % 2 == 0 else "idle2"

        if self.state == "stand":
            return "stand1" if (self.anim_frame // 10) % 2 == 0 else "stand2"

        if self.state == "sit":
            return "sit"

        if self.state == "peck":
            return "peck"

        if self.state == "walk_right":
            return "walk_right1" if (self.anim_frame // 6) % 2 == 0 else "walk_right2"

        if self.state == "walk_left":
            return "walk_left1" if (self.anim_frame // 6) % 2 == 0 else "walk_left2"

        if self.state == "fly":
            frame_divisor = 1 if self.hover_is_buzzing() else 2

            if self.direction >= 0:
                return (
                    "fly_right1"
                    if (self.anim_frame // frame_divisor) % 2 == 0
                    else "fly_right2"
                )

            return (
                "fly_left1"
                if (self.anim_frame // frame_divisor) % 2 == 0
                else "fly_left2"
            )

        return "stand1"

    def tick(self) -> None:

        now = time.time()

        self.sync_brain_state(now)

        self.tick_bubble_queue(now)

        # 读取控制参数
        control = self.current_control()
        self.speed_scale = float(control.get("speed_scale", 1.0))
        self.physics_scale = float(control.get("physics_scale", 1.0))
        self.flight_speed_scale = float(control.get("flight_speed_scale", 1.0))
        self._anim_speed = float(control.get("anim_speed", 1.0))
        fps_target = float(control.get("fps_target", 62.0))
        self._tick_ms = max(8, int(1000.0 / fps_target))

        # delta-time 归一化：让物理速度与帧率解耦
        # 基准是 50ms/tick（20fps），所有物理常量在此基准下调校
        BASE_DT = 0.050
        if self._last_tick_ts > 0:
            real_dt = min(0.2, max(0.005, now - self._last_tick_ts))
            self._dt_scale = real_dt / BASE_DT
        else:
            self._dt_scale = self._tick_ms / 1000.0 / BASE_DT
        self._last_tick_ts = now

        # 动画帧计数器：受 dt_scale（帧率补偿）和 anim_speed（用户调节）影响
        self.anim_frame += self._dt_scale * self._anim_speed

        # Force-sleep tick: stay asleep until drives are restored
        if self.force_sleeping:
            self.state = "sleep"

            drives = self.brain_state.get("drives", {})

            energy = (
                float(drives.get("energy", 0.0) or 0.0)
                if isinstance(drives, dict)
                else 0.0
            )

            comfort = (
                float(drives.get("comfort", 0.0) or 0.0)
                if isinstance(drives, dict)
                else 0.0
            )

            if energy >= 0.85 and comfort >= 0.80:
                self.force_sleeping = False

                # Directly top up all drives in state.json so brain sees full values

                try:
                    raw_state = read_json(STATE_FILE, {})

                    raw_state["drives"] = {
                        "energy": 0.95,
                        "social": 0.90,
                        "curiosity": 0.88,
                        "comfort": 0.92,
                    }

                    write_json(STATE_FILE, raw_state)

                except Exception:
                    pass

                # Wake up 鈥?no cooldown, just full drives means lots of activity

                self.state = "stand"

                self.manual_awake_until = now + MANUAL_AWAKE_DURATION

                self.next_action_time = now + random.uniform(0.3, 0.8)

                self.set_bubble(
                    "chat",
                    random.choice(
                        [
                            "好多了！精神满满～",
                            "睡醒啦！今天要好好玩！",
                            "咕咕！充好电了！",
                        ]
                    ),
                    duration=4.0,
                )

        # control 已在 tick 开头读取，此处直接复用
        command = self.current_command()

        self.apply_bounds_control(control)

        self.apply_floor_control(control)

        if control["mode"] == "frame":
            self.cancel_active_program("preview")

            self.apply_frame_preview(str(control["frame"]))

        else:
            self.dispatch_command(command, control)

        if self.active_program in {
            "fly_to",
            "fly_path",
            "hover",
            "follow_cursor",
        }:
            self.step_active_program()

        else:
            self.update_window_physics()

            if self.active_program:
                self.step_active_program()

            elif self.should_sleep(control):
                self.state = "sleep"

                self.next_action_time = now + 1.0

            else:
                if self.update_first_launch_flow(now):
                    pass

                else:
                    if self.state == "wake":
                        if now < self.manual_awake_until - max(
                            0.0, MANUAL_AWAKE_DURATION - WAKE_SHAKE_DURATION
                        ):
                            pass

                        else:
                            self.state = "stand"

                            self.next_action_time = now + random.uniform(0.3, 0.8)

                    if self.state == "sleep":
                        self.state = "stand"

                        self.next_action_time = now + random.uniform(0.3, 0.8)

                    if self.state != "wake":
                        # Social bother: when social drive is high, randomly

                        # follow cursor for a short burst instead of idle behavior

                        if not self.maybe_social_bother(now):
                            self.update_idle_behavior(now, control)

        self.update_airborne_state(now)

        self.refresh_pet_needs(now)

        self.emit_queued_heart(now)

        if self.state == "sleep" and now >= self.next_sleep_particle_at:
            self.emit_sleep_particles(count=random.choice([1, 2]))

            self.next_sleep_particle_at = now + random.uniform(2.6, 5.2)

        elif self.state != "sleep":
            self.next_sleep_particle_at = now + random.uniform(2.6, 5.2)

        self.update_flight_bob(now)

        for particle in self.flight_trails:
            particle.update()

        self.flight_trails = [
            particle for particle in self.flight_trails if particle.is_alive()
        ]

        self.pet_x = self.base_pet_x

        frame_to_draw = (
            str(control["frame"]) if control["mode"] == "frame" else self.frame_name()
        )

        self.pet_y = self.frame_top_y(frame_to_draw)

        self.draw_flight_trails()

        self.draw_pixel_art(frame_to_draw, self.pet_x, self.pet_y)

        self.position_dialog()

        for heart in self.hearts:
            heart.update()

        self.hearts = [heart for heart in self.hearts if heart.is_alive()]

        self.draw_hearts()

        for particle in self.sleep_texts:
            particle.update()

        self.sleep_texts = [
            particle for particle in self.sleep_texts if particle.is_alive()
        ]

        self.draw_sleep_particles()

        self.draw_slingshot_string()

        if self.bubbles:
            self.draw_bubbles()

        else:
            self.canvas.delete("bubble_group")

        self.canvas.delete("ground_guide")

        self.write_runtime_status(
            "preview" if control["mode"] == "frame" else self.command_state
        )

        if self.command_state == "completed":
            self.command_state = "idle"

        # 帧率由 fps_target 控制（UI 可调 10~120fps）
        self.root.after(self._tick_ms, self.tick)

    def on_click(self, event: tk.Event) -> None:

        if self.state == "sleep":
            self.handle_sleep_interaction()

            return

        self.record_owner_attention()

        hovering = self.is_hovering_flight()

        if hovering:
            self.extend_hover()

        else:
            self.cancel_active_program("dragged")

        self.drag_data["x"] = event.x

        self.drag_data["y"] = event.y

        self.drag_data["dragging"] = True

        self.drag_dx = 0.0

        self.drag_dy = 0.0

        self.drag_velocity_x = 0.0

        self.drag_velocity_y = 0.0

        self.last_drag_sample_ts = time.time()

        self.last_drag_pointer_x = int(getattr(event, "x_root", self.win_x))

        self.last_drag_pointer_y = int(getattr(event, "y_root", self.win_y))

        self.drag_samples = []

        self.drag_moved = False

        self.is_falling = False

        self.fall_velocity = 0.0

        self.flight_velocity_x = 0.0

        if self.pending_single_click_job:
            self.root.after_cancel(self.pending_single_click_job)

        self.pending_single_click_job = self.root.after(
            240, self.commit_single_click_signal
        )

    def commit_single_click_signal(self) -> None:

        self.pending_single_click_job = None

        if self.drag_data["dragging"] or self.drag_moved:
            return

        now = time.time()

        if now - self.last_touch_signal_ts < TOUCH_SIGNAL_COOLDOWN:
            return

        self.last_touch_signal_ts = now

        self.emit_event(
            "owner_touch",
            {
                "pet_state": self.state,
                "mood": self.mood,
                "summary": "The owner rubbed the pet gently with a single click.",
            },
        )

        if self.is_hovering_flight():
            self.extend_hover()

        else:
            self.start_high_jump()

    def on_drag(self, event: tk.Event) -> None:

        if not self.drag_data["dragging"]:
            return

        now = time.time()

        root_x = int(getattr(event, "x_root", self.win_x))

        root_y = int(getattr(event, "y_root", self.win_y))

        dt = (
            max(0.008, now - self.last_drag_sample_ts)
            if self.last_drag_sample_ts
            else 0.016
        )

        move_x = root_x - self.last_drag_pointer_x

        move_y = root_y - self.last_drag_pointer_y

        self.drag_dx = move_x

        self.drag_dy = move_y

        # 閫熷害鍗曚綅锛氬儚绱?tick锛?0ms锛夈€傚皢鐪熷疄鏃堕棿宸綊涓€鍒?tick 灏哄害銆?

        tick_scale = (TICK_MS / 1000.0) / dt

        raw_vx = self.clamp_value(
            move_x * tick_scale, -FLING_MAX_SPEED, FLING_MAX_SPEED
        )

        raw_vy = self.clamp_value(
            move_y * tick_scale, -FLING_MAX_SPEED, FLING_MAX_SPEED
        )

        self.drag_velocity_x = self.clamp_value(
            (self.drag_velocity_x * (1.0 - DRAG_VELOCITY_BLEND))
            + (raw_vx * DRAG_VELOCITY_BLEND),
            -FLING_MAX_SPEED,
            FLING_MAX_SPEED,
        )

        self.drag_velocity_y = self.clamp_value(
            (self.drag_velocity_y * (1.0 - DRAG_VELOCITY_BLEND))
            + (raw_vy * DRAG_VELOCITY_BLEND),
            -FLING_MAX_SPEED,
            FLING_MAX_SPEED,
        )

        self.record_drag_sample(now, raw_vx, raw_vy)

        self.last_drag_sample_ts = now

        self.last_drag_pointer_x = root_x

        self.last_drag_pointer_y = root_y

        if abs(move_x) > 1 or abs(move_y) > 1:
            self.drag_moved = True

            if self.pending_single_click_job:
                self.root.after_cancel(self.pending_single_click_job)

                self.pending_single_click_job = None

            if self.is_hovering_flight():
                self.cancel_active_program("dragged")

        if move_x > 0:
            self.direction = 1

        elif move_x < 0:
            self.direction = -1

        self.win_x += move_x

        self.win_y += move_y

        self.clamp_window()

        if self.win_y < self.floor_y:
            self.state = "fly"

            self.is_falling = True

            self.flight_velocity_x = 0.0

        self.update_window_position()

    def on_release(self, _event: tk.Event) -> None:

        self.drag_data["dragging"] = False

        # 睡眠状态：on_click 已经处理了唤醒，release 直接忽略，避免飞出去
        if self.state == "sleep":
            self.drag_velocity_x = 0.0
            self.drag_velocity_y = 0.0
            self.drag_samples = []
            return

        if self.is_hovering_flight() and not self.drag_moved:
            self.drag_velocity_x = 0.0

            self.drag_velocity_y = 0.0

            self.extend_hover()

            return

        if not self.drag_moved:
            self.drag_velocity_x = 0.0

            self.drag_velocity_y = 0.0

            self.drag_samples = []

            return

        # --- 鎶涘嚭锛氱洿鎺ョ敤閲囨牱閫熷害鍒濆鍖栫墰椤跨墿鐞?---

        release_vx, release_vy = self.release_throw_velocity()

        self.clamp_window()

        if self.win_y >= self.floor_y and release_vy >= 0:
            # 鍦ㄥ湴闈笂涓旀病鏈夊悜涓婄敥鐨勮秼鍔匡紝鐩存帴钀藉湴

            self.win_y = self.floor_y

            self.is_falling = False

            self.fall_velocity = 0.0

            self.flight_velocity_x = 0.0

            self.state = "stand"

            self.next_action_time = time.time() + random.uniform(0.3, 0.8)

        else:
            # 空中释放或向上甩出：初速度跟鼠标矢量，低阻力时额外放大
            # 阻力0.3时系数≈3.3，阻力1.0时=1.0，阻力4.0时≈0.25
            launch_scale = 1.0 / max(0.3, self.physics_scale)
            self.flight_velocity_x = release_vx * launch_scale
            self.fall_velocity = release_vy * launch_scale

            self.fall_velocity = self.clamp_value(
                release_vy, -FLING_MAX_SPEED, FLING_MAX_SPEED
            )

            self.is_falling = True

            self.state = "fly"

            if self.flight_velocity_x > 0:
                self.direction = 1

            elif self.flight_velocity_x < 0:
                self.direction = -1

        self.drag_samples = []

        self.update_window_position()

    # ------------------------------------------------------------------ #
    #  弹弓特效：右键按住拉弦，松手弹射                                      #
    # ------------------------------------------------------------------ #

    def on_slingshot_press(self, event: tk.Event) -> None:
        """右键按下：开始拉弦，记录鸟的中心作为锚点。"""
        if self.state == "sleep":
            self.handle_sleep_interaction()
            return

        # 取消旧的右键单击逻辑的 pending job（兼容旧绑定残留）
        if self.pending_right_click_job:
            self.root.after_cancel(self.pending_right_click_job)
            self.pending_right_click_job = None

        # 停止弦收回动画（如果还在跑）
        self.slingshot_recoil = 0

        # 记录锚点（鸟中心的屏幕坐标）
        self.slingshot_anchor_x = float(self.win_x + self.pet_x + SPRITE_WIDTH / 2)
        self.slingshot_anchor_y = float(self.win_y + self.pet_y + SPRITE_WIDTH / 2)

        # 记录鼠标初始位置
        self.slingshot_mouse_x = float(
            getattr(event, "x_root", self.slingshot_anchor_x)
        )
        self.slingshot_mouse_y = float(
            getattr(event, "y_root", self.slingshot_anchor_y)
        )

        self.slingshot_pull_x = 0.0
        self.slingshot_pull_y = 0.0
        self.slingshot_active = True

        # 取消自动行为，固定宠物
        self.cancel_active_program("slingshot")
        self.record_owner_attention()

        # 开始惊慌扑腾
        self._slingshot_panic_tick()

    def _slingshot_panic_tick(self) -> None:
        """每隔 SLINGSHOT_PANIC_INTERVAL ms 切换一次飞行/站立，模拟惊慌扑腾。"""
        if not self.slingshot_active:
            return
        # 在 fly 和 sit 之间快速切换，制造扑腾感
        self.state = "fly" if self.state != "fly" else "sit"
        # 随机小幅方向摇摆
        self.direction = 1 if random.random() > 0.5 else -1
        self.slingshot_panic_job = self.root.after(
            SLINGSHOT_PANIC_INTERVAL, self._slingshot_panic_tick
        )

    def on_slingshot_drag(self, event: tk.Event) -> None:
        """右键拖动：更新鼠标位置，计算拉伸向量。"""
        if not self.slingshot_active:
            return

        mx = float(getattr(event, "x_root", self.slingshot_mouse_x))
        my = float(getattr(event, "y_root", self.slingshot_mouse_y))

        self.slingshot_mouse_x = mx
        self.slingshot_mouse_y = my

        dx = mx - self.slingshot_anchor_x
        dy = my - self.slingshot_anchor_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > SLINGSHOT_MAX_PULL:
            scale = SLINGSHOT_MAX_PULL / dist
            dx *= scale
            dy *= scale

        self.slingshot_pull_x = dx
        self.slingshot_pull_y = dy

    def on_slingshot_release(self, event: tk.Event) -> None:
        """右键松开：弹射鸟，播放弦收回动画，发 brain 事件。"""
        if not self.slingshot_active:
            # 没有真正拉弦（只是右键单击），走原来的抚摸逻辑
            self._commit_pet_action()
            return

        self.slingshot_active = False

        # 停止惊慌
        if self.slingshot_panic_job:
            self.root.after_cancel(self.slingshot_panic_job)
            self.slingshot_panic_job = None

        pull_x = self.slingshot_pull_x
        pull_y = self.slingshot_pull_y
        dist = math.sqrt(pull_x * pull_x + pull_y * pull_y)

        # 弦收回动画起点 = 当前鼠标位置（转为窗口坐标）
        self.slingshot_recoil_x = self.slingshot_anchor_x
        self.slingshot_recoil_y = self.slingshot_anchor_y
        self.slingshot_recoil = SLINGSHOT_RECOIL_STEPS

        if dist < 5:
            # 几乎没拉，当普通右键单击
            self._commit_pet_action()
            return

        # 发射速度 = 拉伸向量的反方向，幅度由拉伸距离决定
        speed = min(dist * SLINGSHOT_LAUNCH_SCALE, SLINGSHOT_MAX_LAUNCH_SPEED)
        norm = dist
        launch_vx = -(pull_x / norm) * speed
        launch_vy = -(pull_y / norm) * speed

        # 赋予物理速度，低阻力时更猛（轻的东西更容易被弹飞）
        launch_scale = 1.0 / max(0.3, self.physics_scale)
        self.flight_velocity_x = launch_vx * launch_scale
        self.fall_velocity = launch_vy * launch_scale
        self.is_falling = True
        self.state = "fly"
        self.direction = 1 if launch_vx >= 0 else -1

        # 立即显示恐惧气泡
        fear_texts = [
            "啊啊啊啊啊！！",
            "救命！！！",
            "我在飞！！我不想飞！！",
            "呜呜呜好快！！",
            "AAAAAAA！！",
        ]
        fear_kaomoji = ["(°△°|||)", "Σ(°△°|||)", "(ノω＜｡)", "(；′⌒`)", "（>д<）"]
        self.set_bubble("chat", random.choice(fear_texts), duration=3.5)
        self.set_bubble("pet", random.choice(fear_kaomoji), duration=4.0)

        # 通知 brain（高优先级，直接发，不走 low_priority 过滤）
        speed_px_per_s = round(speed / (TICK_MS / 1000.0), 1)
        self.emit_event(
            "slingshot_launched",
            {
                "pet_state": "fly",
                "mood": "terrified",
                "launch_vx": round(launch_vx, 2),
                "launch_vy": round(launch_vy, 2),
                "speed_px_per_s": speed_px_per_s,
                "pull_distance": round(dist, 1),
                "summary": (
                    f"The owner used a slingshot and launched the pet at "
                    f"{speed_px_per_s} px/s. The pet is terrified and flying uncontrollably."
                ),
            },
        )

        self.cancel_active_program("slingshot_launched")

    def _commit_pet_action(self) -> None:
        """普通右键单击的抚摸逻辑（从 on_right_click 提取）。"""
        self.record_owner_attention()
        hovering = self.is_hovering_flight()
        if hovering:
            self.extend_hover()
        now = time.time()
        if now - self.last_pet_signal_ts >= PET_SIGNAL_COOLDOWN:
            self.last_pet_signal_ts = now
            self.emit_event(
                "owner_pet",
                {
                    "pet_state": self.state,
                    "mood": self.mood,
                    "summary": "The owner petted the pet with a right click.",
                },
            )
        self.heart_queue = min(self.heart_queue + 5, HEART_QUEUE_CAP)
        self.next_heart_emit = min(self.next_heart_emit, time.time())
        if not hovering:
            self.state = "sit"
            self.sit_timer = max(self.sit_timer, 18)

    def on_right_click(self, _event: tk.Event) -> None:

        if self.state == "sleep":
            self.handle_sleep_interaction()

            return

        now = time.time()

        if now - self.last_right_click_ts > RIGHT_CLICK_MULTI_WINDOW:
            self.right_click_count = 0

        self.last_right_click_ts = now

        self.right_click_count += 1

        if self.pending_right_click_job:
            self.root.after_cancel(self.pending_right_click_job)

            self.pending_right_click_job = None

        if self.right_click_count >= 3:
            self.right_click_count = 0

            self.open_history_panel()

            return

        self.pending_right_click_job = self.root.after(
            int(RIGHT_CLICK_MULTI_WINDOW * 1000), self.commit_right_click_action
        )

    def commit_right_click_action(self) -> None:

        self.pending_right_click_job = None

        if self.right_click_count <= 0:
            return

        self.right_click_count = 0

        self.record_owner_attention()

        hovering = self.is_hovering_flight()

        if hovering:
            self.extend_hover()

        now = time.time()

        if now - self.last_pet_signal_ts >= PET_SIGNAL_COOLDOWN:
            self.last_pet_signal_ts = now

            self.emit_event(
                "owner_pet",
                {
                    "pet_state": self.state,
                    "mood": self.mood,
                    "summary": "The owner petted the pet with a right click.",
                },
            )

        self.heart_queue = min(self.heart_queue + 5, HEART_QUEUE_CAP)

        self.next_heart_emit = min(self.next_heart_emit, time.time())

        if not hovering:
            self.state = "sit"

            self.sit_timer = max(self.sit_timer, 18)

    def on_double_click(self, _event: tk.Event) -> None:

        if self.state == "sleep":
            self.handle_sleep_interaction()

            return

        self.record_owner_attention()

        if self.is_hovering_flight():
            self.extend_hover()

        if self.pending_single_click_job:
            self.root.after_cancel(self.pending_single_click_job)

            self.pending_single_click_job = None

        if self.state != "fly":
            self.state = "idle"

            self.relax_until = time.time() + 2.6

            self.next_action_time = self.relax_until

        self.open_dialog()

    def run(self) -> None:

        self.root.mainloop()


if __name__ == "__main__":
    instance = ensure_single_instance("main")

    if instance:
        import threading

        def _run_brain() -> None:

            try:
                from brain.agent import run

                run()

            except Exception as exc:
                print(f"[brain] fatal: {exc}")

        threading.Thread(target=_run_brain, daemon=True, name="brain").start()

        DesktopPet().run()
