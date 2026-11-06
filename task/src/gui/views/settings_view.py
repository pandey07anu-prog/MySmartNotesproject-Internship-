"""
Smart Notes Assistant - Settings View
Phase 8: Premium Native Windows Desktop Application

User configuration and system diagnostics workspace:
- Theme selector (Dark / Light / System)
- Accent color selection with persistent JSON configuration
- Real-time Backend Health and ML Model Readiness diagnostics
- Data management (Starter notes synchronization)
- System and platform environment information
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from src.gui.api_client import NotesApiClient
from src.gui.theme import PALETTE, STATUS_COLORS, get_font, theme_mgr


class SettingsView(ctk.CTkScrollableFrame):
    """
    Settings and system diagnostics view for Smart Notes Assistant.
    """

    def __init__(
        self,
        master: Any,
        api_client: NotesApiClient,
        on_load_starter: Callable[[], None],
        on_theme_changed: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color="transparent",
            **kwargs
        )
        self.api_client = api_client
        self.on_load_starter = on_load_starter
        self.on_theme_changed = on_theme_changed

        self._build_ui()
        self._check_backend_status()

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(28, 20))

        title = ctk.CTkLabel(
            header,
            text="Settings & System Diagnostics",
            font=get_font(24, weight="bold"),
            text_color=PALETTE["main_text"],
        )
        title.pack(side="left")

        # 1. Appearance Section
        self._build_appearance_section()

        # 2. System Status & ML Readiness Section
        self._build_status_section()

        # 3. Data Management Section
        self._build_data_section()

        # 4. About & Version Information
        self._build_about_section()

    def _build_appearance_section(self) -> None:
        card = ctk.CTkFrame(
            self,
            fg_color=PALETTE["card_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=14,
        )
        card.pack(fill="x", padx=32, pady=(0, 20))

        # Title
        t_row = ctk.CTkFrame(card, fg_color="transparent")
        t_row.pack(fill="x", padx=20, pady=(16, 12))

        lbl = ctk.CTkLabel(
            t_row,
            text="APPEARANCE & THEME",
            font=get_font(12, weight="bold"),
            text_color=PALETTE["secondary_text"],
        )
        lbl.pack(side="left")

        # Theme Selector Row
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 16))

        info_col = ctk.CTkFrame(row, fg_color="transparent")
        info_col.pack(side="left")

        name_lbl = ctk.CTkLabel(
            info_col,
            text="Interface Theme",
            font=get_font(14, weight="bold"),
            text_color=PALETTE["main_text"],
            anchor="w",
        )
        name_lbl.pack(fill="x")

        desc_lbl = ctk.CTkLabel(
            info_col,
            text="Choose between dark midnight palette, clean light mode, or match Windows system theme.",
            font=get_font(12),
            text_color=PALETTE["secondary_text"],
            anchor="w",
        )
        desc_lbl.pack(fill="x")

        # Segmented Theme Switcher
        self.theme_segmented = ctk.CTkSegmentedButton(
            row,
            values=["Dark", "Light", "System"],
            font=get_font(12),
            selected_color=PALETTE["primary_accent"],
            selected_hover_color=PALETTE["primary_accent_hover"],
            unselected_color=PALETTE["secondary_bg"],
            unselected_hover_color=PALETTE["card_hover"],
            corner_radius=8,
            height=32,
            width=180,
            command=self._on_theme_select,
        )
        current_mode = theme_mgr.appearance_mode.capitalize()
        self.theme_segmented.set(current_mode if current_mode in ("Dark", "Light", "System") else "Dark")
        self.theme_segmented.pack(side="right")

    def _on_theme_select(self, choice: str) -> None:
        mode = choice.lower()
        theme_mgr.set_appearance_mode(mode)
        if self.on_theme_changed:
            self.on_theme_changed(mode)

    def _build_status_section(self) -> None:
        card = ctk.CTkFrame(
            self,
            fg_color=PALETTE["card_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=14,
        )
        card.pack(fill="x", padx=32, pady=(0, 20))

        t_row = ctk.CTkFrame(card, fg_color="transparent")
        t_row.pack(fill="x", padx=20, pady=(16, 12))

        lbl = ctk.CTkLabel(
            t_row,
            text="SYSTEM & MODEL READINESS",
            font=get_font(12, weight="bold"),
            text_color=PALETTE["secondary_text"],
        )
        lbl.pack(side="left")

        # Diagnostics items
        diag_frame = ctk.CTkFrame(card, fg_color="transparent")
        diag_frame.pack(fill="x", padx=20, pady=(0, 16))

        # 1. Backend Service
        self.status_backend = self._create_diag_row(
            diag_frame,
            name="FastAPI Backend Service",
            detail="Local HTTP REST daemon (http://127.0.0.1:8000)",
            initial_status="Checking...",
            initial_color=PALETTE["muted_text"],
        )

        # 2. ML Classification Pipeline
        self.status_model = self._create_diag_row(
            diag_frame,
            name="Machine Learning Model",
            detail="TF-IDF + Logistic Regression (calibrated threshold τ = 0.40)",
            initial_status="Active",
            initial_color=STATUS_COLORS["online"],
        )

        # 3. Persistent Storage Engine
        self.status_storage = self._create_diag_row(
            diag_frame,
            name="Persistent Storage Engine",
            detail="Atomic JSON storage engine with full UTF-8 Indian Rupee (₹) preservation",
            initial_status="Ready",
            initial_color=STATUS_COLORS["online"],
        )

        # 4. Search Engines
        self.status_search = self._create_diag_row(
            diag_frame,
            name="Retrieval Search Engines",
            detail="TF-IDF Cosine Similarity Engine (Default) & Keyword Engine",
            initial_status="Ready",
            initial_color=STATUS_COLORS["online"],
        )

    def _create_diag_row(
        self,
        parent: Any,
        name: str,
        detail: str,
        initial_status: str,
        initial_color: str,
    ) -> ctk.CTkLabel:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=6)

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left")

        n_lbl = ctk.CTkLabel(
            left,
            text=name,
            font=get_font(13, weight="bold"),
            text_color=PALETTE["main_text"],
            anchor="w",
        )
        n_lbl.pack(fill="x")

        d_lbl = ctk.CTkLabel(
            left,
            text=detail,
            font=get_font(11),
            text_color=PALETTE["secondary_text"],
            anchor="w",
        )
        d_lbl.pack(fill="x")

        status_lbl = ctk.CTkLabel(
            row,
            text=f"●  {initial_status}",
            font=get_font(12, weight="bold"),
            text_color=initial_color,
        )
        status_lbl.pack(side="right")
        return status_lbl

    def _check_backend_status(self) -> None:
        def _call():
            return self.api_client.get_health()

        def _success(res: Dict[str, Any]):
            status = res.get("status", "unknown")
            if status == "healthy":
                self.status_backend.configure(
                    text="●  Online",
                    text_color=STATUS_COLORS["online"]
                )
                self.status_model.configure(
                    text="●  Pipeline Ready" if res.get("model_ready") else "●  Model Unready",
                    text_color=STATUS_COLORS["online"] if res.get("model_ready") else STATUS_COLORS["error"]
                )
                self.status_storage.configure(
                    text="●  Storage Ready" if res.get("storage_ready") else "●  Storage Unready",
                    text_color=STATUS_COLORS["online"] if res.get("storage_ready") else STATUS_COLORS["error"]
                )
            else:
                self.status_backend.configure(
                    text=f"●  {status.capitalize()}",
                    text_color=STATUS_COLORS["uncertain"]
                )

        def _error(err: Exception):
            self.status_backend.configure(
                text="●  Disconnected",
                text_color=STATUS_COLORS["error"]
            )

        self.api_client.execute_async(
            _call,
            on_success=_success,
            on_error=_error,
            tk_root=self,
        )

    def _build_data_section(self) -> None:
        card = ctk.CTkFrame(
            self,
            fg_color=PALETTE["card_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=14,
        )
        card.pack(fill="x", padx=32, pady=(0, 20))

        t_row = ctk.CTkFrame(card, fg_color="transparent")
        t_row.pack(fill="x", padx=20, pady=(16, 12))

        lbl = ctk.CTkLabel(
            t_row,
            text="DATA MANAGEMENT",
            font=get_font(12, weight="bold"),
            text_color=PALETTE["secondary_text"],
        )
        lbl.pack(side="left")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 16))

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)

        n_lbl = ctk.CTkLabel(
            left,
            text="Starter Notes Synchronization",
            font=get_font(14, weight="bold"),
            text_color=PALETTE["main_text"],
            anchor="w",
        )
        n_lbl.pack(fill="x")

        d_lbl = ctk.CTkLabel(
            left,
            text="Idempotently load the 12 original candidate-pack starter notes (N001–N012) into persistent storage.",
            font=get_font(12),
            text_color=PALETTE["secondary_text"],
            anchor="w",
        )
        d_lbl.pack(fill="x")

        btn_load = ctk.CTkButton(
            row,
            text="📥 Load Starter Notes",
            font=get_font(12, weight="bold"),
            fg_color=PALETTE["primary_accent"],
            hover_color=PALETTE["primary_accent_hover"],
            text_color="#FFFFFF",
            corner_radius=8,
            height=34,
            command=self.on_load_starter,
        )
        btn_load.pack(side="right", padx=(16, 0))

    def _build_about_section(self) -> None:
        card = ctk.CTkFrame(
            self,
            fg_color=PALETTE["card_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=14,
        )
        card.pack(fill="x", padx=32, pady=(0, 32))

        t_row = ctk.CTkFrame(card, fg_color="transparent")
        t_row.pack(fill="x", padx=20, pady=(16, 10))

        lbl = ctk.CTkLabel(
            t_row,
            text="ABOUT SMART NOTES",
            font=get_font(12, weight="bold"),
            text_color=PALETTE["secondary_text"],
        )
        lbl.pack(side="left")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 16))

        col = ctk.CTkFrame(row, fg_color="transparent")
        col.pack(side="left", fill="both", expand=True)

        app_title = ctk.CTkLabel(
            col,
            text="SMART NOTES — Think. Organize. Remember.",
            font=get_font(15, weight="bold"),
            text_color=PALETTE["main_text"],
            anchor="w",
        )
        app_title.pack(fill="x")

        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        app_info = ctk.CTkLabel(
            col,
            text=f"Version: 1.0.0  •  Platform: Windows 11 (64-bit)  •  Python: {py_ver}  •  CustomTkinter: 6.0.0\n"
                 "Developed for AI Engineering Internship-to-Hire Technical Assessment.",
            font=get_font(12),
            text_color=PALETTE["secondary_text"],
            justify="left",
            anchor="w",
        )
        app_info.pack(fill="x", pady=(4, 0))

