"""设置面板 — API / 宠物身份配置"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import loader as cfg
from ui.widgets import (
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
    FONT_SMALL,
    FONT_TITLE,
    btn_primary,
    btn_secondary,
    card,
    entry,
    label,
    section_title,
    small_label,
)


class SettingsPanel:
    def __init__(self, parent: tk.Widget, on_save: callable | None = None) -> None:
        self._on_save = on_save
        self._frame = card(parent)
        self._frame.pack(fill="x", pady=(0, 10))
        self._build()

    def _build(self) -> None:
        f = self._frame
        section_title(f, "⚙ AI 设置").pack(anchor="w", padx=16, pady=(14, 6))

        config = cfg.load_raw()
        llm = cfg.llm(config)
        pet_cfg = cfg.pet(config)

        # ── 宠物身份 ──
        id_card = tk.Frame(f, bg=BG_CARD)
        id_card.pack(fill="x", padx=16, pady=(0, 8))

        label(id_card, "宠物名字").grid(row=0, column=0, sticky="w", pady=4)
        self._name_var = tk.StringVar(value=str(pet_cfg.get("name", "咕咕")))
        entry(id_card, self._name_var, width=18).grid(
            row=0, column=1, sticky="w", padx=(12, 0)
        )

        label(id_card, "物种").grid(row=1, column=0, sticky="w", pady=4)
        self._species_var = tk.StringVar(value=str(pet_cfg.get("species", "pigeon")))
        entry(id_card, self._species_var, width=18).grid(
            row=1, column=1, sticky="w", padx=(12, 0)
        )

        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(4, 10))

        # ── LLM 配置 ──
        small_label(f, text="配置 AI 接口（兼容 OpenAI 格式，推荐 DeepSeek）").pack(
            anchor="w", padx=16, pady=(0, 6)
        )

        llm_frame = tk.Frame(f, bg=BG_CARD)
        llm_frame.pack(fill="x", padx=16, pady=(0, 8))
        llm_frame.grid_columnconfigure(1, weight=1)

        fields = [
            ("API Key", "api_key", True),
            ("接口地址 (Base URL)", "base_url", False),
            ("模型名称 (Model)", "model", False),
            ("超时秒数", "timeout", False),
            ("随机性 (Temperature)", "temperature", False),
        ]
        self._llm_vars: dict[str, tk.StringVar] = {}
        for i, (lbl, key, secret) in enumerate(fields):
            tk.Label(llm_frame, text=lbl, bg=BG_CARD, fg=FG_MID, font=FONT_LABEL).grid(
                row=i, column=0, sticky="w", pady=4, padx=(0, 8)
            )
            var = tk.StringVar(value=str(llm.get(key, "")))
            self._llm_vars[key] = var
            show = "*" if secret else None
            e = entry(llm_frame, var, show=show)
            e.grid(row=i, column=1, sticky="ew", pady=4)

        self._enabled_var = tk.BooleanVar(
            value=bool(llm.get("enabled", False) or str(llm.get("api_key", "")).strip())
        )
        tk.Checkbutton(
            f,
            text="启用内置 AI 对话",
            variable=self._enabled_var,
            bg=BG_CARD,
            fg=FG_MID,
            activebackground=BG_CARD,
            selectcolor="#FFF6E7",
            font=FONT_LABEL,
        ).pack(anchor="w", padx=16, pady=(0, 6))

        # 状态栏
        self._status_var = tk.StringVar(value="")
        tk.Label(
            f,
            textvariable=self._status_var,
            bg=BG_CARD,
            fg=FG_LIGHT,
            font=FONT_SMALL,
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(0, 4))

        # 按钮
        btn_row = tk.Frame(f, bg=BG_CARD)
        btn_row.pack(anchor="w", padx=16, pady=(0, 14))
        btn_primary(btn_row, "保存", self._save).pack(side="left")
        btn_secondary(btn_row, "测试连接", self._test).pack(side="left", padx=(8, 0))

    def _collect(self) -> dict:
        try:
            timeout = float(self._llm_vars["timeout"].get() or 25)
        except ValueError:
            timeout = 25.0
        try:
            temperature = float(self._llm_vars["temperature"].get() or 0.8)
        except ValueError:
            temperature = 0.8
        api_key = self._llm_vars["api_key"].get().strip()
        return {
            "pet": {
                "name": self._name_var.get().strip() or "咕咕",
                "species": self._species_var.get().strip() or "pigeon",
            },
            "llm": {
                "enabled": bool(self._enabled_var.get() or api_key),
                "api_key": api_key,
                "base_url": self._llm_vars["base_url"].get().strip()
                or "https://api.openai.com/v1",
                "model": self._llm_vars["model"].get().strip() or "gpt-4o-mini",
                "timeout": timeout,
                "temperature": temperature,
            },
        }

    def _save(self) -> None:
        updates = self._collect()
        try:
            config = cfg.load_raw()
            config.update(updates)
            cfg.save(config)
            self._status_var.set("✓ 已保存")
        except Exception as e:
            self._status_var.set(f"保存失败: {e}")
            return
        if self._on_save:
            self._on_save()

    def _test(self) -> None:
        updates = self._collect()
        llm_cfg = updates["llm"]
        if not llm_cfg.get("api_key"):
            self._status_var.set("请先填写 API Key")
            return
        self._status_var.set("连接测试中…")
        self._frame.update_idletasks()
        try:
            from brain.llm_client import chat_completion

            result = chat_completion(
                messages=[{"role": "user", "content": "Reply with exactly: ok"}],
                config=llm_cfg,
                max_tokens=8,
            )
            if result.get("ok"):
                self._status_var.set(
                    f"✓ 连接成功，模型回复: {str(result.get('text', ''))[:40]}"
                )
            else:
                self._status_var.set(
                    f"✗ 连接失败: {str(result.get('error', '未知错误'))[:60]}"
                )
        except Exception as e:
            self._status_var.set(f"✗ 异常: {e}")
