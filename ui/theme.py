"""CustomTkinter theme constants."""

from __future__ import annotations

import customtkinter as ctk


COLORS = {
    "bg": "#f6f8fb",
    "surface": "#ffffff",
    "surface_alt": "#fbfdff",
    "surface_soft": "#f1f5f9",
    "text": "#152033",
    "muted": "#66758a",
    "border": "#dbe4ef",
    "shadow": "#e7edf5",
    "accent": "#2f6fed",
    "accent_hover": "#255ec8",
    "success": "#16875a",
    "success_bg": "#e5f7ee",
    "warning": "#b7791f",
    "warning_bg": "#fff4d6",
    "danger": "#c2413a",
    "danger_bg": "#fdebea",
}

FONT_FAMILY = "Helvetica Neue"


def apply_theme() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
