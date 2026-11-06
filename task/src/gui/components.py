"""
Smart Notes Assistant - Reusable Desktop UI Components
Phase 8: Premium Native Windows Desktop Application

Provides polished, reusable CustomTkinter widgets:
- Navigation buttons with active state indicators
- Category and uncertainty badges
- Dashboard statistics cards
- Responsive note cards with hover elevation
- Category distribution progress bar
- Search result cards
- Empty states & floating notification toasts
- Confirmation modal dialogs
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from src.gui.theme import (
    CATEGORY_BG_TINTS,
    CATEGORY_COLORS,
    PALETTE,
    STATUS_COLORS,
    get_font,
    theme_mgr,
)


# ---------------------------------------------------------------------------
# Navigation Item Widget
# ---------------------------------------------------------------------------
class SidebarNavItem(ctk.CTkFrame):
    """
    Polished sidebar navigation button with left active indicator bar,
    subtle hover styling, icon, and dynamic badge.
    """

    def __init__(
        self,
        master: Any,
        label: str,
        icon: str,
        command: Callable[[], None],
        badge_count: Optional[int] = None,
        is_category: bool = False,
        category_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color="transparent",
            corner_radius=8,
            height=42,
            **kwargs
        )
        self.label_text = label
        self.icon_char = icon
        self.command = command
        self.is_active = False
        self.category_name = category_name

        self.grid_columnconfigure(1, weight=1)

        # Active indicator strip (left 4px)
        self.active_indicator = ctk.CTkFrame(
            self,
            width=4,
            height=24,
            corner_radius=2,
            fg_color="transparent",
        )
        self.active_indicator.grid(row=0, column=0, padx=(3, 6), pady=8, sticky="nsw")

        # Icon
        icon_color = CATEGORY_COLORS.get(category_name, PALETTE["secondary_text"]) if category_name else PALETTE["secondary_text"]
        self.icon_label = ctk.CTkLabel(
            self,
            text=self.icon_char,
            font=get_font(15, weight="bold"),
            text_color=icon_color,
            width=26,
            anchor="center",
        )
        self.icon_label.grid(row=0, column=1, padx=(2, 8), pady=8, sticky="w")

        # Label Text
        self.title_label = ctk.CTkLabel(
            self,
            text=self.label_text,
            font=get_font(13, weight="normal"),
            text_color=PALETTE["secondary_text"],
            anchor="w",
        )
        self.title_label.grid(row=0, column=2, padx=(0, 6), pady=8, sticky="w")

        # Optional Count Badge
        self.badge_label = ctk.CTkLabel(
            self,
            text="" if badge_count is None else str(badge_count),
            font=get_font(11, weight="bold"),
            text_color=PALETTE["muted_text"],
            fg_color="transparent",
            width=24,
            anchor="e",
        )
        self.badge_label.grid(row=0, column=3, padx=(4, 10), pady=8, sticky="e")

        # Bind click and hover events to all child elements
        for widget in (self, self.active_indicator, self.icon_label, self.title_label, self.badge_label):
            widget.bind("<Button-1>", lambda e: self._on_click())
            widget.bind("<Enter>", lambda e: self._on_enter())
            widget.bind("<Leave>", lambda e: self._on_leave())

    def set_active(self, active: bool) -> None:
        self.is_active = active
        if active:
            self.configure(fg_color=PALETTE["secondary_bg"])
            self.active_indicator.configure(fg_color=PALETTE["primary_accent"])
            self.title_label.configure(
                text_color=PALETTE["main_text"],
                font=get_font(13, weight="bold")
            )
        else:
            self.configure(fg_color="transparent")
            self.active_indicator.configure(fg_color="transparent")
            self.title_label.configure(
                text_color=PALETTE["secondary_text"],
                font=get_font(13, weight="normal")
            )

    def set_badge(self, count: Optional[int]) -> None:
        if count is None or count == 0:
            self.badge_label.configure(text="")
        else:
            self.badge_label.configure(text=str(count))

    def _on_click(self) -> None:
        if self.command:
            self.command()

    def _on_enter(self) -> None:
        if not self.is_active:
            self.configure(fg_color=PALETTE["secondary_bg"])

    def _on_leave(self) -> None:
        if not self.is_active:
            self.configure(fg_color="transparent")


# ---------------------------------------------------------------------------
# Category Badge Widget
# ---------------------------------------------------------------------------
class CategoryBadge(ctk.CTkFrame):
    """
    Subtle rounded pill displaying note category with distinct color branding.
    """

    def __init__(self, master: Any, category: str, **kwargs):
        color = CATEGORY_COLORS.get(category, "#927FEA")
        bg_tint = CATEGORY_BG_TINTS.get(category, ("#F0EDFA", "#252438"))

        super().__init__(
            master,
            fg_color=bg_tint,
            border_color=color,
            border_width=1,
            corner_radius=12,
            height=24,
            **kwargs
        )
        self.label = ctk.CTkLabel(
            self,
            text=f"●  {category}",
            font=get_font(11, weight="bold"),
            text_color=color,
        )
        self.label.pack(padx=8, pady=2)


# ---------------------------------------------------------------------------
# Uncertainty / Confidence Badge
# ---------------------------------------------------------------------------
class UncertaintyBadge(ctk.CTkFrame):
    """
    Displays model confidence with explicit, honest visual styling.
    Shows amber warning badge for uncertain predictions requiring user review.
    """

    def __init__(
        self,
        master: Any,
        uncertain: bool,
        confidence: float,
        show_percentage: bool = True,
        **kwargs
    ):
        conf_pct = int(round(confidence * 100))
        if uncertain:
            border_color = STATUS_COLORS["uncertain"]
            bg_color = STATUS_COLORS["uncertain_bg"]
            text_color = STATUS_COLORS["uncertain"]
            badge_text = f"⚠ Needs Review ({conf_pct}%)"
        else:
            border_color = PALETTE["border"]
            bg_color = "transparent"
            text_color = PALETTE["secondary_text"]
            badge_text = f"{conf_pct}% confidence" if show_percentage else "High confidence"

        super().__init__(
            master,
            fg_color=bg_color,
            border_color=border_color,
            border_width=1,
            corner_radius=12,
            height=24,
            **kwargs
        )
        self.label = ctk.CTkLabel(
            self,
            text=badge_text,
            font=get_font(11, weight="bold" if uncertain else "normal"),
            text_color=text_color,
        )
        self.label.pack(padx=8, pady=2)


# ---------------------------------------------------------------------------
# Dashboard Statistics Card
# ---------------------------------------------------------------------------
class StatCard(ctk.CTkFrame):
    """
    Polished dashboard statistics card displaying category icon, count, and percentage.
    """

    def __init__(
        self,
        master: Any,
        title: str,
        count: int = 0,
        icon: str = "📝",
        accent_color: Optional[str] = None,
        subtitle: str = "",
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=PALETTE["card_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=14,
            height=110,
            **kwargs
        )
        self.grid_columnconfigure(0, weight=1)
        self.accent_color = accent_color or PALETTE["primary_accent"]

        # Top indicator bar
        self.top_bar = ctk.CTkFrame(
            self,
            height=3,
            corner_radius=2,
            fg_color=self.accent_color,
        )
        self.top_bar.pack(fill="x", padx=16, pady=(10, 6))

        # Content frame
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        # Top row: Title and Icon
        top_row = ctk.CTkFrame(content_frame, fg_color="transparent")
        top_row.pack(fill="x")

        self.title_label = ctk.CTkLabel(
            top_row,
            text=title.upper(),
            font=get_font(11, weight="bold"),
            text_color=PALETTE["secondary_text"],
            anchor="w",
        )
        self.title_label.pack(side="left")

        self.icon_label = ctk.CTkLabel(
            top_row,
            text=icon,
            font=get_font(15),
            anchor="e",
        )
        self.icon_label.pack(side="right")

        # Value label
        self.count_label = ctk.CTkLabel(
            content_frame,
            text=str(count),
            font=get_font(28, weight="bold"),
            text_color=PALETTE["main_text"],
            anchor="w",
        )
        self.count_label.pack(fill="x", pady=(2, 0))

        # Subtitle
        self.sub_label = ctk.CTkLabel(
            content_frame,
            text=subtitle,
            font=get_font(11),
            text_color=PALETTE["muted_text"],
            anchor="w",
        )
        self.sub_label.pack(fill="x")

    def update_stat(self, count: int, subtitle: str = "") -> None:
        self.count_label.configure(text=str(count))
        if subtitle:
            self.sub_label.configure(text=subtitle)


# ---------------------------------------------------------------------------
# Note Card Component
# ---------------------------------------------------------------------------
class NoteCard(ctk.CTkFrame):
    """
    Card representing a single note in All Notes and Dashboard views.
    Includes Note ID, category badge, uncertainty indicator, timestamp,
    text snippet, and edit/delete actions.
    """

    def __init__(
        self,
        master: Any,
        note: Dict[str, Any],
        on_edit: Callable[[Dict[str, Any]], None],
        on_delete: Callable[[Dict[str, Any]], None],
        view_mode: str = "grid",  # "grid" or "list"
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
        self.note = note
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.view_mode = view_mode

        self._build_card()

        # Bind hover effects
        self.bind("<Enter>", lambda e: self.configure(border_color=PALETTE["secondary_accent"]))
        self.bind("<Leave>", lambda e: self.configure(border_color=PALETTE["border"]))

    def _build_card(self) -> None:
        note_id = self.note.get("id", "N???")
        text = self.note.get("text", "")
        category = self.note.get("category", "Study")
        confidence = float(self.note.get("confidence", 0.0))
        uncertain = bool(self.note.get("uncertain", False))
        updated_at = self.note.get("updated_at", "")[:10]  # YYYY-MM-DD

        padding = 14 if self.view_mode == "grid" else 10

        # Header Frame: ID, Category Badge, Uncertainty, and Action buttons
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=padding, pady=(padding, 6))

        # ID Pill
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

        # Category Badge
        cat_badge = CategoryBadge(header, category=category)
        cat_badge.pack(side="left", padx=(0, 8))

        # Uncertainty Indicator
        unc_badge = UncertaintyBadge(header, uncertain=uncertain, confidence=confidence)
        unc_badge.pack(side="left")

        # Action Buttons on Right
        btn_delete = ctk.CTkButton(
            header,
            text="✕",
            font=get_font(11, weight="bold"),
            text_color=PALETTE["secondary_text"],
            fg_color="transparent",
            hover_color=STATUS_COLORS["error_bg"],
            width=24,
            height=24,
            corner_radius=6,
            command=lambda: self.on_delete(self.note),
        )
        btn_delete.pack(side="right", padx=(4, 0))

        btn_edit = ctk.CTkButton(
            header,
            text="✎",
            font=get_font(13),
            text_color=PALETTE["secondary_text"],
            fg_color="transparent",
            hover_color=PALETTE["secondary_bg"],
            width=24,
            height=24,
            corner_radius=6,
            command=lambda: self.on_edit(self.note),
        )
        btn_edit.pack(side="right")

        # Note Text Body
        display_text = text if len(text) <= 300 else f"{text[:297]}..."
        body_label = ctk.CTkLabel(
            self,
            text=display_text,
            font=get_font(13),
            text_color=PALETTE["main_text"],
            wraplength=380 if self.view_mode == "grid" else 850,
            justify="left",
            anchor="w",
        )
        body_label.pack(fill="both", expand=True, padx=padding, pady=(4, 8))
        body_label.bind("<Button-1>", lambda e: self.on_edit(self.note))

        # Footer Frame: Updated timestamp
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=padding, pady=(0, padding))

        time_label = ctk.CTkLabel(
            footer,
            text=f"Updated: {updated_at}",
            font=get_font(10),
            text_color=PALETTE["muted_text"],
        )
        time_label.pack(side="left")


# ---------------------------------------------------------------------------
# Category Distribution Bar
# ---------------------------------------------------------------------------
class CategoryDistributionBar(ctk.CTkFrame):
    """
    Clean proportional segmented progress bar showing distribution across categories.
    """

    def __init__(self, master: Any, **kwargs):
        super().__init__(
            master,
            fg_color=PALETTE["card_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=14,
            **kwargs
        )
        self.pack_propagate(True)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))

        title = ctk.CTkLabel(
            header,
            text="CATEGORY DISTRIBUTION",
            font=get_font(11, weight="bold"),
            text_color=PALETTE["secondary_text"],
        )
        title.pack(side="left")

        # Bar container
        self.bar_frame = ctk.CTkFrame(
            self,
            height=12,
            corner_radius=6,
            fg_color=PALETTE["secondary_bg"],
        )
        self.bar_frame.pack(fill="x", padx=16, pady=(4, 10))

        # Legend container
        self.legend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.legend_frame.pack(fill="x", padx=16, pady=(0, 12))

    def update_distribution(self, category_counts: Dict[str, int]) -> None:
        """Update distribution bar segments and legend tags."""
        total = sum(category_counts.values())

        # Clear existing segment frames
        for child in self.bar_frame.winfo_children():
            child.destroy()
        for child in self.legend_frame.winfo_children():
            child.destroy()

        if total == 0:
            empty_lbl = ctk.CTkLabel(
                self.legend_frame,
                text="No notes available to analyze.",
                font=get_font(11),
                text_color=PALETTE["muted_text"],
            )
            empty_lbl.pack(side="left")
            return

        # Build legend items
        categories = ["Study", "Money", "Travel", "Shopping"]
        for cat in categories:
            cnt = category_counts.get(cat, 0)
            pct = int(round((cnt / total) * 100)) if total > 0 else 0
            color = CATEGORY_COLORS.get(cat, "#927FEA")

            item = ctk.CTkFrame(self.legend_frame, fg_color="transparent")
            item.pack(side="left", padx=(0, 20))

            dot = ctk.CTkLabel(
                item,
                text="●",
                font=get_font(13),
                text_color=color,
            )
            dot.pack(side="left", padx=(0, 4))

            txt = ctk.CTkLabel(
                item,
                text=f"{cat}: {cnt} ({pct}%)",
                font=get_font(11),
                text_color=PALETTE["secondary_text"],
            )
            txt.pack(side="left")


# ---------------------------------------------------------------------------
# Empty State Widget
# ---------------------------------------------------------------------------
class EmptyState(ctk.CTkFrame):
    """
    Refined empty state placeholder shown when no notes match a query or category.
    """

    def __init__(
        self,
        master: Any,
        title: str = "No Notes Yet",
        description: str = "Create your first smart note to get started.",
        icon: str = "📝",
        action_text: Optional[str] = None,
        action_command: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color="transparent",
            **kwargs
        )
        icon_lbl = ctk.CTkLabel(
            self,
            text=icon,
            font=get_font(42),
        )
        icon_lbl.pack(pady=(40, 10))

        title_lbl = ctk.CTkLabel(
            self,
            text=title,
            font=get_font(18, weight="bold"),
            text_color=PALETTE["main_text"],
        )
        title_lbl.pack(pady=(0, 6))

        desc_lbl = ctk.CTkLabel(
            self,
            text=description,
            font=get_font(13),
            text_color=PALETTE["secondary_text"],
            wraplength=400,
            justify="center",
        )
        desc_lbl.pack(pady=(0, 20))

        if action_text and action_command:
            btn = ctk.CTkButton(
                self,
                text=action_text,
                font=get_font(13, weight="bold"),
                fg_color=PALETTE["primary_accent"],
                hover_color=PALETTE["primary_accent_hover"],
                corner_radius=8,
                height=36,
                command=action_command,
            )
            btn.pack()


# ---------------------------------------------------------------------------
# Confirmation Modal Dialog
# ---------------------------------------------------------------------------
class ConfirmDialog(ctk.CTkToplevel):
    """
    Modal confirmation dialog for destructive actions such as deleting notes.
    """

    def __init__(
        self,
        parent: Any,
        title: str,
        message: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        is_destructive: bool = False,
        on_confirm: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.title(title)
        self.geometry("420x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=PALETTE["card_bg"])

        # Center on parent
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 210
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 100
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        # Title
        t_lbl = ctk.CTkLabel(
            self,
            text=title,
            font=get_font(16, weight="bold"),
            text_color=PALETTE["main_text"],
        )
        t_lbl.pack(padx=24, pady=(20, 8), anchor="w")

        # Message
        m_lbl = ctk.CTkLabel(
            self,
            text=message,
            font=get_font(13),
            text_color=PALETTE["secondary_text"],
            wraplength=370,
            justify="left",
            anchor="w",
        )
        m_lbl.pack(padx=24, pady=(0, 20), anchor="w", fill="x")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 20), side="bottom")

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text=cancel_text,
            font=get_font(12),
            fg_color=PALETTE["secondary_bg"],
            hover_color=PALETTE["border"],
            text_color=PALETTE["main_text"],
            corner_radius=8,
            width=90,
            height=34,
            command=self.destroy,
        )
        btn_cancel.pack(side="right", padx=(8, 0))

        confirm_fg = STATUS_COLORS["error"] if is_destructive else PALETTE["primary_accent"]
        btn_confirm = ctk.CTkButton(
            btn_frame,
            text=confirm_text,
            font=get_font(12, weight="bold"),
            fg_color=confirm_fg,
            text_color="#FFFFFF",
            corner_radius=8,
            width=100,
            height=34,
            command=self._confirm,
        )
        btn_confirm.pack(side="right")

    def _confirm(self) -> None:
        self.destroy()
        if self.on_confirm:
            self.on_confirm()

