"""
Smart Notes Assistant - Dashboard Command Center View
Phase 8: Premium Native Windows Desktop Application

The primary visual experience:
- Time-aware greeting & date display
- Dynamic statistics cards (Total, Study, Money, Travel, Shopping)
- Category distribution visualization
- Recent notes stream with honest uncertainty indicators
- Clean empty states and quick actions
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from src.gui.api_client import NotesApiClient
from src.gui.components import (
    CategoryDistributionBar,
    EmptyState,
    NoteCard,
    StatCard,
)
from src.gui.theme import CATEGORY_COLORS, PALETTE, get_font


class DashboardView(ctk.CTkScrollableFrame):
    """
    Main dashboard command center showing overview metrics, recent activity,
    and proportional category distribution.
    """

    def __init__(
        self,
        master: Any,
        api_client: NotesApiClient,
        on_open_editor: Callable[[Optional[Dict[str, Any]]], None],
        on_navigate: Callable[[str], None],
        on_delete_note: Callable[[Dict[str, Any]], None],
        on_load_starter: Callable[[], None],
        **kwargs
    ):
        super().__init__(
            master,
            fg_color="transparent",
            **kwargs
        )
        self.api_client = api_client
        self.on_open_editor = on_open_editor
        self.on_navigate = on_navigate
        self.on_delete_note = on_delete_note
        self.on_load_starter = on_load_starter

        self.notes: List[Dict[str, Any]] = []

        self._build_ui()

    def _get_greeting(self) -> str:
        hour = datetime.now().hour
        if hour < 12:
            return "Good morning"
        elif hour < 17:
            return "Good afternoon"
        else:
            return "Good evening"

    def _build_ui(self) -> None:
        # 1. Welcome & Quick Actions Section
        welcome_frame = ctk.CTkFrame(self, fg_color="transparent")
        welcome_frame.pack(fill="x", padx=32, pady=(28, 20))

        # Text column
        text_col = ctk.CTkFrame(welcome_frame, fg_color="transparent")
        text_col.pack(side="left", fill="both", expand=True)

        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        self.date_label = ctk.CTkLabel(
            text_col,
            text=f"{self._get_greeting()}  •  {date_str}",
            font=get_font(13, weight="bold"),
            text_color=PALETTE["secondary_accent"],
            anchor="w",
        )
        self.date_label.pack(fill="x")

        self.title_label = ctk.CTkLabel(
            text_col,
            text="Personal Notes Command Center",
            font=get_font(26, weight="bold"),
            text_color=PALETTE["main_text"],
            anchor="w",
        )
        self.title_label.pack(fill="x", pady=(2, 0))

        subtitle = ctk.CTkLabel(
            text_col,
            text="Intelligent note classification, confidence estimation, and fast retrieval.",
            font=get_font(13),
            text_color=PALETTE["secondary_text"],
            anchor="w",
        )
        subtitle.pack(fill="x")

        # Quick action buttons on right
        actions_col = ctk.CTkFrame(welcome_frame, fg_color="transparent")
        actions_col.pack(side="right", padx=(16, 0))

        self.btn_new = ctk.CTkButton(
            actions_col,
            text="+ Add Note",
            font=get_font(13, weight="bold"),
            fg_color=PALETTE["primary_accent"],
            hover_color=PALETTE["primary_accent_hover"],
            text_color="#FFFFFF",
            corner_radius=10,
            height=38,
            width=120,
            command=lambda: self.on_open_editor(None),
        )
        self.btn_new.pack(side="right", padx=(8, 0))

        self.btn_search = ctk.CTkButton(
            actions_col,
            text="🔍 Search",
            font=get_font(12),
            fg_color=PALETTE["card_bg"],
            hover_color=PALETTE["secondary_bg"],
            text_color=PALETTE["main_text"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=10,
            height=38,
            width=100,
            command=lambda: self.on_navigate("Search"),
        )
        self.btn_search.pack(side="right")

        # 2. Statistics Grid (5 Cards: Total, Study, Money, Travel, Shopping)
        self.stats_grid = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_grid.pack(fill="x", padx=32, pady=(0, 24))
        for i in range(5):
            self.stats_grid.grid_columnconfigure(i, weight=1)

        self.card_total = StatCard(
            self.stats_grid,
            title="Total Notes",
            count=0,
            icon="📚",
            accent_color=PALETTE["primary_accent"],
            subtitle="Saved in library",
        )
        self.card_total.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        self.card_study = StatCard(
            self.stats_grid,
            title="Study",
            count=0,
            icon="🎓",
            accent_color=CATEGORY_COLORS["Study"],
            subtitle="Academic & learning",
        )
        self.card_study.grid(row=0, column=1, padx=(0, 10), sticky="nsew")

        self.card_money = StatCard(
            self.stats_grid,
            title="Money",
            count=0,
            icon="💳",
            accent_color=CATEGORY_COLORS["Money"],
            subtitle="Financial & bills",
        )
        self.card_money.grid(row=0, column=2, padx=(0, 10), sticky="nsew")

        self.card_travel = StatCard(
            self.stats_grid,
            title="Travel",
            count=0,
            icon="✈️",
            accent_color=CATEGORY_COLORS["Travel"],
            subtitle="Trips & transit",
        )
        self.card_travel.grid(row=0, column=3, padx=(0, 10), sticky="nsew")

        self.card_shopping = StatCard(
            self.stats_grid,
            title="Shopping",
            count=0,
            icon="🛒",
            accent_color=CATEGORY_COLORS["Shopping"],
            subtitle="Purchases & orders",
        )
        self.card_shopping.grid(row=0, column=4, sticky="nsew")

        # 3. Category Distribution Bar
        self.distribution_bar = CategoryDistributionBar(self)
        self.distribution_bar.pack(fill="x", padx=32, pady=(0, 28))

        # 4. Recent Activity Stream
        recent_header = ctk.CTkFrame(self, fg_color="transparent")
        recent_header.pack(fill="x", padx=32, pady=(0, 12))

        self.recent_title = ctk.CTkLabel(
            recent_header,
            text="RECENT NOTES",
            font=get_font(13, weight="bold"),
            text_color=PALETTE["main_text"],
        )
        self.recent_title.pack(side="left")

        self.btn_view_all = ctk.CTkButton(
            recent_header,
            text="View All Notes →",
            font=get_font(12, weight="bold"),
            fg_color="transparent",
            hover_color=PALETTE["secondary_bg"],
            text_color=PALETTE["secondary_accent"],
            height=26,
            command=lambda: self.on_navigate("All Notes"),
        )
        self.btn_view_all.pack(side="right")

        self.recent_container = ctk.CTkFrame(self, fg_color="transparent")
        self.recent_container.pack(fill="x", padx=32, pady=(0, 40))

    def refresh_data(self, notes: List[Dict[str, Any]]) -> None:
        """Update dashboard numbers, distribution, and recent notes stream."""
        self.notes = notes
        total = len(notes)

        # Calculate exact counts
        counts = {
            "Study": sum(1 for n in notes if n.get("category") == "Study"),
            "Money": sum(1 for n in notes if n.get("category") == "Money"),
            "Travel": sum(1 for n in notes if n.get("category") == "Travel"),
            "Shopping": sum(1 for n in notes if n.get("category") == "Shopping"),
        }

        # Update cards
        self.card_total.update_stat(total, f"{total} total saved")
        self.card_study.update_stat(counts["Study"], f"{int(round(counts['Study']/total*100)) if total else 0}% of total")
        self.card_money.update_stat(counts["Money"], f"{int(round(counts['Money']/total*100)) if total else 0}% of total")
        self.card_travel.update_stat(counts["Travel"], f"{int(round(counts['Travel']/total*100)) if total else 0}% of total")
        self.card_shopping.update_stat(counts["Shopping"], f"{int(round(counts['Shopping']/total*100)) if total else 0}% of total")

        # Update distribution bar
        self.distribution_bar.update_distribution(counts)

        # Clear previous recent cards
        for child in self.recent_container.winfo_children():
            child.destroy()

        if total == 0:
            empty = EmptyState(
                self.recent_container,
                title="Your Notes Library is Empty",
                description="Start organizing your thoughts with genuine AI classification, or load the 12 original starter notes.",
                icon="💡",
                action_text="📥 Load Starter Notes",
                action_command=self.on_load_starter,
            )
            empty.pack(pady=20)
        else:
            # Sort by updated_at descending and take top 4
            recent = sorted(
                notes,
                key=lambda x: x.get("updated_at", ""),
                reverse=True
            )[:4]

            for note in recent:
                card = NoteCard(
                    self.recent_container,
                    note=note,
                    on_edit=self.on_open_editor,
                    on_delete=self.on_delete_note,
                    view_mode="list",
                )
                card.pack(fill="x", pady=6)

