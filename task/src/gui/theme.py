"""
Smart Notes Assistant - GUI Theme & Styling System
Phase 8: Premium Native Windows Desktop Application

Defines the brand identity, color palettes (Dark & Light), category colors,
typography hierarchies, and configuration persistence for SMART NOTES.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import customtkinter as ctk

from src.data_ingestion import get_project_root


# ---------------------------------------------------------------------------
# Color Definitions
# ---------------------------------------------------------------------------
# Format: (Light mode color, Dark mode color) for CustomTkinter dynamic binding
PALETTE = {
    "main_bg": ("#F5F4FA", "#151625"),
    "sidebar_bg": ("#FFFFFF", "#191A2C"),
    "secondary_bg": ("#EFEDF7", "#202237"),
    "card_bg": ("#FFFFFF", "#252940"),
    "card_hover": ("#F0EDFA", "#2D314D"),
    "primary_accent": ("#7966D8", "#927FEA"),
    "primary_accent_hover": ("#6855C6", "#A594F9"),
    "secondary_accent": ("#927FEA", "#B0A2FF"),
    "main_text": ("#242438", "#F6F5FB"),
    "secondary_text": ("#77778D", "#A5A6BC"),
    "muted_text": ("#9D9DAE", "#71738E"),
    "border": ("#E6E3F0", "#353750"),
    "border_focus": ("#7966D8", "#927FEA"),
    "input_bg": ("#FFFFFF", "#1D1E30"),
}

CATEGORY_COLORS: Dict[str, str] = {
    "Study": "#A78BFA",      # Soft Purple
    "Money": "#6CCFA8",      # Mint / Emerald
    "Travel": "#78B9F5",     # Sky Blue
    "Shopping": "#F08F9A",   # Rose / Coral
}

CATEGORY_BG_TINTS: Dict[str, Tuple[str, str]] = {
    "Study": ("#F3EEFF", "#28233D"),
    "Money": ("#EAF7F2", "#1E332A"),
    "Travel": ("#EFF6FF", "#1D2B3D"),
    "Shopping": ("#FDF2F4", "#3D2228"),
}

STATUS_COLORS = {
    "uncertain": "#F59E0B",         # Amber
    "uncertain_bg": ("#FEF3C7", "#3B2D18"),
    "success": "#10B981",           # Emerald
    "success_bg": ("#D1FAE5", "#163327"),
    "error": "#EF4444",             # Rose Red
    "error_bg": ("#FEE2E2", "#3B1818"),
    "online": "#10B981",
    "offline": "#EF4444",
}


# ---------------------------------------------------------------------------
# Typography Specifications (Segoe UI)
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"

def get_font(size: int = 14, weight: str = "normal", slant: str = "roman") -> ctk.CTkFont:
    """Return a consistent CTkFont instance."""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight, slant=slant)


class ThemeManager:
    """
    Manages persistent user preferences (theme, accent) and notifies registered
    observers upon theme modification.
    """

    DEFAULT_CONFIG = {
        "appearance_mode": "dark",  # "dark", "light", "system"
        "color_theme": "dark-blue",
        "accent_color": "#927FEA",
    }

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            project_root = get_project_root()
            self.config_path = project_root / "data" / "app_config.json"
        else:
            self.config_path = Path(config_path)

        self._callbacks: list[Callable[[str], None]] = []
        self.config = self._load_config()
        self._apply_appearance_mode(self.config["appearance_mode"])

    def _load_config(self) -> dict[str, Any]:
        """Safely load user configuration or fall back to default."""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    cfg = dict(self.DEFAULT_CONFIG)
                    cfg.update({k: v for k, v in data.items() if k in self.DEFAULT_CONFIG})
                    return cfg
            except Exception:
                pass
        return dict(self.DEFAULT_CONFIG)

    def save_config(self) -> None:
        """Persist current preferences to disk."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(self.config, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def _apply_appearance_mode(self, mode: str) -> None:
        """Configure CustomTkinter global appearance mode."""
        clean_mode = mode.lower()
        if clean_mode in ("dark", "light", "system"):
            ctk.set_appearance_mode(clean_mode)

    @property
    def appearance_mode(self) -> str:
        return self.config.get("appearance_mode", "dark")

    def set_appearance_mode(self, mode: str) -> None:
        """Update and persist appearance mode."""
        clean_mode = mode.lower()
        if clean_mode not in ("dark", "light", "system"):
            clean_mode = "dark"
        self.config["appearance_mode"] = clean_mode
        self._apply_appearance_mode(clean_mode)
        self.save_config()
        for cb in self._callbacks:
            try:
                cb(clean_mode)
            except Exception:
                pass

    def register_callback(self, cb: Callable[[str], None]) -> None:
        """Register a subscriber to theme changes."""
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[str], None]) -> None:
        if cb in self._callbacks:
            self._callbacks.remove(cb)

    @classmethod
    def get_color(cls, key: str, is_dark: Optional[bool] = None) -> str:
        """Resolve a color string based on dark/light context."""
        val = PALETTE.get(key)
        if val is None:
            return "#927FEA"
        if isinstance(val, tuple):
            if is_dark is None:
                current_mode = ctk.get_appearance_mode().lower()
                is_dark = (current_mode == "dark")
            return val[1] if is_dark else val[0]
        return str(val)


# Global singleton theme manager instance
theme_mgr = ThemeManager()

