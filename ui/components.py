"""Reusable CustomTkinter components."""

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from .theme import COLORS, FONT_FAMILY


class Card(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=18,
            **kwargs,
        )


class SoftPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color=COLORS["surface_alt"], corner_radius=22, **kwargs)


class Pill(ctk.CTkLabel):
    def __init__(self, master, text: str = "-", status: str = "muted", **kwargs) -> None:
        super().__init__(
            master,
            text=text,
            height=24,
            corner_radius=12,
            font=(FONT_FAMILY, 11, "bold"),
            **kwargs,
        )
        self.set_status(status, text)

    def set_status(self, status: str, text: str | None = None) -> None:
        palette = {
            "good": (COLORS["success_bg"], COLORS["success"]),
            "ok": (COLORS["warning_bg"], COLORS["warning"]),
            "bad": (COLORS["danger_bg"], COLORS["danger"]),
            "info": ("#e8f0ff", COLORS["accent"]),
            "muted": (COLORS["surface_soft"], COLORS["muted"]),
        }
        bg, fg = palette.get(status, palette["muted"])
        self.configure(fg_color=bg, text_color=fg, text=text if text is not None else self.cget("text"))


class MetricCard(Card):
    def __init__(self, master, title: str) -> None:
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.title = ctk.CTkLabel(
            self,
            text=title,
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["muted"],
            anchor="w",
        )
        self.title.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 2))
        self.badge = Pill(self, "WAIT", "muted")
        self.badge.grid(row=0, column=1, sticky="ne", padx=14, pady=(12, 0))
        self.value = ctk.CTkLabel(
            self,
            text="-",
            font=(FONT_FAMILY, 21, "bold"),
            text_color=COLORS["text"],
            anchor="w",
            justify="left",
            wraplength=230,
        )
        self.value.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 0))
        self.target = ctk.CTkLabel(
            self,
            text="",
            font=(FONT_FAMILY, 12),
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
            wraplength=230,
        )
        self.target.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(3, 0))
        self.hint = ctk.CTkLabel(
            self,
            text="",
            font=(FONT_FAMILY, 12),
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
            wraplength=230,
        )
        self.hint.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(1, 14))

    def update_metric(self, value: str, target: str, status: str, hint: str = "") -> None:
        status_text = {"good": "GOOD", "ok": "OK", "bad": "BAD", "info": "INFO"}.get(status, "WAIT")
        self.value.configure(text=value)
        self.target.configure(text=target)
        self.hint.configure(text=hint)
        self.badge.set_status(status, status_text)


class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label: str, placeholder: str = "", show: str | None = None) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.label = ctk.CTkLabel(
            self,
            text=label,
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["muted"],
            anchor="w",
        )
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.var = tk.StringVar()
        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.var,
            placeholder_text=placeholder,
            height=38,
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            show=show or "",
        )
        self.entry.grid(row=1, column=0, sticky="ew")

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str) -> None:
        self.var.set(value)


class Tooltip:
    def __init__(self, widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None) -> None:
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip,
            text=self.text,
            background="#172033",
            foreground="#ffffff",
            padx=10,
            pady=6,
            font=(FONT_FAMILY, 11),
            wraplength=260,
            justify="left",
        )
        label.pack()

    def hide(self, _event=None) -> None:
        if self.tip:
            self.tip.destroy()
            self.tip = None


class Toast(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="#172033", corner_radius=14)
        self.label = ctk.CTkLabel(self, text="", text_color="#ffffff", font=(FONT_FAMILY, 12))
        self.label.pack(padx=14, pady=8)

    def show(self, text: str, duration_ms: int = 2200) -> None:
        self.label.configure(text=text)
        self.place(relx=0.5, rely=0.965, anchor="s")
        self.after(duration_ms, self.place_forget)
