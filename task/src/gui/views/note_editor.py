"""
Smart Notes Assistant - Note Editor Dialog
Phase 8: Premium Native Windows Desktop Application

Modal window for creating and editing notes with:
- Strict character count tracking (0-1000 limit)
- Real-time ML classification preview via POST /classify
- Confidence percentage and honest uncertainty indicator
- Duplicate submission prevention
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from src.gui.api_client import NotesApiClient
from src.gui.components import CategoryBadge, UncertaintyBadge
from src.gui.theme import PALETTE, STATUS_COLORS, get_font


class NoteEditorDialog(ctk.CTkToplevel):
    """
    Intelligent note editor modal supporting creation and modification of notes.
    """

    def __init__(
        self,
        parent: Any,
        api_client: NotesApiClient,
        note: Optional[Dict[str, Any]] = None,
        on_save_success: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        super().__init__(parent)
        self.parent = parent
        self.api_client = api_client
        self.note = note
        self.is_edit_mode = (note is not None)
        self.on_save_success = on_save_success

        self.title("Edit Note" if self.is_edit_mode else "New Note")
        self.geometry("640x540")
        self.minsize(540, 480)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=PALETTE["card_bg"])

        # Center on parent window
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 320
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 270
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

        self._debounce_timer: Optional[str] = None
        self._is_saving = False

        self._build_ui()

        # Keyboard shortcuts
        self.bind("<Control-s>", lambda e: self._on_save())
        self.bind("<Escape>", lambda e: self.destroy())

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 12))

        title_text = f"Edit Note {self.note.get('id', '')}" if self.is_edit_mode else "Create Smart Note"
        self.header_title = ctk.CTkLabel(
            header,
            text=title_text,
            font=get_font(20, weight="bold"),
            text_color=PALETTE["main_text"],
        )
        self.header_title.pack(side="left")

        # Text Box Container
        editor_frame = ctk.CTkFrame(
            self,
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=10,
        )
        editor_frame.pack(fill="both", expand=True, padx=28, pady=(0, 8))

        self.textbox = ctk.CTkTextbox(
            editor_frame,
            font=get_font(14),
            text_color=PALETTE["main_text"],
            fg_color="transparent",
            wrap="word",
        )
        self.textbox.pack(fill="both", expand=True, padx=12, pady=12)
        self.textbox.bind("<KeyRelease>", self._on_text_changed)

        if self.is_edit_mode and self.note:
            self.textbox.insert("1.0", self.note.get("text", ""))

        # Character Counter & Status Bar
        meta_row = ctk.CTkFrame(self, fg_color="transparent")
        meta_row.pack(fill="x", padx=28, pady=(0, 10))

        self.char_counter = ctk.CTkLabel(
            meta_row,
            text="0 / 1000 characters",
            font=get_font(11),
            text_color=PALETTE["muted_text"],
        )
        self.char_counter.pack(side="left")

        self.btn_analyze = ctk.CTkButton(
            meta_row,
            text="⚡ Preview AI Classification",
            font=get_font(11, weight="bold"),
            fg_color="transparent",
            hover_color=PALETTE["secondary_bg"],
            text_color=PALETTE["secondary_accent"],
            height=26,
            command=self._trigger_classification_preview,
        )
        self.btn_analyze.pack(side="right")

        # Live Classification Preview Card
        self.preview_card = ctk.CTkFrame(
            self,
            fg_color=PALETTE["secondary_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=10,
            height=54,
        )
        self.preview_card.pack(fill="x", padx=28, pady=(0, 16))

        self.preview_inner = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.preview_inner.pack(fill="both", expand=True, padx=14, pady=10)

        self.preview_placeholder = ctk.CTkLabel(
            self.preview_inner,
            text="Type your note above to preview genuine machine learning classification.",
            font=get_font(12),
            text_color=PALETTE["muted_text"],
        )
        self.preview_placeholder.pack(side="left")

        # Error / Feedback Banner
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            font=get_font(11, weight="bold"),
            text_color=STATUS_COLORS["error"],
            wraplength=550,
            justify="left",
        )
        self.error_label.pack(fill="x", padx=28, pady=(0, 6))

        # Bottom Actions Bar
        actions_row = ctk.CTkFrame(self, fg_color="transparent")
        actions_row.pack(fill="x", padx=28, pady=(0, 24), side="bottom")

        btn_cancel = ctk.CTkButton(
            actions_row,
            text="Cancel (Esc)",
            font=get_font(12),
            fg_color=PALETTE["secondary_bg"],
            hover_color=PALETTE["border"],
            text_color=PALETTE["main_text"],
            corner_radius=8,
            width=100,
            height=36,
            command=self.destroy,
        )
        btn_cancel.pack(side="right", padx=(10, 0))

        self.btn_save = ctk.CTkButton(
            actions_row,
            text="Save Note (Ctrl+S)",
            font=get_font(12, weight="bold"),
            fg_color=PALETTE["primary_accent"],
            hover_color=PALETTE["primary_accent_hover"],
            text_color="#FFFFFF",
            corner_radius=8,
            width=140,
            height=36,
            command=self._on_save,
        )
        self.btn_save.pack(side="right")

        # Initial trigger
        self._update_char_count()
        if self.is_edit_mode:
            self._trigger_classification_preview()

    def _get_text(self) -> str:
        return self.textbox.get("1.0", "end-1c")

    def _update_char_count(self) -> int:
        length = len(self._get_text())
        if length > 1000:
            self.char_counter.configure(
                text=f"{length} / 1000 characters (exceeds limit)",
                text_color=STATUS_COLORS["error"],
            )
            self.btn_save.configure(state="disabled")
        else:
            self.char_counter.configure(
                text=f"{length} / 1000 characters",
                text_color=PALETTE["muted_text"] if length < 900 else STATUS_COLORS["uncertain"],
            )
            self.btn_save.configure(state="normal")
        return length

    def _on_text_changed(self, event=None) -> None:
        self.error_label.configure(text="")
        length = self._update_char_count()

        # Automatic debounced classification preview after 600ms pause
        if self._debounce_timer:
            self.after_cancel(self._debounce_timer)
        if 5 <= length <= 1000:
            self._debounce_timer = self.after(600, self._trigger_classification_preview)

    def _trigger_classification_preview(self) -> None:
        text = self._get_text().strip()
        if not text:
            return

        self.btn_analyze.configure(text="Analyzing...", state="disabled")

        def _call():
            return self.api_client.classify_text(text)

        def _success(res: Dict[str, Any]):
            self.btn_analyze.configure(text="⚡ Preview AI Classification", state="normal")
            for w in self.preview_inner.winfo_children():
                w.destroy()

            cat = res.get("category", "Study")
            conf = float(res.get("confidence", 0.0))
            unc = bool(res.get("uncertain", False))

            prefix = ctk.CTkLabel(
                self.preview_inner,
                text="Predicted:",
                font=get_font(12, weight="bold"),
                text_color=PALETTE["secondary_text"],
            )
            prefix.pack(side="left", padx=(0, 8))

            badge = CategoryBadge(self.preview_inner, category=cat)
            badge.pack(side="left", padx=(0, 8))

            unc_badge = UncertaintyBadge(self.preview_inner, uncertain=unc, confidence=conf)
            unc_badge.pack(side="left", padx=(0, 8))

            if unc:
                hint = ctk.CTkLabel(
                    self.preview_inner,
                    text="AI is not fully confident. Please review.",
                    font=get_font(11),
                    text_color=STATUS_COLORS["uncertain"],
                )
                hint.pack(side="left")

        def _error(err: Exception):
            self.btn_analyze.configure(text="⚡ Preview AI Classification", state="normal")

        self.api_client.execute_async(
            _call,
            on_success=_success,
            on_error=_error,
            tk_root=self,
        )

    def _on_save(self) -> None:
        if self._is_saving:
            return

        text = self._get_text().strip()
        if not text:
            self.error_label.configure(text="Note text cannot be empty or whitespace-only.")
            return
        if len(self._get_text()) > 1000:
            self.error_label.configure(text="Note text exceeds the maximum limit of 1000 characters.")
            return

        self._is_saving = True
        self.btn_save.configure(text="Saving...", state="disabled")
        self.error_label.configure(text="")

        def _call():
            if self.is_edit_mode and self.note:
                note_id = self.note["id"]
                return self.api_client.update_note(note_id, text)
            else:
                return self.api_client.create_note(text)

        def _success(res: Dict[str, Any]):
            self.destroy()
            if self.on_save_success:
                self.on_save_success(res)

        def _error(err: Exception):
            self._is_saving = False
            self.btn_save.configure(text="Save Note (Ctrl+S)", state="normal")
            err_msg = str(getattr(err, "detail", err))
            self.error_label.configure(text=f"Failed to save note: {err_msg}")

        self.api_client.execute_async(
            _call,
            on_success=_success,
            on_error=_error,
            tk_root=self,
        )

