"""咕咕桌宠 — 控制面板"""

from __future__ import annotations

import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import loader as cfg
from runtime.models import RuntimeEventLog
from runtime.state_store import (
    ensure_runtime_files,
    read_event_log,
    read_state,
    read_status,
    write_event_log,
)
from service_runtime import read_json, runtime_file, write_json
from bridge.protocol import BodyEventName
from ui.settings_panel import SettingsPanel
from ui.widgets import (
    ACCENT_GREEN,
    ACCENT_SAND,
    BG,
    BG_CARD,
    BORDER,
    FG_DARK,
    FG_LIGHT,
    FG_MID,
    FONT_BOLD,
    FONT_LABEL,
    FONT_MONO,
    FONT_MONO_SM,
    FONT_SMALL,
    FONT_TITLE,
    btn_primary,
    btn_secondary,
    card,
    draw_drive_bar,
    drive_bar,
    label,
    scrolled_frame,
    section_title,
    small_label,
)

REFRESH_MS = 1200
# Windows process-creation flags — not used on macOS but kept as 0 so any
# accidental reference doesn't break.
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
DETACHED_PROCESS = 0x00000008 if sys.platform == "win32" else 0
PROCESS_FLAGS = CREATE_NO_WINDOW | DETACHED_PROCESS

_DRIVE_LABELS = {
    "energy": "精力",
    "social": "社交",
    "curiosity": "好奇",
    "comfort": "舒适",
}
_DRIVE_COLOURS = {
    "energy": "#4DA3FF",
    "social": "#FF8A65",
    "curiosity": "#9C6BFF",
    "comfort": "#66BB6A",
}

HISTORY_FILE = runtime_file("pet_conversation_history.json")
DEFAULT_HISTORY = {
    "items": [],
}

CONTROL_FILE = runtime_file("pet_manual_control.json")
DEFAULT_CONTROL = {
    "mode": "auto",
    "frame": "auto",
    "use_full_screen_bounds": True,
    "ground_lift_blocks": 0,
    "flight_sky_blocks": 10,
    "flight_side_blocks": 12,
}


def _preferred_python() -> str:
    return sys.executable or "python"


def _pid_of(pid_name: str) -> int | None:
    pid_file = _ROOT / "runtime" / f"{pid_name}.pid"
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        import os

        os.kill(pid, 0)
        return pid
    except Exception:
        return None


def _start_pet() -> None:
    kwargs: dict = dict(cwd=str(_ROOT), close_fds=True)
    if sys.platform == "win32":
        kwargs["creationflags"] = PROCESS_FLAGS
    # On macOS pick launcher_mac.py if it exists, else fall back to launcher.py
    launcher = _ROOT / "app" / "launcher_mac.py"
    if not launcher.exists():
        launcher = _ROOT / "app" / "launcher.py"
    try:
        subprocess.Popen([_preferred_python(), str(launcher)], **kwargs)
    except Exception as e:
        print(f"[panel] start failed: {e}")


def _stop_pet() -> None:
    pid_file = _ROOT / "runtime" / "launcher.pid"
    if not pid_file.exists():
        return
    try:
        pid = int(pid_file.read_text().strip())
        import os, signal

        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        pid_file.unlink(missing_ok=True)
    except Exception:
        pass


class ControlPanel:
    def __init__(self) -> None:
        ensure_runtime_files()
        self.root = tk.Tk()
        self.root.title("咕咕桌宠 — 控制面板")
        self.root.geometry("680x900")
        self.root.minsize(600, 700)
        self.root.configure(bg=BG)
        self._chat_sig: tuple = ()
        self._refresh_job: str | None = None
        self._drive_canvases: dict[str, tk.Canvas] = {}
        self._range_var = tk.StringVar(value="活动范围: —")
        self._build()
        self.root.after(300, self._refresh)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build(self) -> None:
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True)
        _canvas, shell = scrolled_frame(outer, BG)

        # 标题
        tk.Label(
            shell,
            text="咕咕桌宠",
            bg=BG,
            fg=FG_DARK,
            font=(*FONT_TITLE[:1], 20, "bold"),
        ).pack(anchor="w", padx=22, pady=(18, 2))
        tk.Label(shell, text="控制面板", bg=BG, fg=FG_LIGHT, font=FONT_LABEL).pack(
            anchor="w", padx=22, pady=(0, 14)
        )

        wrap = tk.Frame(shell, bg=BG, padx=22)
        wrap.pack(fill="both", expand=True)

        # 启动/停止
        self._build_launcher(wrap)

        # 状态栏
        self._status_var = tk.StringVar(value="就绪")
        tk.Label(
            wrap,
            textvariable=self._status_var,
            bg=BG,
            fg=FG_LIGHT,
            font=FONT_MONO_SM,
        ).pack(anchor="w", pady=(0, 8))

        # 倍速
        self._build_speed(wrap)

        # 内驱力
        self._build_drives(wrap)

        # 聊天
        self._build_chat(wrap)

        # 设置（始终展开）
        SettingsPanel(
            wrap,
            on_save=lambda: self._status_var.set("✓ 设置已保存"),
        )

    def _build_launcher(self, parent: tk.Widget) -> None:
        c = card(parent)
        c.pack(fill="x", pady=(0, 10))

        header = tk.Frame(c, bg=ACCENT_GREEN)
        header.pack(fill="x")
        tk.Label(
            header,
            text="咕咕桌宠",
            bg=ACCENT_GREEN,
            fg="white",
            font=FONT_BOLD,
            padx=14,
            pady=8,
        ).pack(side="left")
        self._pet_status_lbl = tk.Label(
            header,
            text="未运行",
            bg=ACCENT_GREEN,
            fg="white",
            font=FONT_MONO_SM,
            padx=14,
        )
        self._pet_status_lbl.pack(side="right")

        btn_row = tk.Frame(c, bg=BG_CARD)
        btn_row.pack(anchor="w", padx=14, pady=10)
        btn_primary(btn_row, "▶  启动桌宠", self._start_all).pack(side="left")
        btn_secondary(btn_row, "■  停止", self._stop_all).pack(side="left", padx=8)
        btn_secondary(btn_row, "↑  更新", self._run_update).pack(side="left", padx=8)

    def _build_speed(self, parent: tk.Widget) -> None:
        c = card(parent)
        c.pack(fill="x", pady=(0, 10))
        section_title(c, "运动参数").pack(anchor="w", padx=16, pady=(12, 4))

        ctrl = read_json(CONTROL_FILE, DEFAULT_CONTROL)

        def _make_slider(
            label: str,
            key: str,
            lo: float,
            hi: float,
            default: float,
            fmt: str,
            res: float = 0.1,
        ) -> None:
            try:
                cur = float(ctrl.get(key, default) or default)
                cur = max(lo, min(hi, cur))
            except Exception:
                cur = default

            var = tk.DoubleVar(value=cur)
            lbl_var = tk.StringVar(value=fmt.format(cur))
            setattr(self, f"_{key}_var", var)
            setattr(self, f"_{key}_lbl", lbl_var)

            row = tk.Frame(c, bg=BG_CARD)
            row.pack(fill="x", padx=16, pady=(0, 6))

            tk.Label(
                row,
                text=label,
                bg=BG_CARD,
                fg=FG_MID,
                font=FONT_LABEL,
                width=8,
                anchor="w",
            ).pack(side="left")
            tk.Label(
                row, text=fmt.format(lo), bg=BG_CARD, fg=FG_LIGHT, font=FONT_SMALL
            ).pack(side="left")

            def _on_change(_v=None, _k=key, _var=var, _lbl=lbl_var, _fmt=fmt):
                try:
                    val = round(float(_var.get()), 2)
                    _lbl.set(_fmt.format(val))
                    c2 = read_json(CONTROL_FILE, DEFAULT_CONTROL)
                    c2[_k] = val
                    write_json(CONTROL_FILE, c2)
                except Exception:
                    pass

            tk.Scale(
                row,
                variable=var,
                from_=lo,
                to=hi,
                resolution=res,
                orient="horizontal",
                showvalue=False,
                bg=BG_CARD,
                fg=FG_DARK,
                troughcolor=BORDER,
                highlightthickness=0,
                bd=0,
                command=_on_change,
            ).pack(side="left", fill="x", expand=True, padx=6)

            tk.Label(
                row, text=fmt.format(hi), bg=BG_CARD, fg=FG_LIGHT, font=FONT_SMALL
            ).pack(side="left")
            tk.Label(
                row,
                textvariable=lbl_var,
                bg=BG_CARD,
                fg=FG_DARK,
                font=FONT_BOLD,
                width=6,
            ).pack(side="left", padx=(8, 0))

        _make_slider("活动倍速", "speed_scale", 0.05, 5.0, 1.0, "{:.2f}x", res=0.05)
        _make_slider("飞行速度", "flight_speed_scale", 0.3, 4.0, 1.0, "{:.1f}x")
        _make_slider("阻  力", "physics_scale", 0.3, 4.0, 1.0, "{:.1f}x")
        _make_slider("动画速率", "anim_speed", 0.2, 4.0, 1.0, "{:.1f}x")
        _make_slider("帧  率", "fps_target", 10, 120, 62, "{:.0f}fps", res=5)

        tk.Frame(c, bg=BG_CARD, height=6).pack()

    def _on_speed_change(self, _val=None) -> None:
        # 兼容旧代码引用，实际已由 _make_slider 内联回调处理
        pass

    def _build_drives(self, parent: tk.Widget) -> None:
        c = card(parent)
        c.pack(fill="x", pady=(0, 10))
        section_title(c, "内驱力状态").pack(anchor="w", padx=16, pady=(12, 4))
        self._motive_var = tk.StringVar(value="主导动机: —")
        small_label(c, textvariable=self._motive_var).pack(
            anchor="w", padx=16, pady=(0, 8)
        )
        for key in ("energy", "social", "curiosity", "comfort"):
            row = tk.Frame(c, bg=BG_CARD)
            row.pack(fill="x", padx=16, pady=3)
            tk.Label(
                row,
                text=_DRIVE_LABELS[key],
                bg=BG_CARD,
                fg=FG_MID,
                font=FONT_LABEL,
                width=5,
                anchor="w",
            ).pack(side="left")
            bar = drive_bar(row, width=240)
            bar.pack(side="left", fill="x", expand=True, padx=(0, 12))
            self._drive_canvases[key] = bar
        tk.Frame(c, bg=BG_CARD, height=10).pack()

    def _build_chat(self, parent: tk.Widget) -> None:
        c = card(parent)
        c.pack(fill="both", expand=True, pady=(0, 10))

        header = tk.Frame(c, bg="#EAE1D1")
        header.pack(fill="x")
        tk.Label(
            header,
            text="和咕咕聊天",
            bg="#EAE1D1",
            fg=FG_DARK,
            font=FONT_TITLE,
            padx=16,
            pady=10,
        ).pack(side="left")

        body = tk.Frame(c, bg=BG_CARD, padx=10, pady=10)
        body.pack(fill="both", expand=True)

        msg_shell = tk.Frame(
            body, bg="#ECE5DD", highlightthickness=1, highlightbackground=BORDER
        )
        msg_shell.pack(fill="both", expand=True)
        sb = tk.Scrollbar(msg_shell)
        sb.pack(side="right", fill="y")
        self._chat_canvas = tk.Canvas(
            msg_shell,
            bg="#ECE5DD",
            highlightthickness=0,
            bd=0,
            yscrollcommand=sb.set,
            height=220,
        )
        self._chat_canvas.pack(fill="both", expand=True)
        sb.configure(command=self._chat_canvas.yview)
        self._msg_frame = tk.Frame(self._chat_canvas, bg="#ECE5DD")
        self._msg_win = self._chat_canvas.create_window(
            (0, 0), window=self._msg_frame, anchor="nw"
        )
        self._msg_frame.bind(
            "<Configure>",
            lambda _e: self._chat_canvas.configure(
                scrollregion=self._chat_canvas.bbox("all")
            ),
        )
        self._chat_canvas.bind(
            "<Configure>",
            lambda e: self._chat_canvas.itemconfigure(self._msg_win, width=e.width),
        )

        # 输入框
        composer = tk.Frame(body, bg=BG_CARD)
        composer.pack(fill="x", pady=(8, 0))
        self._input = tk.Text(
            composer,
            height=3,
            wrap="word",
            bg="#FFFFFF",
            fg=FG_DARK,
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            font=FONT_LABEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self._input.pack(side="left", fill="x", expand=True)
        self._input.bind("<Return>", self._send)
        btn_primary(composer, "发送", self._send).pack(side="left", padx=(6, 0))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _start_all(self) -> None:
        _start_pet()
        self._status_var.set("正在启动…")

    def _stop_all(self) -> None:
        _stop_pet()
        self._status_var.set("已停止")

    def _run_update(self) -> None:
        _stop_pet()
        self._status_var.set("正在更新…")
        self.root.update_idletasks()
        kwargs: dict = dict(cwd=str(_ROOT), close_fds=True)
        if sys.platform == "win32":
            kwargs["creationflags"] = 0  # show window for progress
        try:
            subprocess.Popen(
                [_preferred_python(), str(_ROOT / "do_update.py")], **kwargs
            )
        except Exception as e:
            self._status_var.set(f"更新失败: {e}")

    def _send(self, _event=None) -> str:
        text = self._input.get("1.0", "end").strip()
        if not text:
            return "break"
        self._input.delete("1.0", "end")
        try:
            now = time.time()
            log = read_event_log()
            next_id = int(log.next_event_id or 1)
            pet_state = read_status().pet_state
            log.events.append(
                {
                    "id": next_id,
                    "type": BodyEventName.USER_MESSAGE,
                    "ts": now,
                    "payload": {
                        "text": text,
                        "pet_state": pet_state,
                        "mood": "alert",
                        "summary": f"主人说: {text}",
                    },
                }
            )
            log.next_event_id = next_id + 1
            write_event_log(log)
            # Also write to conversation history so chat panel shows it
            history = read_json(HISTORY_FILE, DEFAULT_HISTORY)
            hist_items = history.get("items", [])
            if not isinstance(hist_items, list):
                hist_items = []
            hist_items.append(
                {"role": "owner", "name": "主人", "text": text[:500], "ts": now}
            )
            history["items"] = hist_items[-200:]
            write_json(HISTORY_FILE, history)
            self._chat_sig = ()  # force refresh
            self._refresh_chat()
            self._status_var.set("已发送")
        except Exception as e:
            self._status_var.set(f"发送失败: {e}")
        return "break"

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        try:
            self._refresh_pet_status()
            self._refresh_drives()
            self._refresh_chat()
        except Exception:
            pass
        self._refresh_job = self.root.after(REFRESH_MS, self._refresh)

    def _refresh_pet_status(self) -> None:
        pid = _pid_of("launcher")
        if pid:
            self._pet_status_lbl.configure(text=f"运行中 PID {pid}")
        else:
            self._pet_status_lbl.configure(text="未运行")

    def _refresh_drives(self) -> None:
        try:
            state = read_state()
            drives = dict(state.drives) if state.drives else {}
            motive = str(state.dominant_drive or "—")
            motive_cn = {
                "rest": "休息",
                "seek_attention": "寻求陪伴",
                "explore_air": "探索飞行",
                "settle": "安定",
            }.get(motive, motive)
            self._motive_var.set(f"主导动机: {motive_cn}")
            for key, canvas in self._drive_canvases.items():
                try:
                    val = float(drives.get(key, 0.0) or 0.0)
                except Exception:
                    val = 0.0
                draw_drive_bar(canvas, val, _DRIVE_COLOURS.get(key, "#999"))
        except Exception:
            pass

    def _refresh_chat(self) -> None:
        try:
            history = read_json(HISTORY_FILE, DEFAULT_HISTORY)
            items = history.get("items", [])
            if not isinstance(items, list):
                items = []
            sig = tuple(
                (
                    str(it.get("role", "")),
                    str(it.get("text", "")),
                    int(float(it.get("ts", 0) or 0)),
                )
                for it in items
            )
            if sig == self._chat_sig:
                return
            self._chat_sig = sig
            # Rebuild message list
            for child in self._msg_frame.winfo_children():
                child.destroy()
            for it in items:
                role = str(it.get("role", ""))
                text = str(it.get("text", "")).strip()
                if not text or text == "...":
                    continue
                self._add_bubble(role, text)
            self._msg_frame.update_idletasks()
            self._chat_canvas.configure(scrollregion=self._chat_canvas.bbox("all"))
            self._chat_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _add_bubble(self, role: str, text: str) -> None:
        is_owner = role == "owner"
        row = tk.Frame(self._msg_frame, bg="#ECE5DD")
        row.pack(fill="x", pady=3, padx=8)
        name = tk.Label(
            row,
            text="我" if is_owner else "咕咕",
            bg="#ECE5DD",
            fg=FG_LIGHT,
            font=FONT_SMALL,
        )
        name.pack(anchor="e" if is_owner else "w")
        bubble = tk.Label(
            row,
            text=text,
            wraplength=300,
            justify="left",
            anchor="w",
            bg="#95EC69" if is_owner else "#FFFFFF",
            fg=FG_DARK,
            padx=10,
            pady=6,
            font=FONT_LABEL,
        )
        bubble.pack(anchor="e" if is_owner else "w")
        self._chat_canvas.update_idletasks()
        self._chat_canvas.yview_moveto(1.0)

    # ------------------------------------------------------------------

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    panel = ControlPanel()
    panel.run()


if __name__ == "__main__":
    main()
