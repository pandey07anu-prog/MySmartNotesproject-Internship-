"""
Smart Notes Assistant - Notes Library View
Phase 8: Premium Native Windows Desktop Application

Comprehensive notes management workspace:
- Category chip filtering (All, Study, Money, Travel, Shopping)
- Dynamic client-side text filtering
- Sorting: Newest first, Oldest first, Category A-Z
- Grid / List layout switcher
- Responsive card rendering and dedicated empty states
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from src.gui.api_client import NotesApiClient
from src.gui.components import EmptyState, NoteCard
from src.gui.theme import CATEGORY_COLORS, PALETTE, get_font


class NotesView(ctk.CTkScrollableFrame):
    """
    Dedicated notes library view supporting category filtering, client-side filtering,
    sorting, and grid/list layout presentation.
    """

    def __init__(
        self,
        master: Any,
        api_client: NotesApiClient,
        on_open_editor: Callable[[Optional[Dict[str, Any]]], None],
        on_delete_note: Callable[[Dict[str, Any]], None],
        on_refresh: Callable[[], None],
        initial_category: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color="transparent",
            **kwargs
        )
        self.api_client = api_client
        self.on_open_editor = on_open_editor
        self.on_delete_note = on_delete_note
        self.on_refresh_requested = on_refresh
        self.active_category: Optional[str] = initial_category
        self.view_mode = "grid"  # "grid" or "list"
        self.sort_mode = "newest"

        self.all_notes: List[Dict[str, Any]] = []

        self._build_ui()

    def _build_ui(self) -> None:
        # Header Row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(28, 16))

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left")

        self.title_label = ctk.CTkLabel(
            title_col,
            text="All Notes" if not self.active_category else f"{self.active_category} Notes",
            font=get_font(24, weight="bold"),
            text_color=PALETTE["main_text"],
        )
        self.title_label.pack(side="left", padx=(0, 10))

        self.count_badge = ctk.CTkLabel(
            title_col,
            text="0 notes",
            font=get_font(12, weight="bold"),
            text_color=PALETTE["secondary_accent"],
            fg_color=PALETTE["secondary_bg"],
            corner_radius=8,
            width=65,
            height=26,
        )
        self.count_badge.pack(side="left")

        # Top Action Buttons
        btn_col = ctk.CTkFrame(header, fg_color="transparent")
        btn_col.pack(side="right")

        self.btn_add = ctk.CTkButton(
            btn_col,
            text="+ Add Note",
            font=get_font(12, weight="bold"),
            fg_color=PALETTE["primary_accent"],
            hover_color=PALETTE["primary_accent_hover"],
            text_color="#FFFFFF",
            corner_radius=8,
            height=34,
            command=lambda: self.on_open_editor(None),
        )
        self.btn_add.pack(side="right", padx=(8, 0))

        self.btn_refresh = ctk.CTkButton(
            btn_col,
            text="↻ Refresh",
            font=get_font(12),
            fg_color=PALETTE["card_bg"],
            hover_color=PALETTE["secondary_bg"],
            text_color=PALETTE["main_text"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=8,
            height=34,
            width=80,
            command=self.on_refresh_requested,
        )
        self.btn_refresh.pack(side="right")

        # Toolbar: Filter search box, Category Chips, Sort, View Toggle
        toolbar = ctk.CTkFrame(
            self,
            fg_color=PALETTE["card_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=12,
            height=50,
        )
        toolbar.pack(fill="x", padx=32, pady=(0, 20))

        # Filter Search Input
        self.filter_entry = ctk.CTkEntry(
            toolbar,
            placeholder_text="Filter notes by keyword...",
            font=get_font(12),
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=8,
            width=260,
            height=32,
        )
        self.filter_entry.pack(side="left", padx=(12, 12), pady=9)
        self.filter_entry.bind("<KeyRelease>", lambda e: self._render_notes())

        # Category Chips
        chips_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        chips_frame.pack(side="left", fill="y", pady=9)

        self.chip_buttons: Dict[str, ctk.CTkButton] = {}
        categories = ["All", "Study", "Money", "Travel", "Shopping"]
        for cat in categories:
            btn = ctk.CTkButton(
                chips_frame,
                text=cat,
                font=get_font(11, weight="bold"),
                fg_color="transparent",
                hover_color=PALETTE["secondary_bg"],
                text_color=PALETTE["secondary_text"],
                corner_radius=6,
                height=28,
                width=55,
                command=lambda c=cat: self._set_category_filter(c),
            )
            btn.pack(side="left", padx=2)
            self.chip_buttons[cat] = btn

        # Right Controls: Sorting and View Toggle
        right_ctrls = ctk.CTkFrame(toolbar, fg_color="transparent")
        right_ctrls.pack(side="right", padx=(0, 12), pady=9)

        # Sort Dropdown
        self.sort_menu = ctk.CTkOptionMenu(
            right_ctrls,
            values=["Newest first", "Oldest first", "Category A-Z"],
            font=get_font(11),
            fg_color=PALETTE["secondary_bg"],
            button_color=PALETTE["secondary_bg"],
            button_hover_color=PALETTE["card_hover"],
            text_color=PALETTE["main_text"],
            dropdown_fg_color=PALETTE["card_bg"],
            corner_radius=6,
            height=28,
            width=115,
            command=self._on_sort_changed,
        )
        self.sort_menu.pack(side="left", padx=(0, 10))

        # View Mode Toggle (Grid / List)
        self.btn_toggle_view = ctk.CTkSegmentedButton(
            right_ctrls,
            values=["Grid", "List"],
            font=get_font(11),
            selected_color=PALETTE["primary_accent"],
            selected_hover_color=PALETTE["primary_accent_hover"],
            unselected_color=PALETTE["secondary_bg"],
            unselected_hover_color=PALETTE["card_hover"],
            corner_radius=6,
            height=28,
            width=90,
            command=self._on_view_toggle,
        )
        self.btn_toggle_view.set("Grid")
        self.btn_toggle_view.pack(side="left")

        # Notes Cards Container
        self.cards_container = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_container.pack(fill="both", expand=True, padx=32, pady=(0, 32))
        self.cards_container.grid_columnconfigure((0, 1), weight=1)

    def set_active_category(self, category: Optional[str]) -> None:
        """Set active category from external navigation."""
        self.active_category = category
        cat_key = category if category in ("Study", "Money", "Travel", "Shopping") else "All"
        self._update_chip_styles(cat_key)
        self.title_label.configure(
            text="All Notes" if not category else f"{category} Notes"
        )
        self._render_notes()

    def _set_category_filter(self, cat: str) -> None:
        self.active_category = None if cat == "All" else cat
        self._update_chip_styles(cat)
        self.title_label.configure(
            text="All Notes" if not self.active_category else f"{self.active_category} Notes"
        )
        self._render_notes()

    def _update_chip_styles(self, active_cat: str) -> None:
        for cat, btn in self.chip_buttons.items():
            if cat == active_cat:
                btn.configure(
                    fg_color=PALETTE["primary_accent"],
                    text_color="#FFFFFF"
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=PALETTE["secondary_text"]
                )

    def _on_sort_changed(self, choice: str) -> None:
        if choice == "Newest first":
            self.sort_mode = "newest"
        elif choice == "Oldest first":
            self.sort_mode = "oldest"
        else:
            self.sort_mode = "category"
        self._render_notes()

    def _on_view_toggle(self, value: str) -> None:
        self.view_mode = value.lower()
        self._render_notes()

    def update_notes(self, notes: List[Dict[str, Any]]) -> None:
        """Receive updated notes collection from API client."""
        self.all_notes = notes
        active_cat = self.active_category or "All"
        self._update_chip_styles(active_cat)
        self._render_notes()

    def _render_notes(self) -> None:
        # Clear existing cards
        for child in self.cards_container.winfo_children():
            child.destroy()

        # 1. Category Filter
        filtered = list(self.all_notes)
        if self.active_category:
            filtered = [n for n in filtered if n.get("category") == self.active_category]

        # 2. Text Filter
        query = self.filter_entry.get().strip().lower()
        if query:
            filtered = [
                n for n in filtered
                if query in n.get("text", "").lower() or query in n.get("id", "").lower()
            ]

        # 3. Sorting
        if self.sort_mode == "newest":
            filtered.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        elif self.sort_mode == "oldest":
            filtered.sort(key=lambda x: x.get("updated_at", ""))
        elif self.sort_mode == "category":
            filtered.sort(key=lambda x: (x.get("category", ""), x.get("id", "")))

        # Update Count Badge
        self.count_badge.configure(text=f"{len(filtered)} note{'s' if len(filtered) != 1 else ''}")

        # Render Empty States or Cards
        if not filtered:
            if query:
                empty = EmptyState(
                    self.cards_container,
                    title="No Matching Notes",
                    description=f"No notes found matching '{query}'. Try another search query.",
                    icon="🔍",
                )
            elif self.active_category:
                empty = EmptyState(
                    self.cards_container,
                    title=f"No {self.active_category} Notes",
                    description=f"You haven't saved any notes in the {self.active_category} category yet.",
                    icon="📝",
                    action_text=f"+ Add {self.active_category} Note",
                    action_command=lambda: self.on_open_editor(None),
                )
            else:
                empty = EmptyState(
                    self.cards_container,
                    title="Your Library is Empty",
                    description="Create your first note to start building your personal knowledge base.",
                    icon="💡",
                    action_text="+ Create Your First Note",
                    action_command=lambda: self.on_open_editor(None),
                )
            empty.pack(fill="both", expand=True, pady=40)
            return

        # Render Cards (Grid or List)
        if self.view_mode == "grid":
            self.cards_container.grid_columnconfigure((0, 1), weight=1)
            for idx, note in enumerate(filtered):
                row = idx // 2
                col = idx % 2
                card = NoteCard(
                    self.cards_container,
                    note=note,
                    on_edit=self.on_open_editor,
                    on_delete=self.on_delete_note,
                    view_mode="grid",
                )
                padx = (0, 8) if col == 0 else (8, 0)
                card.grid(row=row, column=col, padx=padx, pady=8, sticky="nsew")
        else:
            for note in filtered:
                card = NoteCard(
                    self.cards_container,
                    note=note,
                    on_edit=self.on_open_editor,
                    on_delete=self.on_delete_note,
                    view_mode="list",
                )
                card.pack(fill="x", pady=6)

