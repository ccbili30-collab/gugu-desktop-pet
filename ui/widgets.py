"""Shared UI widgets for gugupet_v2 control panel."""

from __future__ import annotations

import tkinter as tk
from typing import Callable


BG = "#F3E9D3"
BG_CARD = "#F7EFDF"
BG_INPUT = "#FFFDF8"
FG_DARK = "#2C2A27"
FG_MID = "#473A2B"
FG_LIGHT = "#7A6F60"
BORDER = "#D6C5A8"
ACCENT_GREEN = "#2F7A64"
ACCENT_SAND = "#EADBC3"
FONT_TITLE = ("Bahnschrift SemiBold", 14)
FONT_LABEL = ("Microsoft YaHei UI", 10)
FONT_SMALL = ("Microsoft YaHei UI", 9)
FONT_MONO = ("Consolas", 10)
FONT_MONO_SM = ("Consolas", 9)
FONT_BOLD = ("Bahnschrift SemiBold", 10)


def card(parent: tk.Widget, **kw) -> tk.Frame:
    return tk.Frame(
        parent,
        bg=BG_CARD,
        highlightthickness=1,
        highlightbackground=BORDER,
        **kw,
    )


def section_title(parent: tk.Widget, text: str) -> tk.Label:
    return tk.Label(parent, text=text, bg=BG_CARD, fg=FG_DARK, font=FONT_TITLE)


def label(parent: tk.Widget, text: str, **kw) -> tk.Label:
    return tk.Label(parent, text=text, bg=BG_CARD, fg=FG_MID, font=FONT_LABEL, **kw)


def small_label(parent: tk.Widget, text: str = "", textvariable=None, **kw) -> tk.Label:
    kwargs: dict = dict(bg=BG_CARD, fg=FG_LIGHT, font=FONT_SMALL, **kw)
    if textvariable is not None:
        return tk.Label(parent, textvariable=textvariable, **kwargs)
    return tk.Label(parent, text=text, **kwargs)


def entry(
    parent: tk.Widget,
    textvariable: tk.StringVar,
    show: str | None = None,
    width: int = 28,
) -> tk.Entry:
    return tk.Entry(
        parent,
        textvariable=textvariable,
        show=show,
        bg=BG_INPUT,
        fg=FG_DARK,
        relief="flat",
        highlightthickness=1,
        highlightbackground=BORDER,
        font=FONT_MONO,
        width=width,
    )


def btn_primary(parent: tk.Widget, text: str, command: Callable, **kw) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=ACCENT_GREEN,
        fg="white",
        activebackground=ACCENT_GREEN,
        activeforeground="white",
        relief="flat",
        cursor="hand2",
        font=FONT_BOLD,
        padx=10,
        pady=7,
        **kw,
    )


def btn_secondary(parent: tk.Widget, text: str, command: Callable, **kw) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=ACCENT_SAND,
        fg=FG_MID,
        activebackground="#D8C5A6",
        activeforeground=FG_MID,
        relief="flat",
        cursor="hand2",
        font=FONT_BOLD,
        padx=10,
        pady=7,
        **kw,
    )


def drive_bar(parent: tk.Widget, width: int = 260) -> tk.Canvas:
    return tk.Canvas(
        parent,
        width=width,
        height=14,
        bg="#FFF6E7",
        highlightthickness=1,
        highlightbackground=BORDER,
        bd=0,
    )


def draw_drive_bar(canvas: tk.Canvas, value: float, colour: str) -> None:
    canvas.delete("all")
    w = canvas.winfo_width() or 260
    h = canvas.winfo_height() or 14
    fill_w = max(0, min(w, int(w * max(0.0, min(1.0, value)))))
    canvas.create_rectangle(0, 0, w, h, fill="#FFF6E7", outline="")
    canvas.create_rectangle(0, 0, fill_w, h, fill=colour, outline="")
    canvas.create_text(
        w - 5,
        h / 2,
        text=f"{int(value * 100)}%",
        anchor="e",
        fill="#5F5348",
        font=FONT_MONO_SM,
    )


def scrolled_frame(parent: tk.Widget, bg: str = BG) -> tuple[tk.Canvas, tk.Frame]:
    canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
    sb = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=bg)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind(
        "<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))
    canvas.bind_all(
        "<MouseWheel>",
        lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
    )
    return canvas, inner
