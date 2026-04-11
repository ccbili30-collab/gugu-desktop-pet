"""macOS desktop pet window — thin subclass of the Windows DesktopPet.

Strategy
--------
Inherit every behaviour / physics / state-machine method from the original
DesktopPet (body/pet_window.py) unchanged.  Only override the small set of
methods that touch platform APIs:

  Platform layer   (ctypes → pyobjc / Quartz)
  Rendering layer  (tkinter Canvas → pygame Surface + NSWindow)
  Font paths       (C:/Windows/Fonts → macOS system fonts)
  Shortcut helper  (.lnk PowerShell → .command shell script)
  Main loop        (root.mainloop / root.after → pygame Clock)

Everything else — physics, state machine, commands, events, bubbles,
particles — runs without a single line changed.

macOS coordinate note
---------------------
NSWindow uses bottom-left origin; pygame uses top-left.
`update_window_position()` converts win_x / win_y (top-left, same as
Windows) to the NSWindow bottom-left origin before calling setFrameOrigin_.
"""

from __future__ import annotations

import math
import os
import random
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so we can import the original body
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# pygame — must be imported before the parent class touches tkinter
# (we monkeypatch tkinter stubs below so the parent __init__ won't crash)
# ---------------------------------------------------------------------------
import pygame  # type: ignore

# ---------------------------------------------------------------------------
# pyobjc
# ---------------------------------------------------------------------------
try:
    from AppKit import (  # type: ignore
        NSApplication,
        NSBackingStoreBuffered,
        NSBorderlessWindowMask,
        NSColor,
        NSFloatingWindowLevel,
        NSPanel,
        NSScreen,
        NSWindow,
        NSWindowStyleMaskBorderless,
    )
    from Foundation import NSMakeRect, NSObject  # type: ignore
    import Quartz  # type: ignore

    _HAS_PYOBJC = True
except ImportError:
    _HAS_PYOBJC = False
    print(
        "[pet_window_mac] WARNING: pyobjc not found – falling back to pygame-only mode"
    )

# ---------------------------------------------------------------------------
# PIL for bubble rendering
# ---------------------------------------------------------------------------
from PIL import Image, ImageDraw, ImageFont  # type: ignore

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
from pet.pigeon_sprite import FRAMES, FRAME_GROUND_ROWS
from pet.openclaw_pet import extract_json_payload, read_pet_profile
from service_runtime import ensure_single_instance, read_json, runtime_file, write_json
from shared.platform_mac import get_work_area, get_cursor_pos, generate_pet
from shared.particles import HeartParticle, TextParticle, TrailParticle, SpeechBubble

# ---------------------------------------------------------------------------
# Re-use ALL constants from the original window module
# ---------------------------------------------------------------------------
from body.pet_window import (
    PIXEL_SIZE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    TICK_MS,
    FALL_GRAVITY,
    TERMINAL_VELOCITY,
    FLING_MAX_SPEED,
    WALL_BOUNCE_FACTOR,
    GROUND_BOUNCE_FACTOR,
    GROUND_BOUNCE_MIN_VY,
    HEART_QUEUE_CAP,
    HEART_EMIT_INTERVAL,
    TOUCH_SIGNAL_COOLDOWN,
    PET_SIGNAL_COOLDOWN,
    SLEEP_WAKE_CLICK_WINDOW,
    SLEEP_WAKE_REQUIRED_CLICKS,
    WAKE_SHAKE_DURATION,
    MANUAL_AWAKE_DURATION,
    PET_BUBBLE_DURATION,
    CHAT_BUBBLE_DURATION,
    CHAT_BUBBLE_WRAP_WIDTH,
    PET_BUBBLE_LEFT,
    PET_BUBBLE_TOP_MIN,
    PET_BUBBLE_TOP_OFFSET,
    PET_BUBBLE_WRAP_WIDTH,
    PET_BUBBLE_BOTTOM_MARGIN,
    SLEEP_IDLE_DELAY,
    GROUND_PADDING,
    FLOOR_OFFSET,
    FLY_LIFT_PX,
    SPRITE_WIDTH,
    SPRITE_HEIGHT,
    CONTROL_FILE,
    COMMAND_FILE,
    STATUS_FILE,
    EVENT_FILE,
    STATE_FILE,
    CONFIG_FILE,
    HISTORY_FILE,
    FIRST_LAUNCH_FILE,
    UI_REQUEST_FILE,
    DEFAULT_CONTROL,
    DEFAULT_COMMAND,
    DEFAULT_EVENT_LOG,
    DEFAULT_BRAIN_STATE,
    DEFAULT_HISTORY,
    DEFAULT_FIRST_LAUNCH,
    DEFAULT_UI_REQUESTS,
    BORED_TIMEOUT,
    TIRED_TIMEOUT,
    BRAIN_STALE_TIMEOUT,
    PIXEL_COLORS,
    SLINGSHOT_MAX_PULL,
    SLINGSHOT_LAUNCH_SCALE,
    SLINGSHOT_MAX_LAUNCH_SPEED,
    SLINGSHOT_PANIC_INTERVAL,
    SLINGSHOT_RECOIL_STEPS,
    SLINGSHOT_STRING_COLOR,
    SLINGSHOT_STRING_WIDTH,
    FLIGHT_BOB_MAX,
    FLIGHT_CURSOR_STEER,
    LONG_FLIGHT_HOVER_THRESHOLD,
    HOVER_IDLE_LAND_DELAY,
    HOVER_CLICK_EXTEND,
    DRAG_VELOCITY_BLEND,
    DRAG_THROW_SAMPLE_WINDOW,
    DRAG_THROW_MIN_SPEED,
    DRAG_CONTINUE_FLIGHT_CHANCE,
    FLING_CURVE_DISTANCE,
    FLING_CURVE_RISE,
    TRAIL_LIMIT,
    RIGHT_CLICK_MULTI_WINDOW,
)

# Import the original class — we subclass it
from body.pet_window import DesktopPet as _DesktopPetWin

# ---------------------------------------------------------------------------
# macOS font paths
# ---------------------------------------------------------------------------
_MAC_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode MS.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _mac_font_path() -> Path | None:
    for p in _MAC_FONT_CANDIDATES:
        if Path(p).exists():
            return Path(p)
    return None


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _slingshot_color_rgb() -> tuple[int, int, int]:
    return _hex_to_rgb(SLINGSHOT_STRING_COLOR)


# ---------------------------------------------------------------------------
# Stub classes so the parent __init__ doesn't crash when it touches tkinter
# ---------------------------------------------------------------------------


class _FakeAfter:
    """Collects after() calls during __init__; we replay none of them."""

    _jobs: list = []

    def after(self, ms: int, fn=None, *args):  # noqa: D401
        return id(fn)  # return a fake job id

    def after_cancel(self, job_id):
        pass


class _FakeCanvas:
    """No-op stand-in for tk.Canvas used in parent __init__."""

    def bind(self, *a, **kw):
        pass

    def delete(self, *a, **kw):
        pass

    def create_rectangle(self, *a, **kw):
        return 0

    def create_text(self, *a, **kw):
        return 0

    def create_line(self, *a, **kw):
        return 0

    def create_oval(self, *a, **kw):
        return 0

    def create_polygon(self, *a, **kw):
        return 0

    def create_window(self, *a, **kw):
        return 0

    def coords(self, *a, **kw):
        pass

    def bbox(self, *a, **kw):
        return (0, 0, 80, 20)

    def tag_raise(self, *a, **kw):
        pass

    def itemconfigure(self, *a, **kw):
        pass

    def pack(self, *a, **kw):
        pass


class _FakeFont:
    def __init__(self, *a, **kw):
        pass

    def measure(self, text):
        return len(text) * 8

    def metrics(self, *a):
        return {"linespace": 16}


class _FakeRoot(_FakeAfter):
    """Thin tkinter.Tk stub used during parent __init__ on macOS."""

    def __init__(self):
        self.title = lambda *a: None
        self.overrideredirect = lambda *a: None
        self.wm_attributes = lambda *a, **kw: None
        self.wm_attributes.__doc__ = ""
        self.geometry = lambda *a: None
        self.winfo_screenwidth = lambda: 1920
        self.winfo_screenheight = lambda: 1080
        self.update_idletasks = lambda: None
        self.configure = lambda *a, **kw: None
        self.protocol = lambda *a: None
        self.mainloop = lambda: None
        self.destroy = lambda: None
        self.quit = lambda: None


# ---------------------------------------------------------------------------
# DesktopPetMac
# ---------------------------------------------------------------------------


class DesktopPetMac(_DesktopPetWin):
    """macOS port.  Overrides only the platform / rendering surface."""

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        # --- 1. Detect screen geometry via AppKit ---
        if _HAS_PYOBJC:
            screen = NSScreen.mainScreen()
            full_frame = screen.frame()
            self._screen_h_mac = int(full_frame.size.height)
            self._screen_w_mac = int(full_frame.size.width)
        else:
            self._screen_h_mac = 1080
            self._screen_w_mac = 1920

        # --- 2. Inject stubs so parent __init__ doesn't blow up ---
        import tkinter as _tk
        import tkinter.font as _tkfont

        _real_tk = _tk.Tk
        _real_font = _tkfont.Font
        _tk.Tk = lambda: _FakeRoot()  # type: ignore
        _tkfont.Font = _FakeFont  # type: ignore

        # Run the parent constructor (sets up ALL state variables)
        super().__init__()

        # Restore tkinter (control panel may still need it)
        _tk.Tk = _real_tk  # type: ignore
        _tkfont.Font = _real_font  # type: ignore

        # --- 3. Override screen dimensions with real macOS values ---
        self.screen_w = self._screen_w_mac
        self.screen_h = self._screen_h_mac

        # Recompute work area + floor using macOS visible frame
        wl, wt, wr, wb = get_work_area()
        self.work_left = wl
        self.work_top = wt
        self.work_right = wr
        self.work_bottom = wb
        self.base_floor_y = self.work_bottom - WINDOW_HEIGHT + FLOOR_OFFSET
        self.floor_y = self.base_floor_y
        self.base_ground_y = WINDOW_HEIGHT - GROUND_PADDING
        self.ground_y = self.base_ground_y

        # Initial window position (top-right corner, above dock)
        self.win_x = float(self.work_right - WINDOW_WIDTH - 40)
        self.win_y = float(self.base_floor_y)

        # --- 4. pygame surface ---
        pygame.init()
        pygame.display.init()

        # Transparent, borderless, always-on-top window via pygame flags
        flags = pygame.NOFRAME
        self._pg_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)
        pygame.display.set_caption("咕咕桌宠")

        # --- 5. Attach NSWindow wrapper for transparency + topmost ---
        self._ns_window: object | None = None
        if _HAS_PYOBJC:
            self._setup_nswindow()

        # --- 6. pygame fonts ---
        fp = _mac_font_path()
        self._pg_font_path = str(fp) if fp else None
        self._pg_bubble_font = self._make_pg_font(10)
        self._pg_kaomoji_font = self._make_pg_font(10)
        self._pg_heart_font = self._make_pg_font(12)
        self._pg_sleep_font = self._make_pg_font(11)

        # --- 7. Drag state for pygame mouse events ---
        self._pg_drag_start_screen: tuple[int, int] = (0, 0)
        self._pg_slingshot_mouse: tuple[int, int] = (0, 0)

        # --- 8. Dialog state (simple pygame overlay) ---
        self._dialog_text = ""
        self._dialog_cursor = 0  # caret position in text
        self._dialog_active = False

        # Clock for frame timing
        self._pg_clock = pygame.time.Clock()

        # --- 9. Kick off first position ---
        self.update_window_position()

    # ------------------------------------------------------------------
    # NSWindow setup
    # ------------------------------------------------------------------

    def _setup_nswindow(self) -> None:
        """Wrap the pygame SDL window in a transparent, always-on-top NSWindow."""
        try:
            import ctypes, ctypes.util

            # Get the SDL window handle (NSWindow* on macOS)
            sdl_lib = ctypes.CDLL(ctypes.util.find_library("SDL2"))
            sdl_lib.SDL_GetWindowWMInfo.restype = ctypes.c_int

            # Simpler: use pyobjc to find the NSWindow via app's window list
            app = NSApplication.sharedApplication()
            # Give the run loop a brief spin so SDL's NSWindow is registered
            import AppKit

            AppKit.NSRunLoop.mainRunLoop().runUntilDate_(
                AppKit.NSDate.dateWithTimeIntervalSinceNow_(0.05)
            )
            windows = app.windows()
            if windows and len(windows) > 0:
                self._ns_window = windows[0]
                ns = self._ns_window
                ns.setOpaque_(False)
                ns.setBackgroundColor_(NSColor.clearColor())
                ns.setLevel_(NSFloatingWindowLevel)
                ns.setIgnoresMouseEvents_(False)
                ns.setCollectionBehavior_(
                    1 << 3  # NSWindowCollectionBehaviorCanJoinAllSpaces
                )
        except Exception as e:
            print(f"[pet_window_mac] NSWindow setup error: {e}")
            self._ns_window = None

    # ------------------------------------------------------------------
    # Font helper
    # ------------------------------------------------------------------

    def _make_pg_font(self, size: int) -> pygame.font.Font:
        if self._pg_font_path:
            try:
                return pygame.font.Font(self._pg_font_path, size)
            except Exception:
                pass
        return pygame.font.SysFont("pingfang sc", size) or pygame.font.Font(None, size)

    # ------------------------------------------------------------------
    # macOS font path (overrides Windows C:/Windows/Fonts lookup)
    # ------------------------------------------------------------------

    def find_text_font_path(self) -> Path | None:
        return _mac_font_path()

    # ------------------------------------------------------------------
    # Window position (top-left coords → NSWindow bottom-left)
    # ------------------------------------------------------------------

    def update_window_position(self) -> None:
        x = int(self.win_x)
        # Convert top-left y to NSWindow bottom-left y
        # NSWindow origin = screen_bottom_left; y measured upward
        mac_y = self._screen_h_mac - int(self.win_y) - WINDOW_HEIGHT
        if self._ns_window is not None:
            try:
                self._ns_window.setFrameOrigin_((x, mac_y))
            except Exception:
                pass
        else:
            # Fallback: move the SDL window via pygame display
            try:
                os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{int(self.win_y)}"
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Rendering — pixel art
    # ------------------------------------------------------------------

    def draw_pixel_art(self, art_name: str, x: float, y: float) -> None:
        art = FRAMES.get(art_name, FRAMES["idle1"])
        sx0 = int(x)
        sy0 = int(y)
        for row_i, row in enumerate(art):
            for col_i, pixel in enumerate(row):
                rgb = PIXEL_COLORS.get(pixel)
                if rgb is None:
                    continue
                color = _hex_to_rgb(rgb)
                rect = (
                    sx0 + col_i * PIXEL_SIZE,
                    sy0 + row_i * PIXEL_SIZE,
                    PIXEL_SIZE,
                    PIXEL_SIZE,
                )
                pygame.draw.rect(self._pg_surface, color, rect)

    # ------------------------------------------------------------------
    # Rendering — hearts
    # ------------------------------------------------------------------

    def draw_hearts(self) -> None:
        for heart in self.hearts:
            if not heart.is_alive():
                continue
            size = max(8, heart.size)
            font = self._make_pg_font(size)
            surf = font.render("♥", True, (255, 77, 109))
            self._pg_surface.blit(surf, (int(heart.x), int(heart.y)))

    # ------------------------------------------------------------------
    # Rendering — sleep particles
    # ------------------------------------------------------------------

    def draw_sleep_particles(self) -> None:
        for p in self.sleep_texts:
            if not p.is_alive():
                continue
            size = max(10, p.size)
            font = self._make_pg_font(size)
            surf = font.render(p.text, True, (0, 0, 0))
            self._pg_surface.blit(surf, (int(p.x), int(p.y)))

    # ------------------------------------------------------------------
    # Rendering — flight trails
    # ------------------------------------------------------------------

    def draw_flight_trails(self) -> None:
        for p in self.flight_trails:
            if not p.is_alive():
                continue
            cx = int(p.screen_x - self.win_x)
            cy = int(p.screen_y - self.win_y)
            if (
                cx < -12
                or cx > WINDOW_WIDTH + 12
                or cy < -12
                or cy > WINDOW_HEIGHT + 12
            ):
                continue
            radius = max(1, int(p.radius * p.life))
            color = _hex_to_rgb(p.color)
            pygame.draw.circle(self._pg_surface, color, (cx, cy), radius)

    # ------------------------------------------------------------------
    # Rendering — slingshot string
    # ------------------------------------------------------------------

    def draw_slingshot_string(self) -> None:
        color = _slingshot_color_rgb()
        # Active pull
        if self.slingshot_active and (
            abs(self.slingshot_pull_x) > 2 or abs(self.slingshot_pull_y) > 2
        ):
            ax = int(self.slingshot_anchor_x - self.win_x)
            ay = int(self.slingshot_anchor_y - self.win_y)
            ex = ax + int(self.slingshot_pull_x)
            ey = ay + int(self.slingshot_pull_y)
            dist = math.sqrt(self.slingshot_pull_x**2 + self.slingshot_pull_y**2)
            ratio = min(dist / SLINGSHOT_MAX_PULL, 1.0)
            width = max(1, int(SLINGSHOT_STRING_WIDTH + ratio * 2))
            pygame.draw.line(self._pg_surface, color, (ax, ay), (ex, ey), width)
            return
        # Recoil animation
        if self.slingshot_recoil > 0:
            ax = int(self.slingshot_anchor_x - self.win_x)
            ay = int(self.slingshot_anchor_y - self.win_y)
            progress = self.slingshot_recoil / SLINGSHOT_RECOIL_STEPS
            ex = ax + int(self.slingshot_recoil_x * progress)
            ey = ay + int(self.slingshot_recoil_y * progress)
            pygame.draw.line(self._pg_surface, color, (ax, ay), (ex, ey), 1)
            self.slingshot_recoil -= 1

    # ------------------------------------------------------------------
    # Rendering — speech bubbles (PIL → pygame Surface)
    # ------------------------------------------------------------------

    def _pil_bubble(
        self,
        text: str,
        wrap_px: int,
        fill: tuple[int, int, int],
        outline: tuple[int, int, int],
        font_size: int = 13,
    ) -> pygame.Surface:
        """Render a chat bubble as a PIL image then convert to pygame Surface."""
        fp = _mac_font_path()
        try:
            pil_font = (
                ImageFont.truetype(str(fp), font_size)
                if fp
                else ImageFont.load_default()
            )
        except Exception:
            pil_font = ImageFont.load_default()

        # Measure text
        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        # word-wrap manually
        words = list(text)
        lines: list[str] = []
        current = ""
        for ch in text:
            test = current + ch
            bbox = d.textbbox((0, 0), test, font=pil_font)
            if bbox[2] - bbox[0] > wrap_px and current:
                lines.append(current)
                current = ch
            else:
                current = test
        if current:
            lines.append(current)

        line_h = font_size + 4
        text_w = max(
            (d.textbbox((0, 0), ln, font=pil_font)[2] for ln in lines),
            default=10,
        )
        text_h = line_h * len(lines)
        pad = 8
        w = text_w + pad * 2
        h = text_h + pad * 2

        img = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            [2, 2, w + 1, h + 1],
            radius=6,
            fill=(*fill, 230),
            outline=(*outline, 200),
            width=2,
        )
        for i, ln in enumerate(lines):
            draw.text(
                (pad + 2, pad + 2 + i * line_h),
                ln,
                font=pil_font,
                fill=(50, 50, 50, 255),
            )

        # PIL RGBA → pygame Surface
        raw = img.tobytes()
        surf = pygame.image.fromstring(raw, img.size, "RGBA").convert_alpha()
        return surf

    def draw_bubbles(self) -> None:
        self.bubbles = {k: v for k, v in self.bubbles.items() if v.is_alive()}
        if not self.bubbles:
            return

        pet_cx = int(self.pet_x + SPRITE_WIDTH / 2)
        pet_top = int(self.pet_y)

        chat = self.bubbles.get("chat")
        if chat:
            surf = self._pil_bubble(
                chat.text,
                CHAT_BUBBLE_WRAP_WIDTH,
                (255, 255, 255),
                (131, 131, 131),
            )
            bx = max(4, pet_cx - surf.get_width() // 2)
            by = max(4, pet_top - surf.get_height() - 8)
            self._pg_surface.blit(surf, (bx, by))
            # tail triangle
            tail_top = by + surf.get_height()
            pygame.draw.polygon(
                self._pg_surface,
                (255, 255, 255),
                [
                    (pet_cx - 6, tail_top),
                    (pet_cx, tail_top + 8),
                    (pet_cx + 6, tail_top),
                ],
            )

        pet_b = self.bubbles.get("pet")
        if pet_b:
            surf = self._pil_bubble(
                pet_b.text,
                PET_BUBBLE_WRAP_WIDTH,
                (240, 248, 255),
                (150, 180, 220),
                font_size=11,
            )
            bx = PET_BUBBLE_LEFT
            by = max(PET_BUBBLE_TOP_MIN, pet_top + PET_BUBBLE_TOP_OFFSET)
            self._pg_surface.blit(surf, (bx, by))

    # ------------------------------------------------------------------
    # Rendering — inline dialog overlay
    # ------------------------------------------------------------------

    def _draw_dialog(self) -> None:
        """Draw a simple text-input overlay inside the pygame window."""
        if not self._dialog_active:
            return
        # Background box
        bw, bh = 240, 44
        bx = int(self.pet_x + SPRITE_WIDTH + 4)
        by = int(self.pet_y + SPRITE_HEIGHT // 2 - bh // 2)
        bx = max(0, min(bx, WINDOW_WIDTH - bw - 4))
        by = max(0, min(by, WINDOW_HEIGHT - bh - 4))

        box_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        box_surf.fill((255, 255, 255, 220))
        pygame.draw.rect(
            box_surf, (191, 230, 201), box_surf.get_rect(), 2, border_radius=6
        )
        self._pg_surface.blit(box_surf, (bx, by))

        font = self._make_pg_font(11)
        display_text = self._dialog_text or ""
        caret = "|" if (int(time.time() * 2) % 2 == 0) else ""
        rendered = font.render(display_text + caret, True, (30, 58, 43))
        self._pg_surface.blit(rendered, (bx + 8, by + 12))

    # ------------------------------------------------------------------
    # Dialog open / close / submit  (override tkinter versions)
    # ------------------------------------------------------------------

    def open_dialog(self) -> None:
        self._dialog_active = True
        self._dialog_text = ""
        self._dialog_cursor = 0
        self.dialog_visible = True

    def close_dialog(self) -> None:
        self._dialog_active = False
        self._dialog_text = ""
        self.dialog_visible = False

    def position_dialog(self) -> None:
        pass  # drawn inline in _draw_dialog()

    def submit_dialog(self, _event=None) -> None:
        text = self._dialog_text.strip()
        if text:
            self.send_chat_message(text)
        self.close_dialog()

    # ------------------------------------------------------------------
    # macOS shortcut (replaces PowerShell .lnk helper)
    # ------------------------------------------------------------------

    def ensure_desktop_shortcut(self) -> bool:
        shortcut = Path.home() / "Desktop" / "GuguPet.command"
        launcher = _ROOT / "app" / "launcher_mac.py"
        try:
            shortcut.write_text(
                f"#!/bin/bash\ncd '{_ROOT}'\npython3 '{launcher}'\n",
                encoding="utf-8",
            )
            shortcut.chmod(0o755)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # root shim — parent business methods call self.root.after() /
    # self.root.after_cancel() at runtime (not just in __init__).
    # We keep self.root as a _FakeRoot so all these calls are silently
    # absorbed without crashing.  The pygame game loop drives timing.
    # ------------------------------------------------------------------

    # _FakeRoot is already set as self.root by the parent __init__ via
    # our monkey-patch.  We just need to make sure it stays there.
    # The property below makes self.root read-only and always returns
    # the fake, so no accidental reassignment can break things.

    # NOTE: Python doesn't support per-instance properties cleanly, so
    # we instead override the two methods that matter most at runtime:

    def _root_after(self, ms: int, fn=None, *args) -> int:
        """No-op replacement for tkinter root.after()."""
        return id(fn)  # fake job id

    def _root_after_cancel(self, job_id) -> None:
        """No-op replacement for tkinter root.after_cancel()."""
        pass

    # Patch the fake root at the end of __init__ (called after super().__init__)
    # — already done in __init__ via _FakeRoot, but guard here too.

    # ------------------------------------------------------------------
    # Event handling (pygame events replace tkinter bindings)
    # ------------------------------------------------------------------

    def _handle_pygame_events(self) -> bool:
        """Process all pending pygame events.  Returns False to quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                self._on_key(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._on_mouse_down(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._on_mouse_up(event)
            elif event.type == pygame.MOUSEMOTION:
                self._on_mouse_motion(event)
        return True

    def _on_key(self, event: pygame.event.Event) -> None:
        if not self._dialog_active:
            if event.key == pygame.K_RETURN:
                self.open_dialog()
            return
        # Dialog is open — handle text input
        if event.key == pygame.K_RETURN:
            self.submit_dialog()
        elif event.key == pygame.K_ESCAPE:
            self.close_dialog()
        elif event.key == pygame.K_BACKSPACE:
            self._dialog_text = self._dialog_text[:-1]
        else:
            ch = event.unicode
            if ch and ch.isprintable():
                self._dialog_text += ch

    def _on_mouse_down(self, event: pygame.event.Event) -> None:
        # Convert pygame window-local coords to screen coords
        screen_x = int(self.win_x) + event.pos[0]
        screen_y = int(self.win_y) + event.pos[1]

        if event.button == 1:  # left button

            class _Ev:
                x = event.pos[0]
                y = event.pos[1]
                x_root = screen_x
                y_root = screen_y

            self.on_click(_Ev())
            self._pg_drag_start_screen = (screen_x, screen_y)
            # Schedule single-click signal (240ms later, driven by tick loop)
            self._pg_single_click_at = time.time() + 0.24

        elif event.button == 3:  # right button

            class _Ev:
                x = event.pos[0]
                y = event.pos[1]
                x_root = screen_x
                y_root = screen_y

            self.on_slingshot_press(_Ev())
            self._pg_slingshot_mouse = (screen_x, screen_y)

        elif (
            event.button == pygame.BUTTON_LEFT and event.type == pygame.MOUSEBUTTONDOWN
        ):
            # Double-click detection handled via MOUSEBUTTONDOWN count
            pass

    def _on_mouse_up(self, event: pygame.event.Event) -> None:
        screen_x = int(self.win_x) + event.pos[0]
        screen_y = int(self.win_y) + event.pos[1]

        class _Ev:
            x = event.pos[0]
            y = event.pos[1]
            x_root = screen_x
            y_root = screen_y

        if event.button == 1:
            self.on_release(_Ev())
        elif event.button == 3:
            self.on_slingshot_release(_Ev())

    def _on_mouse_motion(self, event: pygame.event.Event) -> None:
        if not any(event.buttons):
            return
        screen_x = int(self.win_x) + event.pos[0]
        screen_y = int(self.win_y) + event.pos[1]

        class _Ev:
            x = event.pos[0]
            y = event.pos[1]
            x_root = screen_x
            y_root = screen_y

        if event.buttons[0]:  # left held → drag
            self.on_drag(_Ev())
            # Cancel pending single-click if user is actually dragging
            if abs(event.rel[0]) > 1 or abs(event.rel[1]) > 1:
                self._pg_single_click_at = 0.0
        if event.buttons[2]:  # right held → slingshot drag
            self.on_slingshot_drag(_Ev())

    # ------------------------------------------------------------------
    # Slingshot panic — replace root.after with a flag + counter
    # ------------------------------------------------------------------

    def _slingshot_panic_tick(self) -> None:
        """On macOS we just flip state; actual scheduling is in the game loop."""
        if not self.slingshot_active:
            return
        self.state = "fly" if self.state != "fly" else "sit"
        self.direction = 1 if random.random() > 0.5 else -1
        # Store next panic flip time instead of using root.after
        self._pg_next_panic_at = time.time() + SLINGSHOT_PANIC_INTERVAL / 1000.0

    # ------------------------------------------------------------------
    # Tick — one game-logic frame (override to remove root.after)
    # ------------------------------------------------------------------

    def tick(self) -> None:
        """Run one logic frame.  On macOS called directly from the game loop."""
        now = time.time()

        self.sync_brain_state(now)
        self.tick_bubble_queue(now)

        control = self.current_control()
        self.speed_scale = float(control.get("speed_scale", 1.0))
        self.physics_scale = float(control.get("physics_scale", 1.0))
        self.flight_speed_scale = float(control.get("flight_speed_scale", 1.0))
        self._anim_speed = float(control.get("anim_speed", 1.0))
        fps_target = float(control.get("fps_target", 62.0))
        self._tick_ms = max(8, int(1000.0 / fps_target))

        BASE_DT = 0.050
        if self._last_tick_ts > 0:
            real_dt = min(0.2, max(0.005, now - self._last_tick_ts))
            self._dt_scale = real_dt / BASE_DT
        else:
            self._dt_scale = self._tick_ms / 1000.0 / BASE_DT
        self._last_tick_ts = now

        self.anim_frame += self._dt_scale * self._anim_speed

        # Force-sleep logic (identical to Windows version)
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
                try:
                    raw = read_json(STATE_FILE, {})
                    raw["drives"] = {
                        "energy": 0.95,
                        "social": 0.90,
                        "curiosity": 0.88,
                        "comfort": 0.92,
                    }
                    write_json(STATE_FILE, raw)
                except Exception:
                    pass
                self.state = "stand"
                self.manual_awake_until = now + MANUAL_AWAKE_DURATION
                self.next_action_time = now + random.uniform(0.3, 0.8)
                self.set_bubble(
                    "chat",
                    random.choice(
                        ["好多了！精神满满～", "睡醒啦！", "咕咕！充好电了！"]
                    ),
                    duration=4.0,
                )

        command = self.current_command()
        self.apply_bounds_control(control)
        self.apply_floor_control(control)

        if control["mode"] == "frame":
            self.cancel_active_program("preview")
            self.apply_frame_preview(str(control["frame"]))
        else:
            self.dispatch_command(command, control)

        if self.active_program in {"fly_to", "fly_path", "hover", "follow_cursor"}:
            self.step_active_program()
        else:
            self.update_window_physics()
            if self.active_program:
                self.step_active_program()
            elif self.should_sleep(control):
                self.state = "sleep"
                self.next_action_time = now + 1.0
            else:
                if not self.update_first_launch_flow(now):
                    if self.state == "wake":
                        if now >= self.manual_awake_until - max(
                            0.0, MANUAL_AWAKE_DURATION - WAKE_SHAKE_DURATION
                        ):
                            self.state = "stand"
                            self.next_action_time = now + random.uniform(0.3, 0.8)
                    if self.state == "sleep":
                        self.state = "stand"
                        self.next_action_time = now + random.uniform(0.3, 0.8)
                    if self.state != "wake":
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

        for p in self.flight_trails:
            p.update()
        self.flight_trails = [p for p in self.flight_trails if p.is_alive()]

        self.pet_x = self.base_pet_x
        frame_to_draw = (
            str(control["frame"]) if control["mode"] == "frame" else self.frame_name()
        )
        self.pet_y = self.frame_top_y(frame_to_draw)

        # --- Slingshot panic scheduling (replaces root.after) ---
        if self.slingshot_active:
            if not hasattr(self, "_pg_next_panic_at"):
                self._pg_next_panic_at = now
            if now >= self._pg_next_panic_at:
                self._slingshot_panic_tick()

        # --- Single-click signal scheduling (replaces root.after 240ms) ---
        # Parent sets pending_single_click_job = root.after(240, commit_single_click_signal)
        # On mac root.after is a no-op; we drive it from here instead.
        if not hasattr(self, "_pg_single_click_at"):
            self._pg_single_click_at = 0.0
        if self._pg_single_click_at > 0 and now >= self._pg_single_click_at:
            self._pg_single_click_at = 0.0
            self.commit_single_click_signal()

        # --- Draw frame ---
        self._pg_surface.fill((0, 0, 0, 0))  # clear with transparent black

        self.draw_flight_trails()
        self.draw_pixel_art(frame_to_draw, self.pet_x, self.pet_y)

        for h in self.hearts:
            h.update()
        self.hearts = [h for h in self.hearts if h.is_alive()]
        self.draw_hearts()

        for p in self.sleep_texts:
            p.update()
        self.sleep_texts = [p for p in self.sleep_texts if p.is_alive()]
        self.draw_sleep_particles()

        self.draw_slingshot_string()

        if self.bubbles:
            self.draw_bubbles()

        self._draw_dialog()

        self.write_runtime_status(
            "preview" if control["mode"] == "frame" else self.command_state
        )
        if self.command_state == "completed":
            self.command_state = "idle"

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Main loop (replaces root.mainloop)
    # ------------------------------------------------------------------

    def run(self) -> None:
        running = True
        while running:
            running = self._handle_pygame_events()
            self.tick()
            self._pg_clock.tick(
                120
            )  # cap at 120 fps; tick() respects fps_target internally

        pygame.quit()

    # ------------------------------------------------------------------
    # Stub out tkinter-specific methods that would crash on macOS
    # ------------------------------------------------------------------

    def build_dialog_ui(self) -> None:
        """Parent builds tkinter widgets here; we do nothing — dialog is pygame overlay."""
        pass

    def update_dialog_layout(self) -> None:
        pass

    def open_history_panel(self) -> None:
        pass  # TODO: implement as separate tkinter window if desired

    def refresh_history_panel(self) -> None:
        pass

    def request_control_panel_chat(self) -> None:
        pass  # control panel handles this independently


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    instance = ensure_single_instance("main_mac")
    if instance:
        import threading

        def _run_brain() -> None:
            try:
                from brain.agent import run

                run()
            except Exception as exc:
                print(f"[brain] fatal: {exc}")

        threading.Thread(target=_run_brain, daemon=True, name="brain").start()
        DesktopPetMac().run()
