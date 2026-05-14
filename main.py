"""Modern CustomTkinter interface for Trading Risk Cockpit."""

from __future__ import annotations

import datetime as dt
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from calculator import ASSET_TYPES, CURRENCIES, DIRECTIONS, TradeInputs, calculate_trade, grade_checklist
from data.catalog_loader import Instrument, InstrumentCatalog
from data.market_data import MarketDataService, load_env, save_env
from database import TRADE_COLUMNS, TradingDatabase
from logic.recommendations import quality_assessments
from ui.components import Card, LabeledEntry, MetricCard, Pill, Toast, Tooltip
from ui.dialogs import choose_value
from ui.theme import COLORS, FONT_FAMILY, apply_theme


SETUP_TYPES = (
    "Support Bounce",
    "Higher-Low Reversal",
    "Breakout Retest",
    "Trend Pullback",
    "Failed Breakout",
    "News Catalyst",
    "Bad Trade",
)
EMOTIONS = ("Calm", "Confident", "FOMO", "Revenge", "Uncertain", "Tired")
CHECKLIST_ITEMS = (
    "Support confirmed?",
    "Entry near support?",
    "Stop-loss defined?",
    "Take-profit defined?",
    "Risk:Reward >= 2?",
    "Emotion calm?",
    "Market/sector agrees?",
    "Not revenge trading?",
    "Daily loss limit not hit?",
    "Max trades per day not exceeded?",
)
RISK_BUTTONS = ("3", "5", "10", "20", "50")
FX_CURRENCIES = ("USD", "EUR", "CHF", "JPY", "CAD", "AUD", "NZD")
DEFAULT_SETTINGS = {
    "default_risk": "10",
    "hard_max_risk": "50",
    "default_buffer": "0.8",
    "daily_loss_limit": "150",
    "max_trades_per_day": "3",
    "default_exposure_limit": "2000",
    "fx_USD": "0.79",
    "fx_EUR": "0.86",
    "fx_CHF": "0.88",
    "fx_JPY": "0.0052",
    "fx_CAD": "0.58",
    "fx_AUD": "0.52",
    "fx_NZD": "0.48",
}


class TradingRiskCockpit(ctk.CTk):
    def __init__(self) -> None:
        apply_theme()
        super().__init__()
        self.title("Trading Risk Cockpit")
        self.geometry("1500x930")
        self.minsize(1260, 780)
        self.configure(fg_color=COLORS["bg"])

        self.db = TradingDatabase()
        self.catalog = InstrumentCatalog()
        self.market_data = MarketDataService(load_env())
        self.current_result = None
        self.selected_trade_id: int | None = None
        self.current_instrument: Instrument | None = None
        self.advanced_visible = tk.BooleanVar(value=False)
        self.setting_vars: dict[str, tk.StringVar] = {}
        self.api_vars: dict[str, tk.StringVar] = {}
        self.fields: dict[str, LabeledEntry] = {}
        self.metric_cards: dict[str, MetricCard] = {}
        self.summary_labels: dict[str, ctk.CTkLabel] = {}
        self.check_vars: list[tk.BooleanVar] = []

        self._build_shell()
        self._load_settings()
        self._load_api_settings()
        self._apply_defaults()
        self.refresh_journal()
        self.refresh_dashboard()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_shell(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self.tabs = ctk.CTkTabview(self, fg_color=COLORS["bg"], segmented_button_fg_color=COLORS["surface_soft"])
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.calculator_tab = self.tabs.add("Calculator")
        self.journal_tab = self.tabs.add("Journal")
        self.dashboard_tab = self.tabs.add("Dashboard")
        self.settings_tab = self.tabs.add("Settings")
        self._build_calculator_tab()
        self._build_journal_tab()
        self._build_dashboard_tab()
        self._build_settings_tab()
        self.toast = Toast(self)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="#172033", corner_radius=0, height=68)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="Trading Risk Cockpit", font=(FONT_FAMILY, 24, "bold"), text_color="#ffffff").grid(
            row=0, column=0, sticky="w", padx=22, pady=16
        )
        status = ctk.CTkFrame(header, fg_color="transparent")
        status.grid(row=0, column=2, sticky="e", padx=22)
        self.api_badge = Pill(status, "API: Manual", "muted")
        self.api_badge.pack(side="left", padx=5)
        self.instrument_badge = Pill(status, "AMD", "info")
        self.instrument_badge.pack(side="left", padx=5)
        self.last_sync_label = ctk.CTkLabel(
            status, text="Last sync: never", font=(FONT_FAMILY, 12), text_color="#cbd5e1"
        )
        self.last_sync_label.pack(side="left", padx=(10, 0))
        self.theme_badge = Pill(status, "Light", "muted")
        self.theme_badge.pack(side="left", padx=5)

    def _build_calculator_tab(self) -> None:
        tab = self.calculator_tab
        tab.grid_columnconfigure((0, 1, 2), weight=1, uniform="cols")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=0)

        self.input_panel = Card(tab)
        self.input_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(4, 12))
        self.quality_panel = Card(tab)
        self.quality_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=(4, 12))
        self.summary_panel = Card(tab)
        self.summary_panel.grid(row=0, column=2, sticky="nsew", pady=(4, 12))
        self.bottom_panel = ctk.CTkFrame(tab, fg_color="transparent")
        self.bottom_panel.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.bottom_panel.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._build_input_panel()
        self._build_quality_panel()
        self._build_summary_panel()
        self._build_bottom_panel()

    def _section_title(self, master, title: str, subtitle: str = "") -> None:
        ctk.CTkLabel(master, text=title, font=(FONT_FAMILY, 19, "bold"), text_color=COLORS["text"]).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                master,
                text=subtitle,
                font=(FONT_FAMILY, 12),
                text_color=COLORS["muted"],
                wraplength=380,
                justify="left",
            ).pack(anchor="w", pady=(2, 14))

    def _build_input_panel(self) -> None:
        panel = self.input_panel
        panel.grid_columnconfigure(0, weight=1)
        self._section_title(panel, "Trade Input", "Type a symbol, select a match, then press Enter to calculate.")

        self.fields["instrument"] = LabeledEntry(panel, "Instrument / ticker", "TSLA, Tesla, QQQ, VUAG")
        self.fields["instrument"].pack(fill="x", padx=18, pady=(2, 8))
        self.fields["instrument"].entry.bind("<KeyRelease>", self._on_instrument_key)
        self.fields["instrument"].entry.bind("<Return>", lambda _event: self.calculate())

        self.suggestion_box = tk.Listbox(
            panel,
            height=5,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            selectbackground=COLORS["accent"],
            font=(FONT_FAMILY, 12),
            activestyle="none",
        )
        self.suggestion_box.pack_forget()
        self.suggestion_box.bind("<<ListboxSelect>>", self._select_suggestion)
        self.suggestions: list[Instrument] = []

        ctk.CTkLabel(panel, text="Direction", font=(FONT_FAMILY, 12, "bold"), text_color=COLORS["muted"]).pack(
            anchor="w", padx=18, pady=(2, 4)
        )
        self.direction_var = tk.StringVar(value="Long")
        self.direction = ctk.CTkSegmentedButton(panel, values=list(DIRECTIONS), variable=self.direction_var, height=36)
        self.direction.pack(fill="x", padx=18, pady=(0, 10))

        for key, label, placeholder in (
            ("entry", "Entry price", "160.00"),
            ("stop", "Stop price", "155.00"),
            ("take_profit", "Take profit price", "172.00"),
            ("max_risk", "Max GBP risk", "10"),
        ):
            self.fields[key] = LabeledEntry(panel, label, placeholder)
            self.fields[key].pack(fill="x", padx=18, pady=(0, 8))
            self.fields[key].entry.bind("<Return>", lambda _event: self.calculate())

        action_row = ctk.CTkFrame(panel, fg_color="transparent")
        action_row.pack(fill="x", padx=18, pady=(0, 12))
        for risk in RISK_BUTTONS:
            ctk.CTkButton(
                action_row,
                text=f"GBP {risk}",
                width=62,
                height=30,
                corner_radius=16,
                fg_color=COLORS["surface_soft"],
                text_color=COLORS["text"],
                hover_color="#e7eef8",
                command=lambda value=risk: self.fields["max_risk"].set(value),
            ).pack(side="left", padx=(0, 6))

        refresh_row = ctk.CTkFrame(panel, fg_color="transparent")
        refresh_row.pack(fill="x", padx=18, pady=(0, 8))
        ctk.CTkButton(refresh_row, text="Refresh price", height=34, corner_radius=16, command=self.refresh_price_async).pack(
            side="left", fill="x", expand=True, padx=(0, 6)
        )
        ctk.CTkButton(
            refresh_row,
            text="Refresh FX",
            height=34,
            corner_radius=16,
            fg_color=COLORS["surface_soft"],
            text_color=COLORS["text"],
            hover_color="#e7eef8",
            command=self.refresh_fx_async,
        ).pack(side="left", fill="x", expand=True)

        self.price_status = ctk.CTkLabel(
            panel,
            text="Price: manual entry active",
            text_color=COLORS["muted"],
            font=(FONT_FAMILY, 12),
            wraplength=390,
            justify="left",
        )
        self.price_status.pack(anchor="w", padx=18, pady=(0, 10))

        self.advanced_switch = ctk.CTkSwitch(
            panel, text="Show advanced settings", variable=self.advanced_visible, command=self._toggle_advanced
        )
        self.advanced_switch.pack(anchor="w", padx=18, pady=(4, 8))
        self.advanced_frame = ctk.CTkFrame(panel, fg_color=COLORS["surface_alt"], corner_radius=16)
        self._build_advanced_fields()

        actions = ctk.CTkFrame(panel, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(14, 18))
        ctk.CTkButton(actions, text="Calculate", height=42, corner_radius=16, command=self.calculate).pack(
            side="left", fill="x", expand=True, padx=(0, 7)
        )
        ctk.CTkButton(actions, text="Save", height=42, corner_radius=16, fg_color=COLORS["surface_soft"], text_color=COLORS["text"], command=self.save_trade).pack(
            side="left", fill="x", expand=True, padx=7
        )
        ctk.CTkButton(actions, text="Clear", height=42, corner_radius=16, fg_color=COLORS["surface_soft"], text_color=COLORS["text"], command=self.clear_form).pack(
            side="left", fill="x", expand=True, padx=(7, 0)
        )

        Tooltip(self.fields["leverage"].entry if "leverage" in self.fields else self.fields["max_risk"].entry, "Leverage affects margin only. P/L is calculated from exposure.")

    def _build_advanced_fields(self) -> None:
        self.advanced_frame.grid_columnconfigure((0, 1), weight=1)
        self.asset_type_var = tk.StringVar(value="CFD")
        self.currency_var = tk.StringVar(value="USD")
        ctk.CTkLabel(self.advanced_frame, text="Asset type", text_color=COLORS["muted"], font=(FONT_FAMILY, 12, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 4)
        )
        ctk.CTkOptionMenu(self.advanced_frame, values=list(ASSET_TYPES), variable=self.asset_type_var, height=36).grid(
            row=1, column=0, sticky="ew", padx=14, pady=(0, 8)
        )
        ctk.CTkLabel(self.advanced_frame, text="Currency", text_color=COLORS["muted"], font=(FONT_FAMILY, 12, "bold")).grid(
            row=0, column=1, sticky="w", padx=14, pady=(14, 4)
        )
        ctk.CTkOptionMenu(self.advanced_frame, values=list(CURRENCIES), variable=self.currency_var, height=36).grid(
            row=1, column=1, sticky="ew", padx=14, pady=(0, 8)
        )
        for idx, (key, label, placeholder) in enumerate(
            (
                ("leverage", "Leverage", "5"),
                ("fx_rate", "FX rate to GBP", "0.79"),
                ("support", "Support / resistance", "same as stop"),
                ("buffer", "Buffer %", "0.8"),
                ("spread", "Spread cost", "0"),
                ("overnight", "Overnight fee", "0"),
                ("commission", "Commission", "0"),
                ("screenshot", "Screenshot path", "optional"),
            ),
            start=2,
        ):
            col = (idx - 2) % 2
            row = 2 + ((idx - 2) // 2) * 2
            self.fields[key] = LabeledEntry(self.advanced_frame, label, placeholder)
            self.fields[key].grid(row=row, column=col, sticky="ew", padx=14, pady=(0, 10))
        self.notes = ctk.CTkTextbox(self.advanced_frame, height=76, corner_radius=14, fg_color=COLORS["surface"], border_width=1, border_color=COLORS["border"])
        ctk.CTkLabel(self.advanced_frame, text="Notes", text_color=COLORS["muted"], font=(FONT_FAMILY, 12, "bold")).grid(
            row=10, column=0, columnspan=2, sticky="w", padx=14, pady=(4, 4)
        )
        self.notes.grid(row=11, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 14))
        self.checklist_frame = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        self.checklist_frame.grid(row=12, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 14))
        self.checklist_frame.grid_columnconfigure((0, 1), weight=1)
        for idx, text in enumerate(CHECKLIST_ITEMS):
            var = tk.BooleanVar(value=False)
            ctk.CTkCheckBox(self.checklist_frame, text=text, variable=var, font=(FONT_FAMILY, 11)).grid(
                row=idx // 2, column=idx % 2, sticky="w", pady=3
            )
            self.check_vars.append(var)
        self.grade_label = ctk.CTkLabel(self.advanced_frame, text="Trade grade: F", text_color=COLORS["danger"], font=(FONT_FAMILY, 13, "bold"))
        self.grade_label.grid(row=13, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 14))

    def _build_quality_panel(self) -> None:
        self.quality_panel.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(self.quality_panel, text="Trade Quality", font=(FONT_FAMILY, 19, "bold"), text_color=COLORS["text"]).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 4)
        )
        ctk.CTkLabel(
            self.quality_panel,
            text="Decision support updates instantly after calculation.",
            font=(FONT_FAMILY, 12),
            text_color=COLORS["muted"],
            wraplength=420,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12))
        for idx, title in enumerate(
            ("Risk:Reward", "Stop-loss %", "Entry distance", "Risk size", "Exposure size", "Margin required", "Overall verdict")
        ):
            card = MetricCard(self.quality_panel, title)
            card.grid(row=2 + idx // 2, column=idx % 2, sticky="nsew", padx=8, pady=8)
            self.metric_cards[title] = card

    def _build_summary_panel(self) -> None:
        self.summary_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.summary_panel, text="Trade Summary", font=(FONT_FAMILY, 19, "bold"), text_color=COLORS["text"]).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 12)
        )
        sections = [
            ("Position", [("Units", "units"), ("Leverage", "leverage"), ("Stop distance", "stop_distance")]),
            ("Exposure & Margin", [("Exposure GBP", "exposure_gbp"), ("Margin GBP", "margin_gbp"), ("Exposure local", "exposure_local"), ("Margin local", "margin_local")]),
            ("Profit / Loss", [("Potential profit", "profit"), ("Potential loss", "loss"), ("Net expected profit", "net_profit")]),
            ("Validation", [("Risk:Reward", "rr"), ("Trade valid?", "valid"), ("Risk label", "label"), ("P/L basis", "basis")]),
        ]
        row = 1
        for title, rows in sections:
            card = Card(self.summary_panel)
            card.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(card, text=title, font=(FONT_FAMILY, 14, "bold"), text_color=COLORS["text"]).grid(
                row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6)
            )
            for idx, (label, key) in enumerate(rows, start=1):
                ctk.CTkLabel(card, text=label, font=(FONT_FAMILY, 12), text_color=COLORS["muted"], anchor="w").grid(
                    row=idx, column=0, sticky="w", padx=14, pady=4
                )
                value = ctk.CTkLabel(card, text="-", font=(FONT_FAMILY, 13, "bold"), text_color=COLORS["text"], anchor="e", justify="right", wraplength=220)
                value.grid(row=idx, column=1, sticky="e", padx=14, pady=4)
                self.summary_labels[key] = value
            row += 1
        self.warning_frame = ctk.CTkFrame(self.summary_panel, fg_color="transparent")
        self.warning_frame.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 18))

    def _build_bottom_panel(self) -> None:
        self.improve_card = Card(self.bottom_panel)
        self.rules_card = Card(self.bottom_panel)
        self.recent_card = Card(self.bottom_panel)
        self.notes_card = Card(self.bottom_panel)
        for idx, card in enumerate((self.improve_card, self.rules_card, self.recent_card, self.notes_card)):
            card.grid(row=0, column=idx, sticky="nsew", padx=(0 if idx == 0 else 10, 0))
        self._card_heading(self.improve_card, "What must improve?")
        self.improve_list = ctk.CTkFrame(self.improve_card, fg_color="transparent")
        self.improve_list.pack(fill="x", padx=14, pady=(0, 14))
        self._write_improvements(["No calculation yet"])
        self._card_heading(self.rules_card, "Pre-trade rules")
        for rule in (
            "No calculator = no trade",
            "Buy low only when support is confirmed",
            "Risk is based on exposure, not margin",
            "Small position first. Let winners grow",
            "Stop-loss goes where the idea is invalidated",
        ):
            ctk.CTkLabel(self.rules_card, text=f"- {rule}", text_color=COLORS["muted"], font=(FONT_FAMILY, 11), wraplength=300).pack(
                anchor="w", padx=14, pady=1
            )
        self._card_heading(self.recent_card, "Recent activity")
        self.recent_list = ctk.CTkFrame(self.recent_card, fg_color="transparent")
        self.recent_list.pack(fill="x", padx=14, pady=(0, 14))
        self._card_heading(self.notes_card, "Quick notes")
        self.quick_notes = ctk.CTkTextbox(self.notes_card, height=96, corner_radius=14, fg_color=COLORS["surface_alt"])
        self.quick_notes.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _card_heading(self, card: Card, title: str) -> None:
        ctk.CTkLabel(card, text=title, font=(FONT_FAMILY, 14, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=14, pady=(12, 8))

    def _build_journal_tab(self) -> None:
        tab = self.journal_tab
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        controls = Card(tab)
        controls.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 12))
        ctk.CTkLabel(controls, text="Trade Journal", font=(FONT_FAMILY, 20, "bold"), text_color=COLORS["text"]).pack(side="left", padx=16, pady=14)
        for text, cmd in (("Update Result", self.update_selected_result), ("Export CSV", self.export_csv), ("Delete", self.delete_selected_trade)):
            ctk.CTkButton(controls, text=text, height=34, corner_radius=16, fg_color=COLORS["surface_soft"], text_color=COLORS["text"], command=cmd).pack(
                side="left", padx=6
            )
        table_frame = Card(tab)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=32, font=(FONT_FAMILY, 11), borderwidth=0)
        style.configure("Treeview.Heading", font=(FONT_FAMILY, 11, "bold"))
        self.tree = ttk.Treeview(table_frame, columns=TRADE_COLUMNS, show="headings", selectmode="browse")
        for column in TRADE_COLUMNS:
            self.tree.heading(column, text=column.replace("_", " ").title(), command=lambda c=column: self._sort_tree(c, False))
            self.tree.column(column, width=100 if column not in {"notes", "lesson_learned"} else 210, minwidth=80, stretch=True)
        self.tree.tag_configure("win", foreground=COLORS["success"])
        self.tree.tag_configure("loss", foreground=COLORS["danger"])
        self.tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_trade_select)

    def _build_dashboard_tab(self) -> None:
        tab = self.dashboard_tab
        tab.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.metric_labels: dict[str, ctk.CTkLabel] = {}
        for idx, label in enumerate(("Total trades", "Win rate %", "Average R multiple", "Total P/L", "Average win", "Average loss", "Best trade", "Worst trade")):
            card = Card(tab)
            card.grid(row=idx // 4, column=idx % 4, sticky="ew", padx=8, pady=8)
            ctk.CTkLabel(card, text=label, font=(FONT_FAMILY, 12, "bold"), text_color=COLORS["muted"]).pack(anchor="w", padx=14, pady=(12, 0))
            value = ctk.CTkLabel(card, text="-", font=(FONT_FAMILY, 20, "bold"), text_color=COLORS["text"])
            value.pack(anchor="w", padx=14, pady=(4, 14))
            self.metric_labels[label] = value
        self.dashboard_detail = Card(tab)
        self.dashboard_detail.grid(row=2, column=0, columnspan=4, sticky="ew", padx=8, pady=12)
        self.dashboard_detail.grid_columnconfigure(1, weight=1)
        for idx, label in enumerate(("Profit factor", "Best instrument", "Worst instrument", "Most profitable setup", "Most common mistake", "Daily P/L", "Daily loss limit status", "Trades taken today", "Max trades per day status")):
            ctk.CTkLabel(self.dashboard_detail, text=label, font=(FONT_FAMILY, 12), text_color=COLORS["muted"]).grid(row=idx, column=0, sticky="w", padx=16, pady=5)
            value = ctk.CTkLabel(self.dashboard_detail, text="-", font=(FONT_FAMILY, 12, "bold"), text_color=COLORS["text"])
            value.grid(row=idx, column=1, sticky="e", padx=16, pady=5)
            self.metric_labels[label] = value

    def _build_settings_tab(self) -> None:
        tab = self.settings_tab
        tab.grid_columnconfigure((0, 1), weight=1)
        left = Card(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(4, 10), pady=4)
        right = Card(tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 4), pady=4)
        self._settings_section(left, "Risk defaults", [("Default risk", "default_risk"), ("Hard max risk", "hard_max_risk"), ("Default buffer %", "default_buffer"), ("Default exposure limit", "default_exposure_limit"), ("Max daily loss", "daily_loss_limit"), ("Max trades/day", "max_trades_per_day")])
        self._settings_section(left, "FX defaults", [(currency, f"fx_{currency}") for currency in FX_CURRENCIES])
        self._api_settings(right)

    def _settings_section(self, master, title: str, rows: list[tuple[str, str]]) -> None:
        ctk.CTkLabel(master, text=title, font=(FONT_FAMILY, 16, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(18, 8))
        for label, key in rows:
            entry = LabeledEntry(master, label)
            entry.pack(fill="x", padx=18, pady=(0, 8))
            self.setting_vars[key] = entry.var
        ctk.CTkButton(master, text="Save Settings", height=38, corner_radius=16, command=self.save_settings).pack(fill="x", padx=18, pady=(8, 18))

    def _api_settings(self, master) -> None:
        ctk.CTkLabel(master, text="API Keys", font=(FONT_FAMILY, 16, "bold"), text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(master, text="Stored locally in .env and ignored by Git. Read-only market data only.", font=(FONT_FAMILY, 12), text_color=COLORS["muted"], wraplength=450).pack(anchor="w", padx=18, pady=(0, 12))
        for label, key, secret in (
            ("Trading 212 API key", "TRADING212_API_KEY", True),
            ("IG API key", "IG_API_KEY", True),
            ("IG username", "IG_USERNAME", False),
            ("IG password", "IG_PASSWORD", True),
            ("IG account type", "IG_ACCOUNT_TYPE", False),
            ("Twelve Data API key", "TWELVE_DATA_API_KEY", True),
            ("Market data API key", "MARKET_DATA_API_KEY", True),
        ):
            entry = LabeledEntry(master, label, show="*" if secret else None)
            entry.pack(fill="x", padx=18, pady=(0, 8))
            self.api_vars[key] = entry.var
        ctk.CTkButton(master, text="Save API Keys", height=38, corner_radius=16, command=self.save_api_settings).pack(fill="x", padx=18, pady=(8, 18))

    def _on_instrument_key(self, _event=None) -> None:
        query = self.fields["instrument"].get()
        self.suggestions = self.catalog.search(query)
        if not self.suggestions:
            self.suggestion_box.pack_forget()
            self._apply_profile_if_exact(query)
            return
        self.suggestion_box.delete(0, "end")
        for item in self.suggestions:
            self.suggestion_box.insert("end", f"{item.ticker}  |  {item.display_name}  |  {item.category}")
        self.suggestion_box.pack(fill="x", padx=18, pady=(0, 10), after=self.fields["instrument"])
        self._apply_profile_if_exact(query)

    def _select_suggestion(self, _event=None) -> None:
        selection = self.suggestion_box.curselection()
        if not selection:
            return
        instrument = self.suggestions[selection[0]]
        self.suggestion_box.pack_forget()
        self._apply_instrument(instrument, refresh=True)

    def _apply_profile_if_exact(self, query: str) -> None:
        instrument = self.catalog.by_ticker(query)
        if instrument:
            self._apply_instrument(instrument, refresh=False)

    def _apply_instrument(self, instrument: Instrument, refresh: bool) -> None:
        self.current_instrument = instrument
        self.fields["instrument"].set(instrument.ticker)
        self.asset_type_var.set(instrument.asset_type)
        self.currency_var.set(instrument.currency)
        self.fields["leverage"].set(f"{instrument.leverage_default:g}")
        self.fields["fx_rate"].set("1" if instrument.currency == "GBP" else self.db.get_setting(f"fx_{instrument.currency}", DEFAULT_SETTINGS.get(f"fx_{instrument.currency}", "1")))
        self.instrument_badge.set_status("info", instrument.ticker)
        if refresh:
            self.refresh_price_async()
            self.refresh_fx_async()

    def _toggle_advanced(self) -> None:
        if self.advanced_visible.get():
            self.advanced_frame.pack(fill="x", padx=18, pady=(0, 8))
        else:
            self.advanced_frame.pack_forget()

    def _apply_defaults(self) -> None:
        values = {"instrument": "AMD", "entry": "160", "stop": "155", "take_profit": "172", "max_risk": self.db.get_setting("default_risk", DEFAULT_SETTINGS["default_risk"]), "buffer": self.db.get_setting("default_buffer", DEFAULT_SETTINGS["default_buffer"]), "spread": "0", "overnight": "0", "commission": "0", "support": ""}
        for key, value in values.items():
            if key in self.fields:
                self.fields[key].set(value)
        amd = self.catalog.by_ticker("AMD")
        if amd:
            self._apply_instrument(amd, refresh=False)

    def _float(self, key: str, default: float = 0.0) -> float:
        raw = self.fields[key].get().replace(",", "").strip()
        return float(raw) if raw else default

    def _setting_float(self, key: str, fallback: str | float) -> float:
        try:
            return float(self.db.get_setting(key, str(fallback)).replace(",", ""))
        except ValueError:
            return float(fallback)

    def _trade_inputs(self) -> TradeInputs:
        entry = self._float("entry")
        stop = self._float("stop")
        return TradeInputs(
            instrument=self.fields["instrument"].get().strip().upper(),
            asset_type=self.asset_type_var.get(),
            currency=self.currency_var.get(),
            fx_rate_to_gbp=self._float("fx_rate", 1.0),
            direction=self.direction_var.get(),
            entry_price=entry,
            stop_price=stop,
            take_profit_price=self._float("take_profit"),
            max_risk_gbp=self._float("max_risk"),
            support_line=self._float("support", stop or entry),
            buffer_percent=self._float("buffer", self._setting_float("default_buffer", DEFAULT_SETTINGS["default_buffer"])) / 100,
            leverage=self._float("leverage", 1.0),
            spread_cost=self._float("spread"),
            overnight_fee=self._float("overnight"),
            commission=self._float("commission"),
            notes=self.notes.get("1.0", "end").strip(),
        )

    def calculate(self) -> None:
        try:
            values = self._trade_inputs()
        except ValueError:
            self.toast.show("Check numeric fields.")
            return
        result = calculate_trade(values)
        self.current_result = result
        self._update_summary(values, result)
        self._update_quality(values, result)
        self._sync_checklist(result)
        self.refresh_dashboard()

    def _update_summary(self, values: TradeInputs, result) -> None:
        data = {
            "units": f"{result.units:.4f}",
            "leverage": f"{result.leverage:g}x",
            "stop_distance": f"{result.stop_distance:.4f}",
            "exposure_gbp": f"GBP {result.exposure_gbp:,.2f}",
            "margin_gbp": f"GBP {result.required_margin_gbp:,.2f}",
            "exposure_local": f"{result.exposure_local:,.2f} {values.currency}",
            "margin_local": f"{result.required_margin_local:,.2f} {values.currency}",
            "profit": f"GBP {result.potential_profit_gbp:,.2f}",
            "loss": f"GBP {result.potential_loss_gbp:,.2f}",
            "net_profit": f"GBP {result.net_expected_profit_gbp:,.2f}",
            "rr": f"{result.risk_reward:.2f}",
            "valid": "YES" if result.valid else "NO",
            "label": result.risk_label,
            "basis": "Exposure, not margin",
        }
        for key, value in data.items():
            label = self.summary_labels[key]
            label.configure(text=value, text_color=COLORS["success"] if key in {"profit", "valid"} and result.valid else COLORS["danger"] if key in {"loss", "valid"} and not result.valid else COLORS["text"])
        self._write_warnings(result.errors + result.warnings)

    def _update_quality(self, values: TradeInputs, result) -> None:
        assessments, reasons = quality_assessments(
            values,
            result,
            self._setting_float("default_risk", DEFAULT_SETTINGS["default_risk"]),
            self._setting_float("hard_max_risk", DEFAULT_SETTINGS["hard_max_risk"]),
            self._setting_float("default_exposure_limit", DEFAULT_SETTINGS["default_exposure_limit"]),
            self._daily_loss_hit(),
            self._max_trades_hit(),
        )
        for name, assessment in assessments.items():
            self.metric_cards[name].update_metric(assessment["value"], assessment["target"], assessment["status"], assessment["hint"])
        self._write_improvements(reasons)

    def _write_improvements(self, reasons: list[str]) -> None:
        for child in self.improve_list.winfo_children():
            child.destroy()
        for reason in reasons[:6]:
            status = "good" if reason == "No major issues" else "muted"
            text = f"OK {reason}" if status == "good" else f"- {reason}"
            ctk.CTkLabel(
                self.improve_list,
                text=text,
                font=(FONT_FAMILY, 12),
                text_color=COLORS["success"] if status == "good" else COLORS["muted"],
                wraplength=320,
                justify="left",
            ).pack(anchor="w", pady=1)

    def _write_warnings(self, warnings: list[str]) -> None:
        for child in self.warning_frame.winfo_children():
            child.destroy()
        for warning in (warnings or ["No warnings."])[:7]:
            ctk.CTkLabel(
                self.warning_frame,
                text=f"- {warning}",
                text_color=COLORS["danger"] if "must" in warning.lower() or "invalid" in warning.lower() else COLORS["warning"],
                font=(FONT_FAMILY, 12),
                wraplength=410,
                justify="left",
            ).pack(anchor="w", pady=2)

    def _sync_checklist(self, result) -> None:
        auto = [True, True, result.stop_distance > 0, result.potential_profit_gbp > 0, result.risk_reward >= 2, True, True, True, not self._daily_loss_hit(), not self._max_trades_hit()]
        for var, value in zip(self.check_vars, auto):
            var.set(value)
        grade = grade_checklist(sum(var.get() for var in self.check_vars), len(self.check_vars), not result.valid)
        self.grade_label.configure(text=f"Trade grade: {grade}", text_color=COLORS["success"] if grade in {"A", "B"} else COLORS["danger"])

    def refresh_price_async(self) -> None:
        instrument = self.fields["instrument"].get().strip().upper()
        if not instrument:
            return
        self.api_badge.set_status("info", "API: Loading")
        self.price_status.configure(text="Fetching latest price...")
        threading.Thread(target=self._refresh_price_worker, args=(instrument,), daemon=True).start()

    def _refresh_price_worker(self, instrument: str) -> None:
        quote = self.market_data.latest_price(instrument)
        self.after(0, lambda: self._handle_price_quote(quote))

    def _handle_price_quote(self, quote) -> None:
        if quote is None:
            self.api_badge.set_status("bad", "API: Offline")
            self.price_status.configure(text="Price unavailable. Manual entry remains active.")
            return
        self.fields["entry"].set(f"{quote.value:.4f}")
        self.api_badge.set_status("good" if quote.source == "Twelve Data" else "ok", f"API: {quote.source}")
        self.last_sync_label.configure(text=f"Last sync: {quote.timestamp}")
        self.price_status.configure(text=f"Latest {quote.value:.4f} from {quote.source} at {quote.timestamp}. Use broker price for final execution.")

    def refresh_fx_async(self) -> None:
        currency = self.currency_var.get()
        threading.Thread(target=self._refresh_fx_worker, args=(currency,), daemon=True).start()

    def _refresh_fx_worker(self, currency: str) -> None:
        quote = self.market_data.latest_fx_to_gbp(currency)
        self.after(0, lambda: self._handle_fx_quote(quote))

    def _handle_fx_quote(self, quote) -> None:
        if quote is None:
            self.api_badge.set_status("bad", "API: Fallback")
            return
        self.fields["fx_rate"].set(f"{quote.value:.6f}")
        self.api_badge.set_status("good" if quote.source == "Twelve Data" else "ok", f"API: {quote.source}")
        self.last_sync_label.configure(text=f"Last sync: {quote.timestamp}")

    def save_trade(self) -> None:
        if self.current_result is None:
            self.calculate()
        if self.current_result is None:
            return
        values = self._trade_inputs()
        if not self.current_result.valid and not messagebox.askyesno("Invalid trade", "This trade is invalid. Save it anyway?"):
            return
        data = {
            "created_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "instrument": values.instrument or "Unknown",
            "asset_type": values.asset_type,
            "currency": values.currency,
            "fx_rate": values.fx_rate_to_gbp,
            "direction": values.direction,
            "entry": values.entry_price,
            "stop": values.stop_price,
            "take_profit": values.take_profit_price,
            "max_risk": values.max_risk_gbp,
            "units": self.current_result.units,
            "exposure_gbp": self.current_result.exposure_gbp,
            "potential_profit": self.current_result.potential_profit_gbp,
            "risk_reward": self.current_result.risk_reward,
            "setup_type": choose_value(self, "Setup type", SETUP_TYPES, "Support Bounce"),
            "emotion_before": choose_value(self, "Emotion before trade", EMOTIONS, "Calm"),
            "result_gbp": 0,
            "win_loss": "",
            "r_multiple": 0,
            "mistake_made": "",
            "lesson_learned": "",
            "screenshot_path": self.fields["screenshot"].get(),
            "notes": values.notes,
        }
        self.db.add_trade(data)
        self.refresh_journal()
        self.refresh_dashboard()
        self.toast.show("Trade saved.")

    def clear_form(self) -> None:
        for key in ("entry", "stop", "take_profit", "support", "spread", "overnight", "commission", "screenshot"):
            if key in self.fields:
                self.fields[key].set("")
        self.notes.delete("1.0", "end")
        self.current_result = None
        self._write_improvements(["No calculation yet"])
        self._write_warnings([])
        for label in self.summary_labels.values():
            label.configure(text="-", text_color=COLORS["text"])

    def refresh_journal(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.db.all_trades():
            result = float(row["result_gbp"] or 0)
            tag = "win" if result > 0 else "loss" if result < 0 else ""
            self.tree.insert("", "end", iid=str(row["id"]), values=[row[col] for col in TRADE_COLUMNS], tags=(tag,) if tag else ())
        self._refresh_recent()

    def _refresh_recent(self) -> None:
        for child in self.recent_list.winfo_children():
            child.destroy()
        rows = self.db.all_trades()[:4]
        if not rows:
            ctk.CTkLabel(self.recent_list, text="No saved trades yet.", text_color=COLORS["muted"], font=(FONT_FAMILY, 12)).pack(anchor="w")
            return
        for row in rows:
            ctk.CTkLabel(
                self.recent_list,
                text=f"{row['instrument']} | {row['direction']} | R:R {float(row['risk_reward'] or 0):.2f}",
                text_color=COLORS["muted"],
                font=(FONT_FAMILY, 12),
                wraplength=300,
            ).pack(anchor="w", pady=1)

    def _on_trade_select(self, _event=None) -> None:
        selection = self.tree.selection()
        self.selected_trade_id = int(selection[0]) if selection else None

    def _sort_tree(self, column: str, reverse: bool) -> None:
        rows = [(self.tree.set(item, column), item) for item in self.tree.get_children("")]
        try:
            rows.sort(key=lambda item: float(str(item[0]).replace(",", "")), reverse=reverse)
        except ValueError:
            rows.sort(key=lambda item: str(item[0]).lower(), reverse=reverse)
        for index, (_value, item) in enumerate(rows):
            self.tree.move(item, "", index)
        self.tree.heading(column, command=lambda: self._sort_tree(column, not reverse))

    def delete_selected_trade(self) -> None:
        if self.selected_trade_id is None:
            self.toast.show("Select a trade first.")
            return
        if messagebox.askyesno("Delete trade", "Delete selected trade?"):
            self.db.delete_trade(self.selected_trade_id)
            self.selected_trade_id = None
            self.refresh_journal()
            self.refresh_dashboard()

    def update_selected_result(self) -> None:
        if self.selected_trade_id is None:
            self.toast.show("Select a trade first.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Update result")
        dialog.geometry("420x360")
        dialog.transient(self)
        dialog.grab_set()
        entries: dict[str, LabeledEntry] = {}
        for key, label in (("result", "Result GBP"), ("r", "R multiple"), ("mistake", "Mistake made?"), ("lesson", "Lesson learned")):
            entry = LabeledEntry(dialog, label)
            entry.pack(fill="x", padx=20, pady=(14 if not entries else 4, 4))
            entries[key] = entry
        win_loss = ctk.CTkOptionMenu(dialog, values=["Win", "Loss", "Breakeven"])
        win_loss.set("Win")
        win_loss.pack(fill="x", padx=20, pady=8)

        def save() -> None:
            try:
                result = float(entries["result"].get() or 0)
                r_multiple = float(entries["r"].get() or 0)
            except ValueError:
                self.toast.show("Result and R multiple must be numbers.")
                return
            self.db.update_result(self.selected_trade_id, result, win_loss.get(), r_multiple, entries["mistake"].get(), entries["lesson"].get())
            dialog.destroy()
            self.refresh_journal()
            self.refresh_dashboard()

        ctk.CTkButton(dialog, text="Save", command=save).pack(fill="x", padx=20, pady=18)

    def export_csv(self) -> None:
        default = Path("exports") / f"trading-risk-cockpit-{dt.date.today().isoformat()}.csv"
        default.parent.mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=default.name, initialdir=str(default.parent.resolve()), filetypes=(("CSV files", "*.csv"), ("All files", "*.*")))
        if path:
            self.db.export_csv(path)
            self.toast.show("CSV exported.")

    def refresh_dashboard(self) -> None:
        rows = self.db.all_trades()
        results = [float(row["result_gbp"] or 0) for row in rows]
        wins = [value for value in results if value > 0]
        losses = [value for value in results if value < 0]
        total = len(rows)
        total_pl = sum(results)
        win_rate = (len(wins) / total * 100) if total else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        avg_r = sum(float(row["r_multiple"] or 0) for row in rows) / total if total else 0
        today = self.db.trades_today(dt.date.today().isoformat())
        daily_pl = sum(float(row["result_gbp"] or 0) for row in today)
        values = {
            "Total trades": str(total),
            "Win rate %": f"{win_rate:.1f}%",
            "Average R multiple": f"{avg_r:.2f}",
            "Total P/L": f"GBP {total_pl:,.2f}",
            "Average win": f"GBP {avg_win:,.2f}",
            "Average loss": f"GBP {avg_loss:,.2f}",
            "Best trade": f"GBP {max(results) if results else 0:,.2f}",
            "Worst trade": f"GBP {min(results) if results else 0:,.2f}",
            "Profit factor": f"{(sum(wins) / abs(sum(losses))) if losses else 0:.2f}",
            "Best instrument": self._best_group(rows, "instrument", best=True),
            "Worst instrument": self._best_group(rows, "instrument", best=False),
            "Most profitable setup": self._best_group(rows, "setup_type", best=True),
            "Most common mistake": self._most_common_mistake(rows),
            "Daily P/L": f"GBP {daily_pl:,.2f}",
            "Daily loss limit status": "Daily loss limit hit - stop trading." if self._daily_loss_hit() else "Within limit",
            "Trades taken today": str(len(today)),
            "Max trades per day status": "Max trades reached - stop trading." if self._max_trades_hit() else "Within limit",
        }
        for key, value in values.items():
            label = self.metric_labels.get(key)
            if label:
                color = COLORS["danger"] if "-" in value or "stop trading" in value else COLORS["success"] if key in {"Total P/L", "Best trade", "Average win"} and value != "GBP 0.00" else COLORS["text"]
                label.configure(text=value, text_color=color)

    def _best_group(self, rows, field: str, best: bool) -> str:
        totals: dict[str, float] = {}
        for row in rows:
            totals[row[field] or "Unknown"] = totals.get(row[field] or "Unknown", 0) + float(row["result_gbp"] or 0)
        if not totals:
            return "-"
        key = max(totals, key=totals.get) if best else min(totals, key=totals.get)
        return f"{key} ({totals[key]:.2f})"

    def _most_common_mistake(self, rows) -> str:
        mistakes: dict[str, int] = {}
        for row in rows:
            mistake = str(row["mistake_made"] or "").strip()
            if mistake:
                mistakes[mistake] = mistakes.get(mistake, 0) + 1
        return max(mistakes, key=mistakes.get) if mistakes else "-"

    def _daily_loss_hit(self) -> bool:
        limit = abs(self._setting_float("daily_loss_limit", DEFAULT_SETTINGS["daily_loss_limit"]))
        daily_pl = sum(float(row["result_gbp"] or 0) for row in self.db.trades_today(dt.date.today().isoformat()))
        return daily_pl <= -limit

    def _max_trades_hit(self) -> bool:
        max_trades = int(self._setting_float("max_trades_per_day", DEFAULT_SETTINGS["max_trades_per_day"]))
        return len(self.db.trades_today(dt.date.today().isoformat())) >= max_trades

    def save_settings(self) -> None:
        for key, var in self.setting_vars.items():
            self.db.set_setting(key, var.get())
        self.toast.show("Settings saved.")

    def _load_settings(self) -> None:
        for key, var in self.setting_vars.items():
            var.set(self.db.get_setting(key, DEFAULT_SETTINGS.get(key, "")))

    def save_api_settings(self) -> None:
        save_env({key: var.get() for key, var in self.api_vars.items()})
        self.market_data = MarketDataService(load_env())
        self.toast.show("API keys saved to .env.")

    def _load_api_settings(self) -> None:
        values = load_env()
        for key, var in self.api_vars.items():
            var.set(values.get(key, "demo" if key == "IG_ACCOUNT_TYPE" else ""))

    def _on_close(self) -> None:
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = TradingRiskCockpit()
    app.mainloop()
