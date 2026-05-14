"""Polished modal dialogs."""

from __future__ import annotations

import customtkinter as ctk

from .theme import COLORS, FONT_FAMILY


class SelectionDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, values: tuple[str, ...], default: str) -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("360x190")
        self.minsize(360, 190)
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])
        self.transient(master)
        self.grab_set()
        self.result = default

        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self,
            text=title,
            font=(FONT_FAMILY, 18, "bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(22, 8))
        self.option = ctk.CTkOptionMenu(self, values=list(values), height=38, corner_radius=12)
        self.option.set(default)
        self.option.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 18))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="e", padx=22, pady=(0, 18))
        ctk.CTkButton(actions, text="Cancel", fg_color=COLORS["surface_soft"], text_color=COLORS["text"], command=self._cancel).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(actions, text="Save", fg_color=COLORS["accent"], command=self._save).pack(side="left")

        self.bind("<Escape>", lambda _event: self._cancel())
        self.bind("<Return>", lambda _event: self._save())
        self.update_idletasks()
        self._center(master)

    def _center(self, master) -> None:
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (self.winfo_width() // 2)
        y = master.winfo_rooty() + (master.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _save(self) -> None:
        self.result = self.option.get()
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()


def choose_value(master, title: str, values: tuple[str, ...], default: str) -> str:
    dialog = SelectionDialog(master, title, values, default)
    master.wait_window(dialog)
    return dialog.result
