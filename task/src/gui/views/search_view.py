"""
Smart Notes Assistant - Search Experience View
Phase 8: Premium Native Windows Desktop Application

Full-text and semantic retrieval workspace:
- Prominent search input with auto-clear and enter trigger
- Search engine selector: TF-IDF Cosine Similarity (Default) vs Keyword Search
- Ranked result cards displaying rank, relevance score, and category badge
- Dedicated states for empty queries, loading, and no results
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from src.gui.api_client import NotesApiClient
from src.gui.components import CategoryBadge, EmptyState, UncertaintyBadge
from src.gui.theme import PALETTE, STATUS_COLORS, get_font


class SearchResultCard(ctk.CTkFrame):
    """
    Card displaying a single ranked search result.
    """

    def __init__(
        self,
        master: Any,
        result: Dict[str, Any],
        on_click: Callable[[Dict[str, Any]], None],
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=PALETTE["card_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=12,
            **kwargs
        )
        self.result = result
        self.on_click = on_click

        rank = result.get("rank", 1)
        score = float(result.get("score", 0.0))
        note_id = result.get("id", "N???")
        text = result.get("text", "")
        category = result.get("category", "Study")
        confidence = float(result.get("confidence", 0.0))
        uncertain = bool(result.get("uncertain", False))

        # Top row: Rank, ID, Category, Score
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))

        # Rank badge
        rank_badge = ctk.CTkLabel(
            header,
            text=f"#{rank}",
            font=get_font(12, weight="bold"),
            text_color="#FFFFFF",
            fg_color=PALETTE["primary_accent"],
            corner_radius=6,
            width=36,
            height=22,
        )
        rank_badge.pack(side="left", padx=(0, 8))

        id_badge = ctk.CTkLabel(
            header,
            text=note_id,
            font=get_font(12, weight="bold"),
            text_color=PALETTE["secondary_accent"],
            fg_color=PALETTE["secondary_bg"],
            corner_radius=6,
            width=50,
            height=22,
        )
        id_badge.pack(side="left", padx=(0, 8))

        cat_badge = CategoryBadge(header, category=category)
        cat_badge.pack(side="left", padx=(0, 8))

        unc_badge = UncertaintyBadge(header, uncertain=uncertain, confidence=confidence)
        unc_badge.pack(side="left")

        # Score display on right
        score_lbl = ctk.CTkLabel(
            header,
            text=f"Relevance: {score:.4f}",
            font=get_font(11, weight="bold"),
            text_color=PALETTE["muted_text"],
        )
        score_lbl.pack(side="right")

        # Note text
        body_lbl = ctk.CTkLabel(
            self,
            text=text,
            font=get_font(13),
            text_color=PALETTE["main_text"],
            wraplength=800,
            justify="left",
            anchor="w",
        )
        body_lbl.pack(fill="x", padx=16, pady=(0, 14))

        # Hover effects & click
        for w in (self, body_lbl):
            w.bind("<Enter>", lambda e: self.configure(border_color=PALETTE["secondary_accent"]))
            w.bind("<Leave>", lambda e: self.configure(border_color=PALETTE["border"]))
            w.bind("<Button-1>", lambda e: self.on_click(self.result))


class SearchView(ctk.CTkScrollableFrame):
    """
    Dedicated search view with prominent input, method selector, and ranked cards.
    """

    def __init__(
        self,
        master: Any,
        api_client: NotesApiClient,
        on_open_note: Callable[[Dict[str, Any]], None],
        **kwargs
    ):
        super().__init__(
            master,
            fg_color="transparent",
            **kwargs
        )
        self.api_client = api_client
        self.on_open_note = on_open_note

        self._is_searching = False
        self._build_ui()

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(28, 16))

        title = ctk.CTkLabel(
            header,
            text="Search Notes",
            font=get_font(24, weight="bold"),
            text_color=PALETTE["main_text"],
        )
        title.pack(side="left")

        subtitle = ctk.CTkLabel(
            header,
            text="Query all saved notes using TF-IDF cosine similarity or keyword ranking.",
            font=get_font(13),
            text_color=PALETTE["secondary_text"],
        )
        subtitle.pack(side="left", padx=(16, 0), pady=(6, 0))

        # Search Control Box
        search_box = ctk.CTkFrame(
            self,
            fg_color=PALETTE["card_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=14,
        )
        search_box.pack(fill="x", padx=32, pady=(0, 20))

        # Input Row
        input_row = ctk.CTkFrame(search_box, fg_color="transparent")
        input_row.pack(fill="x", padx=16, pady=14)

        icon_lbl = ctk.CTkLabel(
            input_row,
            text="🔍",
            font=get_font(16),
        )
        icon_lbl.pack(side="left", padx=(0, 8))

        self.query_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter search query (e.g., 'python algorithms', 'grocery list', 'flight booking')...",
            font=get_font(14),
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=8,
            height=40,
        )
        self.query_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.query_entry.bind("<Return>", lambda e: self._perform_search())

        self.btn_search = ctk.CTkButton(
            input_row,
            text="Search",
            font=get_font(13, weight="bold"),
            fg_color=PALETTE["primary_accent"],
            hover_color=PALETTE["primary_accent_hover"],
            text_color="#FFFFFF",
            corner_radius=8,
            height=40,
            width=100,
            command=self._perform_search,
        )
        self.btn_search.pack(side="left", padx=(0, 8))

        self.btn_clear = ctk.CTkButton(
            input_row,
            text="Clear",
            font=get_font(12),
            fg_color=PALETTE["secondary_bg"],
            hover_color=PALETTE["border"],
            text_color=PALETTE["main_text"],
            corner_radius=8,
            height=40,
            width=70,
            command=self._clear_search,
        )
        self.btn_clear.pack(side="left")

        # Method Selector Row
        options_row = ctk.CTkFrame(search_box, fg_color="transparent")
        options_row.pack(fill="x", padx=16, pady=(0, 12))

        opt_lbl = ctk.CTkLabel(
            options_row,
            text="Search Engine Method:",
            font=get_font(12, weight="bold"),
            text_color=PALETTE["secondary_text"],
        )
        opt_lbl.pack(side="left", padx=(0, 10))

        self.method_selector = ctk.CTkSegmentedButton(
            options_row,
            values=["TF-IDF Cosine Similarity", "Keyword Search"],
            font=get_font(11),
            selected_color=PALETTE["primary_accent"],
            selected_hover_color=PALETTE["primary_accent_hover"],
            unselected_color=PALETTE["secondary_bg"],
            unselected_hover_color=PALETTE["card_hover"],
            corner_radius=6,
            height=28,
            command=lambda v: self._perform_search() if self.query_entry.get().strip() else None,
        )
        self.method_selector.set("TF-IDF Cosine Similarity")
        self.method_selector.pack(side="left")

        # Status Summary Bar
        self.status_bar = ctk.CTkLabel(
            self,
            text="",
            font=get_font(12, weight="bold"),
            text_color=PALETTE["secondary_text"],
            anchor="w",
        )
        self.status_bar.pack(fill="x", padx=32, pady=(0, 10))

        # Results Container
        self.results_container = ctk.CTkFrame(self, fg_color="transparent")
        self.results_container.pack(fill="both", expand=True, padx=32, pady=(0, 32))

        self._show_initial_state()

    def focus_search(self) -> None:
        """Focus the search input entry for shortcut navigation."""
        self.query_entry.focus_set()

    def _show_initial_state(self) -> None:
        for c in self.results_container.winfo_children():
            c.destroy()
        empty = EmptyState(
            self.results_container,
            title="Instant Retrieval",
            description="Type keywords or natural language queries above to find any note in your personal knowledge base.",
            icon="🔎",
        )
        empty.pack(fill="both", expand=True, pady=40)

    def _clear_search(self) -> None:
        self.query_entry.delete(0, "end")
        self.status_bar.configure(text="")
        self._show_initial_state()

    def _perform_search(self) -> None:
        query = self.query_entry.get().strip()
        if not query:
            self._show_initial_state()
            return

        method_choice = self.method_selector.get()
        method_param = "tfidf" if "TF-IDF" in method_choice else "keyword"

        self._is_searching = True
        self.btn_search.configure(text="Searching...", state="disabled")
        self.status_bar.configure(text=f"Searching notes for '{query}'...")

        def _call():
            return self.api_client.search_notes(query=query, method=method_param, top_k=25)

        def _success(results: List[Dict[str, Any]]):
            self._is_searching = False
            self.btn_search.configure(text="Search", state="normal")
            for c in self.results_container.winfo_children():
                c.destroy()

            count = len(results)
            self.status_bar.configure(
                text=f"Found {count} matching note{'s' if count != 1 else ''} using {method_choice}."
            )

            if count == 0:
                empty = EmptyState(
                    self.results_container,
                    title="No Matching Notes Found",
                    description=f"No notes matched '{query}' with the active search method. Try different search terms or toggle the search method.",
                    icon="🔍",
                )
                empty.pack(fill="both", expand=True, pady=40)
                return

            for res in results:
                card = SearchResultCard(
                    self.results_container,
                    result=res,
                    on_click=self.on_open_note,
                )
                card.pack(fill="x", pady=6)

        def _error(err: Exception):
            self._is_searching = False
            self.btn_search.configure(text="Search", state="normal")
            err_msg = str(getattr(err, "detail", err))
            self.status_bar.configure(
                text=f"Search failed: {err_msg}",
                text_color=STATUS_COLORS["error"]
            )

        self.api_client.execute_async(
            _call,
            on_success=_success,
            on_error=_error,
            tk_root=self,
        )

