"""
Smart Notes Assistant - Main Native Desktop Application Window
Phase 8: Premium Native Windows Desktop Application

The central application shell coordinating:
- Navigation sidebar with active state tracking and category note count badges
- Views: Dashboard, All Notes, Category Views (Study, Money, Travel, Shopping), Search, Settings
- Floating toast notification banner for feedback
- Global keyboard shortcuts (Ctrl+N, Ctrl+F, Ctrl+S, Esc)
- Threaded API data synchronization
- Graceful lifecycle management and clean child process shutdown
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import customtkinter as ctk
from PIL import Image

from src.data_ingestion import get_project_root
from src.gui.api_client import NotesApiClient
from src.gui.backend_manager import BackendLifecycleManager
from src.gui.components import ConfirmDialog, SidebarNavItem
from src.gui.theme import (
    CATEGORY_COLORS,
    PALETTE,
    STATUS_COLORS,
    get_font,
    theme_mgr,
)
from src.gui.views import (
    DashboardView,
    NoteEditorDialog,
    NotesView,
    SearchView,
    SettingsView,
)


class SmartNotesApp(ctk.CTk):
    """
    Main CustomTkinter window for SMART NOTES desktop productivity assistant.
    """

    APP_TITLE = "SMART NOTES — Think. Organize. Remember."
    INITIAL_WIDTH = 1350
    INITIAL_HEIGHT = 850
    MIN_WIDTH = 1050
    MIN_HEIGHT = 650

    def __init__(
        self,
        api_client: Optional[NotesApiClient] = None,
        backend_manager: Optional[BackendLifecycleManager] = None,
    ):
        super().__init__()

        self.project_root = get_project_root()
        self.backend_manager = backend_manager or BackendLifecycleManager(project_root=self.project_root)
        self.api_client = api_client or NotesApiClient()

        self.title(self.APP_TITLE)
        self.geometry(f"{self.INITIAL_WIDTH}x{self.INITIAL_HEIGHT}")
        self.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # Set window icon
        self._setup_window_icon()

        # Configure root grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)  # Sidebar (fixed 240px)
        self.grid_columnconfigure(1, weight=1)  # Main Content (fluid)

        self.configure(fg_color=PALETTE["main_bg"])

        # State
        self.notes: List[Dict[str, Any]] = []
        self.active_page = "Dashboard"
        self._toast_timer: Optional[str] = None

        # Build Shell
        self._build_sidebar()
        self._build_content_area()
        self._build_toast_banner()

        # Bind Global Shortcuts
        self.bind("<Control-n>", lambda e: self.open_note_editor(None))
        self.bind("<Control-f>", lambda e: self.navigate_to("Search", focus_search=True))

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Initial navigation & data sync
        self.navigate_to("Dashboard")
        self.refresh_all_notes()

    def _setup_window_icon(self) -> None:
        """Load and set custom application icon."""
        try:
            ico_path = self.project_root / "assets" / "app_icon.ico"
            if ico_path.exists():
                self.iconbitmap(str(ico_path))
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Sidebar Navigation Shell
    # -----------------------------------------------------------------------
    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0,
            fg_color=PALETTE["sidebar_bg"],
            border_color=PALETTE["border"],
            border_width=1,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1)  # Navigation expands
        self.sidebar.grid_propagate(False)

        # 1. Brand Area
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=20, pady=(24, 16), sticky="ew")

        # Logo Icon
        logo_icon = ctk.CTkLabel(
            brand_frame,
            text="✨",
            font=get_font(20),
            text_color=PALETTE["primary_accent"],
        )
        logo_icon.pack(side="left", padx=(0, 10))

        title_col = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_col.pack(side="left")

        app_name = ctk.CTkLabel(
            title_col,
            text="SMART NOTES",
            font=get_font(16, weight="bold"),
            text_color=PALETTE["main_text"],
            anchor="w",
        )
        app_name.pack(fill="x")

        app_tagline = ctk.CTkLabel(
            title_col,
            text="Think. Organize. Remember.",
            font=get_font(10),
            text_color=PALETTE["muted_text"],
            anchor="w",
        )
        app_tagline.pack(fill="x")

        # 2. Prominent + Add Note Action
        btn_new_note = ctk.CTkButton(
            self.sidebar,
            text="+ Add Note",
            font=get_font(13, weight="bold"),
            fg_color=PALETTE["primary_accent"],
            hover_color=PALETTE["primary_accent_hover"],
            text_color="#FFFFFF",
            corner_radius=10,
            height=38,
            command=lambda: self.open_note_editor(None),
        )
        btn_new_note.grid(row=1, column=0, padx=16, pady=(0, 20), sticky="ew")

        # 3. Navigation List Frame
        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.grid(row=2, column=0, padx=12, pady=0, sticky="nsew")

        self.nav_items: Dict[str, SidebarNavItem] = {}

        # Main Section
        self._add_nav_item("Dashboard", "📊", lambda: self.navigate_to("Dashboard"))
        self._add_nav_item("All Notes", "📚", lambda: self.navigate_to("All Notes"))
        self._add_nav_item("Search", "🔍", lambda: self.navigate_to("Search"))

        # Category Section Separator
        cat_sep_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        cat_sep_frame.pack(fill="x", padx=10, pady=(16, 6))

        cat_lbl = ctk.CTkLabel(
            cat_sep_frame,
            text="CATEGORIES",
            font=get_font(10, weight="bold"),
            text_color=PALETTE["muted_text"],
        )
        cat_lbl.pack(side="left")

        # Category Nav Items
        self._add_nav_item("Study", "●", lambda: self.navigate_to("Study"), is_category=True, category_name="Study")
        self._add_nav_item("Money", "●", lambda: self.navigate_to("Money"), is_category=True, category_name="Money")
        self._add_nav_item("Travel", "●", lambda: self.navigate_to("Travel"), is_category=True, category_name="Travel")
        self._add_nav_item("Shopping", "●", lambda: self.navigate_to("Shopping"), is_category=True, category_name="Shopping")

        # Settings
        self._add_nav_item("Settings", "⚙️", lambda: self.navigate_to("Settings"))

        # 4. Bottom Area: Backend indicator & Theme Switcher
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="sew")

        # Connection status pill
        conn_frame = ctk.CTkFrame(
            bottom_frame,
            fg_color=PALETTE["secondary_bg"],
            corner_radius=8,
            height=30,
        )
        conn_frame.pack(fill="x", pady=(0, 10))

        self.conn_dot = ctk.CTkLabel(
            conn_frame,
            text="●",
            font=get_font(12),
            text_color=STATUS_COLORS["online"],
        )
        self.conn_dot.pack(side="left", padx=(10, 4), pady=4)

        self.conn_text = ctk.CTkLabel(
            conn_frame,
            text="Backend Active",
            font=get_font(11, weight="bold"),
            text_color=PALETTE["secondary_text"],
        )
        self.conn_text.pack(side="left", pady=4)

        # Version text
        ver_lbl = ctk.CTkLabel(
            bottom_frame,
            text="v1.0.0 • Python 3.10",
            font=get_font(10),
            text_color=PALETTE["muted_text"],
        )
        ver_lbl.pack(fill="x")

    def _add_nav_item(
        self,
        name: str,
        icon: str,
        cmd: Any,
        is_category: bool = False,
        category_name: Optional[str] = None,
    ) -> None:
        item = SidebarNavItem(
            self.nav_frame,
            label=name,
            icon=icon,
            command=cmd,
            is_category=is_category,
            category_name=category_name,
        )
        item.pack(fill="x", pady=2)
        self.nav_items[name] = item

    # -----------------------------------------------------------------------
    # Content Area & View Switcher
    # -----------------------------------------------------------------------
    def _build_content_area(self) -> None:
        self.content_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Initialize Views
        self.views: Dict[str, Any] = {
            "Dashboard": DashboardView(
                self.content_frame,
                api_client=self.api_client,
                on_open_editor=self.open_note_editor,
                on_navigate=self.navigate_to,
                on_delete_note=self.prompt_delete_note,
                on_load_starter=self.load_starter_notes,
            ),
            "Notes": NotesView(
                self.content_frame,
                api_client=self.api_client,
                on_open_editor=self.open_note_editor,
                on_delete_note=self.prompt_delete_note,
                on_refresh=self.refresh_all_notes,
            ),
            "Search": SearchView(
                self.content_frame,
                api_client=self.api_client,
                on_open_note=self.open_note_editor,
            ),
            "Settings": SettingsView(
                self.content_frame,
                api_client=self.api_client,
                on_load_starter=self.load_starter_notes,
                on_theme_changed=self._on_theme_changed,
            ),
        }

    def navigate_to(self, page_name: str, focus_search: bool = False) -> None:
        """Switch active view in content container."""
        # Update Nav Item Styles
        for name, item in self.nav_items.items():
            item.set_active(name == page_name)

        self.active_page = page_name

        # Hide all views
        for view in self.views.values():
            view.grid_forget()

        # Display target view
        if page_name == "Dashboard":
            self.views["Dashboard"].grid(row=0, column=0, sticky="nsew")
            self.views["Dashboard"].refresh_data(self.notes)
        elif page_name in ("All Notes", "Study", "Money", "Travel", "Shopping"):
            target_cat = None if page_name == "All Notes" else page_name
            self.views["Notes"].set_active_category(target_cat)
            self.views["Notes"].grid(row=0, column=0, sticky="nsew")
        elif page_name == "Search":
            self.views["Search"].grid(row=0, column=0, sticky="nsew")
            if focus_search:
                self.views["Search"].focus_search()
        elif page_name == "Settings":
            self.views["Settings"].grid(row=0, column=0, sticky="nsew")

    # -----------------------------------------------------------------------
    # Toast Notification System
    # -----------------------------------------------------------------------
    def _build_toast_banner(self) -> None:
        self.toast_banner = ctk.CTkFrame(
            self,
            fg_color=PALETTE["secondary_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=10,
            height=40,
        )
        self.toast_label = ctk.CTkLabel(
            self.toast_banner,
            text="",
            font=get_font(12, weight="bold"),
            text_color=PALETTE["main_text"],
        )
        self.toast_label.pack(side="left", padx=16, pady=8)

    def show_toast(self, message: str, is_error: bool = False, duration_ms: int = 3500) -> None:
        """Display a floating notification banner for user feedback."""
        if self._toast_timer:
            self.after_cancel(self._toast_timer)

        border_col = STATUS_COLORS["error"] if is_error else PALETTE["primary_accent"]
        self.toast_banner.configure(border_color=border_col)
        self.toast_label.configure(
            text=message,
            text_color=STATUS_COLORS["error"] if is_error else PALETTE["main_text"]
        )

        # Place at top right
        self.toast_banner.place(relx=0.98, rely=0.03, anchor="ne")

        def _hide():
            self.toast_banner.place_forget()

        self._toast_timer = self.after(duration_ms, _hide)

    # -----------------------------------------------------------------------
    # Data Synchronization & Note CRUD
    # -----------------------------------------------------------------------
    def refresh_all_notes(self) -> None:
        """Fetch saved notes from backend daemon on background thread."""
        def _call():
            return self.api_client.get_notes()

        def _success(notes: List[Dict[str, Any]]):
            self.notes = notes
            self._update_badges(notes)
            self.views["Dashboard"].refresh_data(notes)
            self.views["Notes"].update_notes(notes)
            self.conn_dot.configure(text_color=STATUS_COLORS["online"])
            self.conn_text.configure(text="Backend Active")

        def _error(err: Exception):
            self.conn_dot.configure(text_color=STATUS_COLORS["error"])
            self.conn_text.configure(text="Backend Offline")
            self.show_toast(f"Failed to sync with backend: {getattr(err, 'detail', err)}", is_error=True)

        self.api_client.execute_async(
            _call,
            on_success=_success,
            on_error=_error,
            tk_root=self,
        )

    def _update_badges(self, notes: List[Dict[str, Any]]) -> None:
        """Update category note count badges in the sidebar."""
        all_count = len(notes)
        counts = {
            "All Notes": all_count,
            "Study": sum(1 for n in notes if n.get("category") == "Study"),
            "Money": sum(1 for n in notes if n.get("category") == "Money"),
            "Travel": sum(1 for n in notes if n.get("category") == "Travel"),
            "Shopping": sum(1 for n in notes if n.get("category") == "Shopping"),
        }
        for nav_name, count in counts.items():
            if nav_name in self.nav_items:
                self.nav_items[nav_name].set_badge(count)

    def open_note_editor(self, note: Optional[Dict[str, Any]] = None) -> None:
        """Open modal dialog to create or edit note."""
        def _on_save_success(saved_note: Dict[str, Any]):
            note_id = saved_note.get("id", "")
            action = "updated" if note else "created"
            self.show_toast(f"Note {note_id} {action} successfully!")
            self.refresh_all_notes()

        NoteEditorDialog(
            parent=self,
            api_client=self.api_client,
            note=note,
            on_save_success=_on_save_success,
        )

    def prompt_delete_note(self, note: Dict[str, Any]) -> None:
        """Show confirmation dialog before deleting note."""
        note_id = note.get("id", "")
        text_snippet = note.get("text", "")[:60]

        def _execute_delete():
            def _call():
                return self.api_client.delete_note(note_id)

            def _success(res: Dict[str, Any]):
                self.show_toast(f"Note {note_id} deleted successfully.")
                self.refresh_all_notes()

            def _error(err: Exception):
                err_msg = str(getattr(err, "detail", err))
                self.show_toast(f"Failed to delete note {note_id}: {err_msg}", is_error=True)

            self.api_client.execute_async(
                _call,
                on_success=_success,
                on_error=_error,
                tk_root=self,
            )

        ConfirmDialog(
            parent=self,
            title="Delete Note",
            message=f"Are you sure you want to delete note {note_id}?\n\n\"{text_snippet}...\"\n\nThis action cannot be undone.",
            confirm_text="Delete",
            cancel_text="Cancel",
            is_destructive=True,
            on_confirm=_execute_delete,
        )

    def load_starter_notes(self) -> None:
        """Idempotently import the 12 candidate-pack starter notes."""
        def _call():
            return self.api_client.load_starter_notes()

        def _success(res: Dict[str, Any]):
            count = res.get("loaded_count", 0)
            if count > 0:
                self.show_toast(f"Successfully loaded {count} starter notes!")
            else:
                self.show_toast("Starter notes are already loaded.")
            self.refresh_all_notes()

        def _error(err: Exception):
            err_msg = str(getattr(err, "detail", err))
            self.show_toast(f"Starter notes: {err_msg}", is_error=True)

        self.api_client.execute_async(
            _call,
            on_success=_success,
            on_error=_error,
            tk_root=self,
        )

    def _on_theme_changed(self, mode: str) -> None:
        """Handle theme change propagation."""
        self.configure(fg_color=PALETTE["main_bg"])
        self.sidebar.configure(
            fg_color=PALETTE["sidebar_bg"],
            border_color=PALETTE["border"]
        )

    # -----------------------------------------------------------------------
    # Application Shutdown
    # -----------------------------------------------------------------------
    def _on_window_close(self) -> None:
        """Safely close HTTP connection pool and terminate child process."""
        try:
            self.api_client.close()
        except Exception:
            pass

        try:
            self.backend_manager.stop()
        except Exception:
            pass

        self.destroy()

