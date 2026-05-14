"""Trading Risk Cockpit tkinter application."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from calculator import ASSET_TYPES, CURRENCIES, DIRECTIONS, TradeInputs, calculate_trade, grade_checklist
from database import TRADE_COLUMNS, TradingDatabase
from market_data import MarketDataService, load_env, save_env


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

INSTRUMENT_PROFILES = {
    "TSLA": ("CFD", "USD"),
    "NVDA": ("CFD", "USD"),
    "AMD": ("CFD", "USD"),
    "MSFT": ("CFD", "USD"),
    "PLTR": ("CFD", "USD"),
    "ASML": ("CFD", "USD"),
    "TECH100": ("Index", "USD"),
    "NDX": ("Index", "USD"),
    "USA500": ("Index", "USD"),
    "SPX": ("Index", "USD"),
    "GER40": ("Index", "EUR"),
    "UK100": ("Index", "GBP"),
    "XAGUSD": ("Commodity", "USD"),
    "XAUUSD": ("Commodity", "USD"),
    "OIL": ("Commodity", "USD"),
    "CRUDE": ("Commodity", "USD"),
    "BTCUSD": ("Crypto", "USD"),
    "ETHUSD": ("Crypto", "USD"),
    "EURUSD": ("Forex", "USD"),
    "GBPUSD": ("Forex", "USD"),
    "USDJPY": ("Forex", "JPY"),
}

LEVERAGE_DEFAULTS = {
    "TSLA": 5,
    "NVDA": 5,
    "AMD": 5,
    "MSFT": 5,
    "PLTR": 5,
    "ASML": 5,
    "TECH100": 20,
    "NDX": 20,
    "USA500": 20,
    "SPX": 20,
    "GER40": 20,
    "UK100": 20,
    "XAUUSD": 20,
    "XAGUSD": 10,
    "OIL": 10,
    "CRUDE": 10,
    "BTCUSD": 2,
    "ETHUSD": 2,
    "EURUSD": 30,
    "GBPUSD": 30,
    "USDJPY": 30,
}

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


class TradingRiskCockpit(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Trading Risk Cockpit")
        self.geometry("1320x860")
        self.minsize(1120, 740)
        self.db = TradingDatabase()
        self.market_data = MarketDataService(load_env())
        self.current_result = None
        self.selected_trade_id: int | None = None
        self.advanced_visible = tk.BooleanVar(value=False)
        self.vars: dict[str, tk.Variable] = {}
        self.setting_vars: dict[str, tk.StringVar] = {}
        self.api_vars: dict[str, tk.StringVar] = {}
        self.output_labels: dict[str, ttk.Label] = {}
        self.quality_cards: dict[str, dict[str, tk.Label | tk.Frame]] = {}
        self.summary_cards: dict[str, tk.Label] = {}
        self.input_widgets: list[tk.Widget] = []
        self.improve_items: list[ttk.Label] = []
        self.check_vars: list[tk.BooleanVar] = []
        self.last_price_var = tk.StringVar(value="Last price: manual")
        self.last_fx_var = tk.StringVar(value="FX source: saved default")

        self._setup_style()
        self._build_ui()
        self._load_settings()
        self._load_api_settings()
        self._apply_quick_defaults()
        self.refresh_journal()
        self.refresh_dashboard()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        bg = "#f8fafc"
        panel = "#ffffff"
        text = "#172033"
        accent = "#2f6fed"
        border = "#dbe4ef"
        self.configure(bg=bg)
        style.configure(".", background=bg, foreground=text, font=("Helvetica Neue", 12))
        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel, relief="flat", borderwidth=0)
        style.configure("Advanced.TFrame", background=panel)
        style.configure("TLabel", background=bg, foreground=text)
        style.configure("Panel.TLabel", background=panel)
        style.configure("Header.TLabel", font=("Helvetica Neue", 22, "bold"), background=bg)
        style.configure("Subtle.TLabel", background=panel, foreground="#64748b", font=("Helvetica Neue", 10))
        style.configure("Section.TLabel", background=panel, foreground=text, font=("Helvetica Neue", 13, "bold"))
        style.configure("Rule.TLabel", font=("Helvetica Neue", 11, "bold"), background=panel, foreground="#334155")
        style.configure("TButton", padding=(12, 7), font=("Helvetica Neue", 11), borderwidth=0)
        style.configure("Accent.TButton", background=accent, foreground="#ffffff", borderwidth=0, focusthickness=1, focuscolor="#bfdbfe")
        style.map("Accent.TButton", background=[("active", "#255ec8")])
        style.configure("Secondary.TButton", background="#f1f5fb", foreground=text, borderwidth=0, focusthickness=1, focuscolor="#dbeafe")
        style.map("Secondary.TButton", background=[("active", "#e5edf7")])
        style.configure("Risk.TButton", padding=(9, 5), font=("Helvetica Neue", 11, "bold"), background="#f1f5fb")
        style.configure("TEntry", padding=(10, 8), fieldbackground="#ffffff", bordercolor=border, lightcolor=border, darkcolor=border)
        style.map("TEntry", bordercolor=[("focus", accent)], lightcolor=[("focus", accent)], darkcolor=[("focus", accent)])
        style.configure("TCombobox", padding=(10, 8), fieldbackground="#ffffff", bordercolor=border, lightcolor=border, darkcolor=border)
        style.map("TCombobox", bordercolor=[("focus", accent)])
        style.configure("Treeview", rowheight=31, font=("Helvetica Neue", 11), background="#ffffff", fieldbackground="#ffffff", borderwidth=0)
        style.configure("Treeview.Heading", font=("Helvetica Neue", 11, "bold"))
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(20, 10), font=("Helvetica Neue", 12, "bold"), background="#edf3fb", borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", "#ffffff"), ("active", "#f6f9fd")], foreground=[("selected", accent)])
        self.colors = {
            "green": "#16875a",
            "green_bg": "#e4f7ed",
            "red": "#c2413a",
            "red_bg": "#fdebea",
            "yellow": "#b7791f",
            "yellow_bg": "#fff4d6",
            "orange": "#c76a14",
            "muted": "#66758a",
            "text": text,
            "panel": panel,
            "border": border,
            "bg": bg,
            "shadow": "#e9eff7",
            "glass": "#fbfdff",
            "accent": accent,
        }

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(22, 16, 22, 2))
        header.pack(fill="x")
        ttk.Label(header, text="Trading Risk Cockpit", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="No calculator = no trade.", foreground="#b91c1c", font=("Helvetica Neue", 13, "bold")).pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=12)
        self.calculator_tab = ttk.Frame(self.notebook)
        self.journal_tab = ttk.Frame(self.notebook)
        self.dashboard_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.calculator_tab, text="Calculator")
        self.notebook.add(self.journal_tab, text="Journal")
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.settings_tab, text="Settings")

        self._build_calculator_tab()
        self._build_journal_tab()
        self._build_dashboard_tab()
        self._build_settings_tab()

    def _panel(self, parent: tk.Widget, padding: int = 16) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=padding)
        return frame

    def _card(self, parent: tk.Widget, padding: int = 16) -> tk.Frame:
        shell = tk.Frame(parent, bg=self.colors["shadow"], padx=1, pady=1)
        card = tk.Frame(
            shell,
            bg=self.colors["glass"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            bd=0,
            padx=padding,
            pady=padding,
        )
        card.pack(fill="both", expand=True)
        card._shadow_shell = shell  # type: ignore[attr-defined]
        return card

    def _grid_card(self, card: tk.Frame, **grid_options) -> None:
        shell = getattr(card, "_shadow_shell", card)
        shell.grid(**grid_options)

    def _build_calculator_tab(self) -> None:
        self.calculator_tab.columnconfigure(0, weight=2, uniform="cockpit")
        self.calculator_tab.columnconfigure(1, weight=2, uniform="cockpit")
        self.calculator_tab.columnconfigure(2, weight=2, uniform="cockpit")
        self.calculator_tab.rowconfigure(0, weight=1)

        inputs = self._panel(self.calculator_tab)
        inputs.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        quality = self._panel(self.calculator_tab)
        quality.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        outputs = self._panel(self.calculator_tab)
        outputs.grid(row=0, column=2, sticky="nsew")
        quality.columnconfigure(0, weight=1)
        outputs.columnconfigure(0, weight=1)

        self._build_inputs(inputs)
        self._build_quality_dashboard(quality)
        self._build_outputs(outputs)
        self.checklist_panel = self._panel(self.advanced_frame, padding=12)
        self.checklist_panel.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        self._build_checklist(self.checklist_panel)
        self._toggle_advanced()

    def _add_entry(self, parent: ttk.Frame, row: int, label: str, key: str, default: str = "", width: int | None = None) -> ttk.Entry:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        var = tk.StringVar(value=default)
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 0))
        self.vars[key] = var
        self.input_widgets.append(entry)
        return entry

    def _add_combo(self, parent: ttk.Frame, row: int, label: str, key: str, values: tuple[str, ...], default: str) -> ttk.Combobox:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        var = tk.StringVar(value=default)
        combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly")
        combo.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 0))
        self.vars[key] = var
        self.input_widgets.append(combo)
        return combo

    def _build_inputs(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="Trade Input", style="Panel.TLabel", font=("Helvetica Neue", 17, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
        ttk.Label(
            parent,
            text="Quick mode keeps the six decisions that matter. Profiles fill the rest.",
            style="Panel.TLabel",
            foreground=self.colors["muted"],
            wraplength=420,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self._add_entry(parent, 2, "Instrument / ticker", "instrument", "AMD")
        self.vars["instrument"].trace_add("write", lambda *_: self._on_instrument_change())
        self._add_combo(parent, 3, "Direction", "direction", DIRECTIONS, "Long")
        entry = self._add_entry(parent, 4, "Entry price", "entry", "160")
        ttk.Button(parent, text="Refresh", style="Secondary.TButton", command=self.refresh_price).grid(row=4, column=2, sticky="ew", padx=(8, 0), pady=4)
        self._add_entry(parent, 5, "Stop price", "stop", "155")
        self._add_entry(parent, 6, "Take profit price", "take_profit", "172")
        max_risk_entry = self._add_entry(parent, 7, "Max GBP risk", "max_risk", DEFAULT_SETTINGS["default_risk"])
        max_risk_entry.bind("<Return>", lambda _event: self.calculate())

        risk_buttons = ttk.Frame(parent, style="Panel.TFrame")
        risk_buttons.grid(row=8, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=(0, 8))
        for value in RISK_BUTTONS:
            ttk.Button(risk_buttons, text=f"£{value}", style="Risk.TButton", command=lambda v=value: self.vars["max_risk"].set(v)).pack(
                side="left", padx=(0, 6)
            )

        ttk.Label(parent, textvariable=self.last_price_var, style="Panel.TLabel", foreground=self.colors["muted"], wraplength=420).grid(
            row=9, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )

        self.advanced_button = ttk.Button(parent, text="Show advanced settings", style="Secondary.TButton", command=self._toggle_advanced_requested)
        self.advanced_button.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(8, 6))
        self.advanced_frame = ttk.Frame(parent, style="Advanced.TFrame")
        self.advanced_frame.columnconfigure(1, weight=1)

        self._add_combo(self.advanced_frame, 0, "Asset type", "asset_type", ASSET_TYPES, "CFD")
        self._add_combo(self.advanced_frame, 1, "Currency", "currency", CURRENCIES, "USD")
        self._add_entry(self.advanced_frame, 2, "Leverage", "leverage", "5")
        self._add_entry(self.advanced_frame, 3, "FX rate to GBP", "fx_rate", DEFAULT_SETTINGS["fx_USD"])
        ttk.Button(self.advanced_frame, text="Refresh FX", command=self.refresh_fx).grid(row=3, column=2, sticky="ew", padx=(8, 0), pady=4)
        ttk.Label(self.advanced_frame, textvariable=self.last_fx_var, style="Panel.TLabel", foreground=self.colors["muted"], wraplength=420).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        self._add_entry(self.advanced_frame, 5, "Support / resistance line", "support", "")
        self._add_entry(self.advanced_frame, 6, "Custom buffer %", "custom_buffer", DEFAULT_SETTINGS["default_buffer"])
        self._add_entry(self.advanced_frame, 7, "Spread cost", "spread_cost", "0")
        self._add_entry(self.advanced_frame, 8, "Overnight fee", "overnight_fee", "0")
        self._add_entry(self.advanced_frame, 9, "Commission", "commission", "0")
        self._add_entry(self.advanced_frame, 10, "Screenshot path", "screenshot_path", "")
        ttk.Label(self.advanced_frame, text="Notes / setup reason", style="Panel.TLabel").grid(row=11, column=0, sticky="nw", pady=4)
        self.notes_text = tk.Text(self.advanced_frame, height=4, wrap="word", font=("Helvetica Neue", 12), relief="solid", bd=1)
        self.notes_text.grid(row=11, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4)

        buttons = ttk.Frame(parent, style="Panel.TFrame")
        buttons.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="Calculate", style="Accent.TButton", command=self.calculate).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Save Trade", style="Secondary.TButton", command=self.save_trade).pack(side="left", padx=4)
        ttk.Button(buttons, text="Clear", style="Secondary.TButton", command=self.clear_form).pack(side="left", padx=4)
        ttk.Button(buttons, text="Copy", style="Secondary.TButton", command=self.copy_calculation).pack(side="left", padx=4)

        rules = self._panel(parent, padding=10)
        rules.grid(row=13, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Label(rules, text="Trading rules", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        for idx, text in enumerate(
            (
                "No calculator = no trade.",
                "Buy low only when support is confirmed.",
                "Risk is based on exposure, not margin.",
                "Small position first. Let winners grow.",
                "Stop-loss goes where the idea is invalidated.",
            )
        ):
            ttk.Label(rules, text=text, style="Subtle.TLabel").grid(row=idx + 1, column=0, sticky="w", pady=1)
        entry.focus_set()

    def _build_quality_dashboard(self, parent: ttk.Frame) -> None:
        parent.columnconfigure((0, 1), weight=1)
        ttk.Label(parent, text="Trade Quality", style="Panel.TLabel", font=("Helvetica Neue", 17, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        labels = (
            "Risk:Reward",
            "Stop-loss %",
            "Entry distance",
            "Risk size",
            "Exposure size",
            "Margin required",
            "Overall verdict",
        )
        for idx, label in enumerate(labels):
            frame = tk.Frame(parent, bg=self.colors["glass"], highlightbackground=self.colors["border"], highlightthickness=1, padx=14, pady=12)
            frame.grid(row=1 + idx // 2, column=idx % 2, sticky="ew", padx=7, pady=7)
            top = tk.Frame(frame, bg=self.colors["glass"])
            top.pack(fill="x")
            title = tk.Label(top, text=label, bg=self.colors["glass"], fg=self.colors["muted"], font=("Helvetica Neue", 10, "bold"), wraplength=130, justify="left")
            title.pack(side="left", anchor="w")
            badge = tk.Label(top, text="-", bg="#e2e8f0", fg=self.colors["muted"], font=("Helvetica Neue", 8, "bold"), padx=6, pady=1)
            badge.pack(side="right")
            value = tk.Label(frame, text="-", bg=self.colors["glass"], fg=self.colors["text"], font=("Helvetica Neue", 13, "bold"), justify="left", wraplength=210)
            value.pack(anchor="w", pady=(5, 1), fill="x")
            target = tk.Label(frame, text="", bg=self.colors["glass"], fg=self.colors["muted"], font=("Helvetica Neue", 9), justify="left", wraplength=210)
            target.pack(anchor="w", fill="x")
            gap = tk.Label(frame, text="", bg=self.colors["glass"], fg=self.colors["muted"], font=("Helvetica Neue", 9), justify="left", wraplength=210)
            gap.pack(anchor="w")
            self.quality_cards[label] = {"frame": frame, "title": title, "badge": badge, "value": value, "target": target, "gap": gap}

        ttk.Label(parent, text="What must improve?", style="Panel.TLabel", font=("Helvetica Neue", 13, "bold")).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(10, 3)
        )
        self.improve_frame = ttk.Frame(parent, style="Panel.TFrame")
        self.improve_frame.grid(row=6, column=0, columnspan=2, sticky="ew")
        self._write_improvements(["Calculate a trade to see improvement notes."])

    def _build_outputs(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        ttk.Label(parent, text="Trade Summary", style="Panel.TLabel", font=("Helvetica Neue", 17, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        sections = [
            ("Position", [("Units / shares / contracts", "units"), ("Leverage used", "leverage"), ("Stop distance", "stop_distance")]),
            (
                "Exposure & Margin",
                [
                    ("Exposure GBP", "exposure_gbp"),
                    ("Margin GBP", "required_margin_gbp"),
                    ("Exposure local", "exposure_local"),
                    ("Margin local", "required_margin_local"),
                ],
            ),
            (
                "Profit / Loss",
                [
                    ("Potential profit", "potential_profit"),
                    ("Potential loss", "potential_loss"),
                    ("Net expected profit", "net_profit"),
                    ("P/L basis", "pl_basis"),
                ],
            ),
            (
                "Validation",
                [
                    ("Risk:Reward", "risk_reward"),
                    ("Trade valid?", "valid"),
                    ("Risk label", "risk_label"),
                    ("Stop-loss %", "stop_loss_percent"),
                    ("Invalidation stop", "invalidation_stop"),
                ],
            ),
        ]
        row = 1
        for title, items in sections:
            card = self._summary_section(parent, title, items)
            self._grid_card(card, row=row, column=0, sticky="ew", pady=(0, 14))
            row += 1
        ttk.Label(parent, text="Warnings", style="Section.TLabel").grid(row=row, column=0, sticky="w", pady=(2, 4))
        self.warning_frame = ttk.Frame(parent, style="Panel.TFrame")
        self.warning_frame.grid(row=row + 1, column=0, sticky="ew")

    def _summary_section(self, parent: ttk.Frame, title: str, items: list[tuple[str, str]]) -> tk.Frame:
        card = self._card(parent, padding=12)
        card.columnconfigure(1, weight=1)
        tk.Label(card, text=title, bg=self.colors["glass"], fg=self.colors["text"], font=("Helvetica Neue", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        for idx, (label, key) in enumerate(items, start=1):
            tk.Label(card, text=label, bg=self.colors["glass"], fg=self.colors["muted"], font=("Helvetica Neue", 10), wraplength=170, justify="left").grid(
                row=idx, column=0, sticky="w", pady=3
            )
            value = tk.Label(card, text="-", bg=self.colors["glass"], fg=self.colors["text"], font=("Helvetica Neue", 12, "bold"), justify="right", wraplength=220)
            value.grid(row=idx, column=1, sticky="e", pady=3, padx=(12, 0))
            self.output_labels[key] = value
        return card

    def _build_checklist(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Advanced checklist", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        for idx, item in enumerate(CHECKLIST_ITEMS, start=1):
            var = tk.BooleanVar(value=False)
            chk = ttk.Checkbutton(parent, text=item, variable=var, command=self.update_checklist_grade)
            chk.grid(row=idx, column=(idx - 1) % 2, sticky="w", pady=3, padx=(0, 16))
            self.check_vars.append(var)
        self.grade_label = ttk.Label(parent, text="Trade grade: F", style="Panel.TLabel", font=("Helvetica Neue", 15, "bold"))
        self.grade_label.grid(row=7, column=0, columnspan=2, sticky="w", pady=(14, 0))

    def _build_journal_tab(self) -> None:
        self.journal_tab.rowconfigure(1, weight=1)
        self.journal_tab.columnconfigure(0, weight=1)
        controls = self._panel(self.journal_tab)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(controls, text="Trade Journal", style="Panel.TLabel", font=("Helvetica Neue", 17, "bold")).pack(side="left", padx=(0, 16))
        ttk.Button(controls, text="Update Result", style="Secondary.TButton", command=self.update_selected_result).pack(side="left", padx=4)
        ttk.Button(controls, text="Export CSV", style="Secondary.TButton", command=self.export_csv).pack(side="left", padx=4)
        ttk.Button(controls, text="Delete", style="Secondary.TButton", command=self.delete_selected_trade).pack(side="left", padx=4)

        self.tree = ttk.Treeview(self.journal_tab, columns=TRADE_COLUMNS, show="headings", selectmode="browse")
        for column in TRADE_COLUMNS:
            self.tree.heading(column, text=column.replace("_", " ").title(), command=lambda c=column: self._sort_tree(c, False))
            width = 90 if column not in {"notes", "lesson_learned"} else 180
            self.tree.column(column, width=width, minwidth=70, stretch=True)
        self.tree.tag_configure("win", foreground=self.colors["green"])
        self.tree.tag_configure("loss", foreground=self.colors["red"])
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_trade_select)
        scroll_y = ttk.Scrollbar(self.journal_tab, orient="vertical", command=self.tree.yview)
        scroll_y.grid(row=1, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(self.journal_tab, orient="horizontal", command=self.tree.xview)
        scroll_x.grid(row=2, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    def _sort_tree(self, column: str, reverse: bool) -> None:
        rows = [(self.tree.set(item, column), item) for item in self.tree.get_children("")]
        try:
            rows.sort(key=lambda item: float(str(item[0]).replace(",", "")), reverse=reverse)
        except ValueError:
            rows.sort(key=lambda item: str(item[0]).lower(), reverse=reverse)
        for index, (_value, item) in enumerate(rows):
            self.tree.move(item, "", index)
        self.tree.heading(column, command=lambda: self._sort_tree(column, not reverse))

    def _build_dashboard_tab(self) -> None:
        self.dashboard_tab.columnconfigure(0, weight=3)
        self.dashboard_tab.columnconfigure(1, weight=2)
        metrics = self._panel(self.dashboard_tab)
        metrics.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.dashboard_tab.rowconfigure(0, weight=1)
        metrics.columnconfigure((0, 1, 2, 3), weight=1)
        ttk.Label(metrics, text="Trading Dashboard", style="Panel.TLabel", font=("Helvetica Neue", 17, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 10)
        )
        self.metric_labels: dict[str, ttk.Label] = {}
        primary = [
            "Total trades",
            "Win rate %",
            "Average R multiple",
            "Total P/L",
            "Average win",
            "Average loss",
            "Best trade",
            "Worst trade",
        ]
        for idx, label in enumerate(primary):
            card = self._card(metrics, padding=14)
            self._grid_card(card, row=1 + idx // 4, column=idx % 4, sticky="ew", padx=7, pady=7)
            tk.Label(card, text=label, bg=self.colors["glass"], fg=self.colors["muted"], font=("Helvetica Neue", 10, "bold")).pack(anchor="w")
            value = tk.Label(card, text="-", bg=self.colors["glass"], fg=self.colors["text"], font=("Helvetica Neue", 15, "bold"))
            value.pack(anchor="w", pady=(4, 0))
            self.metric_labels[label] = value

        secondary = self._card(metrics, padding=14)
        self._grid_card(secondary, row=3, column=0, columnspan=4, sticky="ew", pady=(16, 0))
        secondary.columnconfigure(1, weight=1)
        for idx, label in enumerate(
            (
                "Profit factor",
                "Best instrument",
                "Worst instrument",
                "Most profitable setup",
                "Most common mistake",
                "Daily P/L",
                "Daily loss limit status",
                "Trades taken today",
                "Max trades per day status",
            )
        ):
            tk.Label(secondary, text=label, bg=self.colors["glass"], fg=self.colors["muted"], font=("Helvetica Neue", 10)).grid(
                row=idx, column=0, sticky="w", pady=3
            )
            value = tk.Label(secondary, text="-", bg=self.colors["glass"], fg=self.colors["text"], font=("Helvetica Neue", 11, "bold"))
            value.grid(row=idx, column=1, sticky="e", pady=3)
            self.metric_labels[label] = value

        notice = self._panel(self.dashboard_tab)
        notice.grid(row=0, column=1, sticky="nsew")
        ttk.Label(notice, text="Risk Desk", style="Panel.TLabel", font=("Helvetica Neue", 17, "bold")).pack(anchor="w")
        self.risk_status_frame = ttk.Frame(notice, style="Panel.TFrame")
        self.risk_status_frame.pack(fill="x", pady=(12, 0))

    def _build_settings_tab(self) -> None:
        self.settings_tab.columnconfigure(0, weight=1)
        self.settings_tab.columnconfigure(1, weight=1)
        trading = self._panel(self.settings_tab)
        trading.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        trading.columnconfigure(0, weight=1)
        trading.columnconfigure(1, weight=1)
        ttk.Label(trading, text="Settings", style="Panel.TLabel", font=("Helvetica Neue", 17, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        risk_card = self._settings_card(trading, "Risk defaults")
        self._grid_card(risk_card, row=1, column=0, sticky="nsew", padx=(0, 8), pady=8)
        self._settings_entry(risk_card, 1, "Default risk", "default_risk")
        self._settings_entry(risk_card, 2, "Hard max risk", "hard_max_risk")
        self._settings_entry(risk_card, 3, "Default buffer %", "default_buffer")

        exposure_card = self._settings_card(trading, "Exposure limits")
        self._grid_card(exposure_card, row=1, column=1, sticky="nsew", padx=(8, 0), pady=8)
        self._settings_entry(exposure_card, 1, "Default exposure limit", "default_exposure_limit")

        daily_card = self._settings_card(trading, "Daily rules")
        self._grid_card(daily_card, row=2, column=0, sticky="nsew", padx=(0, 8), pady=8)
        self._settings_entry(daily_card, 1, "Max daily loss", "daily_loss_limit")
        self._settings_entry(daily_card, 2, "Max trades per day", "max_trades_per_day")

        fx_card = self._settings_card(trading, "FX defaults")
        self._grid_card(fx_card, row=2, column=1, sticky="nsew", padx=(8, 0), pady=8)
        for offset, currency in enumerate(FX_CURRENCIES, start=1):
            self._settings_entry(fx_card, offset, currency, f"fx_{currency}")

        ui_card = self._settings_card(trading, "UI preferences")
        self._grid_card(ui_card, row=3, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(ui_card, text="Light workstation layout is enabled by default.", style="Subtle.TLabel").grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Button(trading, text="Save Settings", style="Accent.TButton", command=self.save_settings).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0)
        )

        api = self._panel(self.settings_tab)
        api.grid(row=0, column=1, sticky="nsew")
        api.columnconfigure(1, weight=1)
        ttk.Label(api, text="API Keys", style="Panel.TLabel", font=("Helvetica Neue", 17, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        ttk.Label(
            api,
            text="Keys are saved locally in .env and ignored by Git. API support is read-only.",
            style="Panel.TLabel",
            foreground=self.colors["muted"],
            wraplength=420,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        api_rows = [
            ("Trading 212 API key", "TRADING212_API_KEY"),
            ("IG API key", "IG_API_KEY"),
            ("IG username", "IG_USERNAME"),
            ("IG password", "IG_PASSWORD"),
            ("IG account type", "IG_ACCOUNT_TYPE"),
            ("Twelve Data API key", "TWELVE_DATA_API_KEY"),
            ("Market data API key", "MARKET_DATA_API_KEY"),
        ]
        last_api_row = 1
        for row, (label, key) in enumerate(api_rows, start=2):
            last_api_row = row
            ttk.Label(api, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=5)
            var = tk.StringVar()
            if key == "IG_ACCOUNT_TYPE":
                ttk.Combobox(api, textvariable=var, values=("demo", "live"), state="readonly").grid(
                    row=row, column=1, sticky="ew", pady=5, padx=(8, 0)
                )
            else:
                show = "*" if "PASSWORD" in key or "KEY" in key else ""
                ttk.Entry(api, textvariable=var, show=show).grid(row=row, column=1, sticky="ew", pady=5, padx=(8, 0))
            self.api_vars[key] = var
        ttk.Button(api, text="Save API Keys", style="Accent.TButton", command=self.save_api_settings).grid(
            row=last_api_row + 1, column=0, columnspan=2, sticky="ew", pady=(16, 0)
        )
        ttk.Label(
            api,
            text="Safety: the app never auto-submits trades. Market data is for autofill only. Use broker price for final execution.",
            style="Panel.TLabel",
            foreground=self.colors["orange"],
            wraplength=420,
        ).grid(row=last_api_row + 2, column=0, columnspan=2, sticky="w", pady=(16, 0))

    def _settings_entry(self, parent: ttk.Frame, row: int, label: str, key: str) -> None:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        var = tk.StringVar(value=DEFAULT_SETTINGS.get(key, ""))
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=5, padx=(8, 0))
        self.setting_vars[key] = var

    def _settings_card(self, parent: ttk.Frame, title: str) -> ttk.Frame:
        card = self._panel(parent, padding=12)
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text=title, style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        return card

    def _toggle_advanced_requested(self) -> None:
        self.advanced_visible.set(not self.advanced_visible.get())
        self._toggle_advanced()

    def _toggle_advanced(self) -> None:
        if self.advanced_visible.get():
            self.advanced_frame.grid(row=11, column=0, columnspan=3, sticky="ew")
            self.checklist_panel.grid()
            self.advanced_button.configure(text="Hide advanced settings")
        else:
            self.advanced_frame.grid_remove()
            self.checklist_panel.grid_remove()
            self.advanced_button.configure(text="Show advanced settings")

    def _float(self, key: str, default: float = 0.0) -> float:
        raw = str(self.vars[key].get()).replace(",", "").strip()
        return float(raw) if raw else default

    def _setting_float(self, key: str, fallback: str | float) -> float:
        value = self.db.get_setting(key, str(fallback))
        try:
            return float(str(value).replace(",", "").strip())
        except ValueError:
            return float(fallback)

    def _buffer_percent(self) -> float:
        default_buffer = self._setting_float("default_buffer", DEFAULT_SETTINGS["default_buffer"])
        return self._float("custom_buffer", default_buffer) / 100

    def _trade_inputs(self) -> TradeInputs:
        entry = self._float("entry")
        stop = self._float("stop")
        return TradeInputs(
            instrument=self.vars["instrument"].get().strip().upper(),
            asset_type=self.vars["asset_type"].get(),
            currency=self.vars["currency"].get(),
            fx_rate_to_gbp=self._float("fx_rate", 1.0),
            direction=self.vars["direction"].get(),
            entry_price=entry,
            stop_price=stop,
            take_profit_price=self._float("take_profit"),
            max_risk_gbp=self._float("max_risk"),
            support_line=self._float("support", stop or entry),
            buffer_percent=self._buffer_percent(),
            leverage=self._float("leverage", self._default_leverage()),
            spread_cost=self._float("spread_cost"),
            overnight_fee=self._float("overnight_fee"),
            commission=self._float("commission"),
            notes=self.notes_text.get("1.0", "end").strip(),
        )

    def _on_instrument_change(self) -> None:
        self._apply_instrument_profile()

    def _apply_quick_defaults(self) -> None:
        self.vars["max_risk"].set(self.db.get_setting("default_risk", DEFAULT_SETTINGS["default_risk"]))
        self.vars["custom_buffer"].set(self.db.get_setting("default_buffer", DEFAULT_SETTINGS["default_buffer"]))
        self.vars["spread_cost"].set("0")
        self.vars["overnight_fee"].set("0")
        self.vars["commission"].set("0")
        self.vars["leverage"].set(str(self._default_leverage()))
        self._apply_instrument_profile()

    def _apply_instrument_profile(self) -> None:
        instrument = self.vars.get("instrument")
        if not instrument:
            return
        ticker = instrument.get().strip().upper()
        profile = INSTRUMENT_PROFILES.get(ticker)
        if not profile and self._looks_like_forex_pair(ticker):
            quote_currency = ticker[-3:]
            profile = ("Forex", quote_currency if quote_currency in CURRENCIES else "USD")
        if not profile:
            return
        asset_type, currency = profile
        self.vars["asset_type"].set(asset_type)
        self.vars["currency"].set(currency)
        fx = "1" if currency == "GBP" else self.db.get_setting(f"fx_{currency}", DEFAULT_SETTINGS.get(f"fx_{currency}", "1"))
        self.vars["fx_rate"].set(fx)
        self.vars["leverage"].set(str(self._default_leverage(ticker, asset_type)))
        self.last_fx_var.set(f"FX source: saved {currency} default")

    def _looks_like_forex_pair(self, ticker: str) -> bool:
        majors = {"EUR", "GBP", "USD", "JPY", "CHF", "CAD", "AUD", "NZD"}
        return len(ticker) == 6 and ticker[:3] in majors and ticker[3:] in majors

    def _default_leverage(self, instrument: str | None = None, asset_type: str | None = None) -> int:
        ticker = (instrument or self.vars.get("instrument", tk.StringVar(value="")).get()).strip().upper()
        asset = asset_type or self.vars.get("asset_type", tk.StringVar(value="CFD")).get()
        if ticker in LEVERAGE_DEFAULTS:
            return LEVERAGE_DEFAULTS[ticker]
        if self._looks_like_forex_pair(ticker) or asset == "Forex":
            return 30
        if asset == "Index":
            return 20
        if asset == "3x ETP":
            return 1
        if asset == "Crypto":
            return 2
        if ticker == "XAUUSD":
            return 20
        if ticker in {"XAGUSD", "OIL", "CRUDE"}:
            return 10
        if asset == "Commodity":
            return 10
        if asset == "CFD":
            return 5
        return 1

    def calculate(self) -> None:
        try:
            values = self._trade_inputs()
            result = calculate_trade(values)
        except ValueError:
            messagebox.showerror("Invalid input", "Check numeric fields and try again.")
            return

        self.current_result = result
        outputs = {
            "stop_distance": f"{result.stop_distance:.4f}",
            "stop_loss_percent": f"{result.stop_loss_percent:.2%}",
            "invalidation_stop": f"{result.invalidation_stop_price:.4f}",
            "units": f"{result.units:.4f}",
            "leverage": f"{result.leverage:g}x",
            "exposure_local": f"{result.exposure_local:,.2f} {values.currency}",
            "exposure_gbp": f"GBP {result.exposure_gbp:,.2f}",
            "required_margin_local": f"{result.required_margin_local:,.2f} {values.currency}",
            "required_margin_gbp": f"GBP {result.required_margin_gbp:,.2f}",
            "potential_profit": f"GBP {result.potential_profit_gbp:,.2f}",
            "potential_loss": f"GBP {result.potential_loss_gbp:,.2f}",
            "pl_basis": "Based on exposure, not margin",
            "net_profit": f"GBP {result.net_expected_profit_gbp:,.2f}",
            "risk_reward": f"{result.risk_reward:.2f}",
            "valid": "Yes" if result.valid else "No",
            "risk_label": result.risk_label,
        }
        for key, value in outputs.items():
            self.output_labels[key].configure(text=value)
        self.output_labels["potential_profit"].configure(foreground=self.colors["green"])
        self.output_labels["potential_loss"].configure(foreground=self.colors["red"])
        self.output_labels["net_profit"].configure(foreground=self.colors["green"] if result.net_expected_profit_gbp >= 0 else self.colors["red"])
        self.output_labels["valid"].configure(
            foreground=self.colors["green"] if result.valid else self.colors["red"],
            background=self.colors["green_bg"] if result.valid else self.colors["red_bg"],
        )
        self.output_labels["risk_label"].configure(
            foreground=self.colors["green"] if result.risk_label in {"Safe", "Moderate"} else self.colors["orange"]
        )
        warnings = result.errors + result.warnings
        if "yfinance" in self.last_price_var.get() or "yfinance" in self.last_fx_var.get():
            warnings.append("Price data may be delayed. Verify before trading.")
        quality_warnings = self._update_quality_dashboard(values, result)
        warnings.extend([warning for warning in quality_warnings if warning not in warnings])
        self._write_warnings(warnings)
        self._sync_checklist_from_result(result)
        self.refresh_dashboard()

    def _update_quality_dashboard(self, values: TradeInputs, result) -> list[str]:
        assessments = self._quality_assessments(values, result)
        reasons: list[str] = []
        red_count = 0
        yellow_count = 0

        for label, assessment in assessments.items():
            if label == "Overall verdict":
                continue
            status = assessment["status"]
            red_count += status == "red"
            yellow_count += status == "yellow"
            self._set_quality_card(label, assessment["value"], status, assessment["target"], assessment["gap"])
            reasons.extend(assessment["reasons"])

        if not result.valid or self._daily_loss_hit() or self._max_trades_hit():
            verdict = "Avoid"
            verdict_status = "red"
        elif red_count >= 2:
            verdict = "Avoid"
            verdict_status = "red"
        elif red_count == 1:
            verdict = "Borderline"
            verdict_status = "red"
        elif yellow_count:
            verdict = "Acceptable"
            verdict_status = "yellow"
        else:
            verdict = "Ideal"
            verdict_status = "green"

        invalid_reasons = []
        if not result.valid:
            invalid_reasons.append("Trade invalid")
        if self._daily_loss_hit():
            invalid_reasons.append("Daily loss limit hit")
        if self._max_trades_hit():
            invalid_reasons.append("Max trades reached")
        reasons = invalid_reasons + [reason for reason in reasons if reason not in invalid_reasons]

        self._set_quality_card("Overall verdict", verdict, verdict_status, "Target: Ideal / Acceptable", "")
        self._write_improvements(reasons or ["No major issues."])
        return reasons

    def _quality_assessments(self, values: TradeInputs, result) -> dict[str, dict[str, object]]:
        stop_loss_pct = result.stop_loss_percent * 100
        entry_distance = self._entry_distance_percent(values)
        default_risk = self._setting_float("default_risk", DEFAULT_SETTINGS["default_risk"])
        hard_risk = self._setting_float("hard_max_risk", DEFAULT_SETTINGS["hard_max_risk"])
        exposure_limit = self._setting_float("default_exposure_limit", DEFAULT_SETTINGS["default_exposure_limit"])

        rr_status = "green" if result.risk_reward >= 2 else "yellow" if result.risk_reward >= 1.5 else "red"
        rr_reasons = [] if rr_status == "green" else ["Risk:Reward too low"]
        rr_gap = "" if result.risk_reward >= 2 else f"Need R:R +{2 - result.risk_reward:.2f}"

        stop_status, stop_reason, stop_target, stop_gap = self._stop_loss_status(values, stop_loss_pct)
        distance_status = "green" if 0 <= entry_distance <= 1 else "yellow" if entry_distance <= 2 else "red"
        distance_reasons = [] if distance_status == "green" else ["Entry too far from support"]
        distance_target = "Target: 0%-1% from resistance" if values.direction == "Short" else "Target: 0%-1% from support"
        distance_gap = "" if entry_distance <= 1 else f"Entry {entry_distance - 1:.2f}% too far"

        if values.max_risk_gbp <= default_risk:
            risk_status = "green"
        elif values.max_risk_gbp <= hard_risk:
            risk_status = "yellow"
        else:
            risk_status = "red"
        risk_reasons = [] if risk_status == "green" else ["Position too large"]
        risk_gap = "" if values.max_risk_gbp <= default_risk else f"Risk GBP {values.max_risk_gbp - default_risk:.2f} over"

        if result.exposure_gbp <= exposure_limit:
            exposure_status = "green"
        elif result.exposure_gbp <= exposure_limit * 1.5:
            exposure_status = "yellow"
        else:
            exposure_status = "red"
        exposure_reasons = [] if exposure_status == "green" else ["Position too large"]
        exposure_gap = "" if result.exposure_gbp <= exposure_limit else f"Exposure GBP {result.exposure_gbp - exposure_limit:,.0f} over"
        margin_status = exposure_status

        return {
            "Risk:Reward": {
                "value": f"{result.risk_reward:.2f}",
                "status": rr_status,
                "target": "Target: 2.0+ ideal",
                "gap": rr_gap,
                "reasons": rr_reasons,
            },
            "Stop-loss %": {
                "value": f"{stop_loss_pct:.2f}%",
                "status": stop_status,
                "target": stop_target,
                "gap": stop_gap,
                "reasons": [stop_reason] if stop_reason else [],
            },
            "Entry distance": {
                "value": f"{entry_distance:.2f}%",
                "status": distance_status,
                "target": distance_target,
                "gap": distance_gap,
                "reasons": distance_reasons,
            },
            "Risk size": {
                "value": f"GBP {values.max_risk_gbp:.2f}",
                "status": risk_status,
                "target": f"Target: <= GBP {default_risk:g}",
                "gap": risk_gap,
                "reasons": risk_reasons,
            },
            "Exposure size": {
                "value": f"GBP {result.exposure_gbp:,.0f} exposure\nGBP {result.required_margin_gbp:,.0f} margin | {result.leverage:g}x",
                "status": exposure_status,
                "target": f"Target: <= GBP {exposure_limit:g}",
                "gap": exposure_gap,
                "reasons": exposure_reasons,
            },
            "Margin required": {
                "value": f"GBP {result.required_margin_gbp:,.2f}",
                "status": margin_status,
                "target": "Based on leverage used",
                "gap": f"Leverage: {result.leverage:g}x",
                "reasons": [],
            },
            "Overall verdict": {"value": "-", "status": "yellow", "target": "Target: Ideal / Acceptable", "gap": "", "reasons": []},
        }

    def _entry_distance_percent(self, values: TradeInputs) -> float:
        if values.support_line <= 0:
            return 999.0
        if values.direction == "Short":
            return max(0.0, (values.support_line - values.entry_price) / values.support_line * 100)
        return max(0.0, (values.entry_price - values.support_line) / values.support_line * 100)

    def _stop_loss_status(self, values: TradeInputs, stop_loss_pct: float) -> tuple[str, str, str, str]:
        green, yellow = self._stop_loss_ranges(values)
        target = self._stop_loss_target_text(values)
        if green[0] <= stop_loss_pct <= green[1]:
            return "green", "", target, ""
        if yellow[0] <= stop_loss_pct <= yellow[1]:
            reason = "Stop too tight" if stop_loss_pct < green[0] else "Stop too wide"
            gap = self._stop_gap_text(reason, stop_loss_pct, green)
            return "yellow", reason, target, gap
        reason = "Stop too tight" if stop_loss_pct < yellow[0] else "Stop too wide"
        gap = self._stop_gap_text(reason, stop_loss_pct, green)
        return "red", reason, target, gap

    def _stop_loss_ranges(self, values: TradeInputs) -> tuple[tuple[float, float], tuple[float, float]]:
        instrument = values.instrument.upper()
        asset_type = values.asset_type
        if asset_type == "Index":
            return (0.3, 1.2), (0.2, 1.8)
        if asset_type == "3x ETP":
            return (2.0, 6.0), (1.5, 8.0)
        if instrument in {"XAUUSD", "XAGUSD"}:
            return (0.5, 2.0), (0.3, 3.0)
        if instrument in {"OIL", "CRUDE"}:
            return (0.8, 3.0), (0.5, 4.0)
        if asset_type == "Forex":
            return (0.2, 0.8), (0.1, 1.2)
        if asset_type == "Crypto":
            return (2.0, 6.0), (1.0, 10.0)
        return (0.8, 2.5), (0.5, 3.5)

    def _stop_loss_target_text(self, values: TradeInputs) -> str:
        instrument = values.instrument.upper()
        asset_type = values.asset_type
        if asset_type == "Index":
            return "Target: 0.3%-1.2%"
        if asset_type == "3x ETP":
            return "Target: 2%-6%"
        if instrument in {"XAUUSD", "XAGUSD"}:
            return "Target: 0.5%-2%"
        if instrument in {"OIL", "CRUDE"}:
            return "Target: 0.8%-3%"
        if asset_type == "Forex":
            return "Target: 0.2%-0.8%"
        if asset_type == "Crypto":
            return "Target: 2%-6%"
        return "Target: 0.8%-2.5%"

    def _stop_gap_text(self, reason: str, stop_loss_pct: float, green: tuple[float, float]) -> str:
        if reason == "Stop too tight":
            return f"Stop too tight by {green[0] - stop_loss_pct:.2f}%"
        return f"Stop too wide by {stop_loss_pct - green[1]:.2f}%"

    def _set_quality_card(self, label: str, value: str, status: str, target_text: str = "", gap_text: str = "") -> None:
        colors = {
            "green": (self.colors["green_bg"], self.colors["green"], "GOOD"),
            "yellow": (self.colors["yellow_bg"], self.colors["yellow"], "WATCH"),
            "red": (self.colors["red_bg"], self.colors["red"], "BAD"),
        }
        badge_bg, fg, badge_text = colors[status]
        card = self.quality_cards[label]
        frame = card["frame"]
        title = card["title"]
        badge = card["badge"]
        value_label = card["value"]
        target_label = card["target"]
        gap_label = card["gap"]
        assert isinstance(frame, tk.Frame)
        assert isinstance(title, tk.Label)
        assert isinstance(badge, tk.Label)
        assert isinstance(value_label, tk.Label)
        assert isinstance(target_label, tk.Label)
        assert isinstance(gap_label, tk.Label)
        frame.configure(bg=self.colors["glass"], highlightbackground=fg if status == "red" else self.colors["border"])
        for child in frame.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=self.colors["glass"])
        title.configure(bg=self.colors["glass"], fg=self.colors["muted"])
        badge.configure(text=badge_text, bg=badge_bg, fg=fg)
        value_label.configure(text=value, bg=self.colors["glass"], fg=self.colors["text"] if status != "red" else fg)
        target_label.configure(text=target_text, bg=self.colors["glass"], fg=self.colors["muted"])
        gap_label.configure(text=gap_text, bg=self.colors["glass"], fg=fg if gap_text else self.colors["muted"])

    def _write_improvements(self, reasons: list[str]) -> None:
        cleaned: list[str] = []
        for reason in reasons:
            if reason and reason not in cleaned:
                cleaned.append(reason)
        for child in self.improve_frame.winfo_children():
            child.destroy()
        for idx, reason in enumerate(cleaned[:6]):
            prefix = "OK" if "No major issues" in reason else "-"
            color = self.colors["green"] if "No major issues" in reason else self.colors["muted"]
            label = ttk.Label(self.improve_frame, text=f"{prefix} {reason}", style="Subtle.TLabel", foreground=color, wraplength=440)
            label.grid(row=idx, column=0, sticky="w", pady=1)

    def refresh_price(self) -> None:
        instrument = self.vars["instrument"].get().strip().upper()
        if not instrument:
            messagebox.showwarning("Missing instrument", "Enter an instrument first.")
            return
        quote = self.market_data.latest_price(instrument)
        if quote is None:
            self.last_price_var.set("Last price: unavailable, manual entry active")
            self._write_warnings(["Live price unavailable. Keep manual entry available."])
            return
        self.vars["entry"].set(f"{quote.value:.4f}")
        delay = " delayed" if quote.delayed else ""
        self.last_price_var.set(f"Latest: {quote.value:.4f} | {quote.source}{delay} | {quote.timestamp}. Use broker price for final execution.")

    def refresh_fx(self) -> None:
        currency = self.vars["currency"].get()
        quote = self.market_data.latest_fx_to_gbp(currency)
        if quote is None:
            self.last_fx_var.set("FX source: unavailable, saved/manual rate active")
            self._write_warnings(["Live FX unavailable. Keep manual entry available."])
            return
        self.vars["fx_rate"].set(f"{quote.value:.6f}")
        delay = " delayed" if quote.delayed else ""
        self.last_fx_var.set(f"FX: {quote.value:.6f} | {quote.source}{delay} | {quote.timestamp}. Manual override available.")

    def _write_warnings(self, messages: list[str]) -> None:
        for child in self.warning_frame.winfo_children():
            child.destroy()
        shown = messages if messages else ["No warnings."]
        for idx, message in enumerate(shown[:7]):
            color = self.colors["red"] if "invalid" in message.lower() or "must" in message.lower() else self.colors["orange"]
            ttk.Label(self.warning_frame, text=f"- {message}", style="Subtle.TLabel", foreground=color).grid(
                row=idx, column=0, sticky="w", pady=1
            )

    def _sync_checklist_from_result(self, result) -> None:
        auto = [
            True,
            True,
            result.stop_distance > 0,
            result.potential_profit_gbp > 0,
            result.risk_reward >= 2,
            True,
            True,
            True,
            not self._daily_loss_hit(),
            not self._max_trades_hit(),
        ]
        for var, value in zip(self.check_vars, auto):
            var.set(value)
        self.update_checklist_grade()

    def update_checklist_grade(self) -> None:
        passed = sum(1 for var in self.check_vars if var.get())
        invalid = self.current_result is not None and not self.current_result.valid
        if len(self.check_vars) >= 8 and (not self.check_vars[5].get() or not self.check_vars[7].get()):
            invalid = True
        grade = grade_checklist(passed, len(self.check_vars), invalid)
        color = {"A": self.colors["green"], "B": "#65a30d", "C": self.colors["orange"], "F": self.colors["red"]}[grade]
        self.grade_label.configure(text=f"Trade grade: {grade}", foreground=color)

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
            "setup_type": self._choose_value("Setup type", SETUP_TYPES, "Support Bounce"),
            "emotion_before": self._choose_value("Emotion before trade", EMOTIONS, "Calm"),
            "result_gbp": 0,
            "win_loss": "",
            "r_multiple": 0,
            "mistake_made": "",
            "lesson_learned": "",
            "screenshot_path": self.vars["screenshot_path"].get().strip(),
            "notes": values.notes,
        }
        self.db.add_trade(data)
        self.refresh_journal()
        self.refresh_dashboard()
        messagebox.showinfo("Saved", "Trade saved to journal.")

    def _choose_value(self, title: str, values: tuple[str, ...], default: str) -> str:
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        ttk.Label(dialog, text=title, padding=12).pack(anchor="w")
        var = tk.StringVar(value=default)
        ttk.Combobox(dialog, textvariable=var, values=values, state="readonly", width=28).pack(padx=12, pady=(0, 12))
        ttk.Button(dialog, text="OK", command=dialog.destroy).pack(pady=(0, 12))
        self.wait_window(dialog)
        return var.get()

    def clear_form(self) -> None:
        keep = {"asset_type", "currency", "direction"}
        for key, var in self.vars.items():
            if key not in keep:
                var.set("")
        self.vars["direction"].set("Long")
        self.notes_text.delete("1.0", "end")
        self.current_result = None
        self._apply_quick_defaults()
        for label in self.output_labels.values():
            label.configure(text="-", foreground=self.colors["text"], background="#ffffff")
        self._write_warnings(["No calculator = no trade."])
        for label in self.quality_cards:
            self._set_quality_card(label, "-", "yellow")
        self._write_improvements(["Calculate a trade to see improvement notes."])
        for var in self.check_vars:
            var.set(False)
        self.update_checklist_grade()

    def copy_calculation(self) -> None:
        if self.current_result is None:
            self.calculate()
        if self.current_result is None:
            return
        lines = [f"{label}: {widget.cget('text')}" for label, widget in self.output_labels.items()]
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        messagebox.showinfo("Copied", "Calculation result copied to clipboard.")

    def refresh_journal(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.db.all_trades():
            values = [row[column] for column in TRADE_COLUMNS]
            result = float(row["result_gbp"] or 0)
            tag = "win" if result > 0 else "loss" if result < 0 else ""
            self.tree.insert("", "end", iid=str(row["id"]), values=values, tags=(tag,) if tag else ())

    def _on_trade_select(self, _event=None) -> None:
        selection = self.tree.selection()
        self.selected_trade_id = int(selection[0]) if selection else None

    def delete_selected_trade(self) -> None:
        if self.selected_trade_id is None:
            messagebox.showwarning("No selection", "Select a trade first.")
            return
        if messagebox.askyesno("Delete trade", "Delete selected trade?"):
            self.db.delete_trade(self.selected_trade_id)
            self.selected_trade_id = None
            self.refresh_journal()
            self.refresh_dashboard()

    def update_selected_result(self) -> None:
        if self.selected_trade_id is None:
            messagebox.showwarning("No selection", "Select a trade first.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Update result")
        dialog.transient(self)
        dialog.grab_set()
        fields = {
            "Result GBP": tk.StringVar(value="0"),
            "Win/Loss": tk.StringVar(value="Win"),
            "R multiple": tk.StringVar(value="0"),
            "Mistake made?": tk.StringVar(value=""),
            "Lesson learned": tk.StringVar(value=""),
        }
        for row, (label, var) in enumerate(fields.items()):
            ttk.Label(dialog, text=label, padding=(12, 5)).grid(row=row, column=0, sticky="w")
            if label == "Win/Loss":
                ttk.Combobox(dialog, textvariable=var, values=("Win", "Loss", "Breakeven"), state="readonly").grid(
                    row=row, column=1, sticky="ew", padx=12, pady=5
                )
            else:
                ttk.Entry(dialog, textvariable=var, width=34).grid(row=row, column=1, sticky="ew", padx=12, pady=5)

        def save() -> None:
            try:
                result = float(fields["Result GBP"].get())
                r_multiple = float(fields["R multiple"].get())
            except ValueError:
                messagebox.showerror("Invalid input", "Result and R multiple must be numbers.")
                return
            self.db.update_result(
                self.selected_trade_id,
                result,
                fields["Win/Loss"].get(),
                r_multiple,
                fields["Mistake made?"].get(),
                fields["Lesson learned"].get(),
            )
            dialog.destroy()
            self.refresh_journal()
            self.refresh_dashboard()

        ttk.Button(dialog, text="Save", command=save).grid(row=len(fields), column=0, columnspan=2, pady=12)
        self.wait_window(dialog)

    def export_csv(self) -> None:
        default = Path("exports") / f"trading-risk-cockpit-{dt.date.today().isoformat()}.csv"
        default.parent.mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default.name,
            initialdir=str(default.parent.resolve()),
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if path:
            self.db.export_csv(path)
            messagebox.showinfo("Exported", f"CSV exported to:\n{path}")

    def _daily_loss_hit(self) -> bool:
        try:
            limit = abs(float(self.db.get_setting("daily_loss_limit", DEFAULT_SETTINGS["daily_loss_limit"])))
        except ValueError:
            return False
        daily_pl = sum(float(row["result_gbp"] or 0) for row in self.db.trades_today(dt.date.today().isoformat()))
        return daily_pl <= -limit

    def _max_trades_hit(self) -> bool:
        try:
            max_trades = int(float(self.db.get_setting("max_trades_per_day", DEFAULT_SETTINGS["max_trades_per_day"])))
        except ValueError:
            return False
        return len(self.db.trades_today(dt.date.today().isoformat())) >= max_trades

    def refresh_dashboard(self) -> None:
        rows = self.db.all_trades()
        total = len(rows)
        results = [float(row["result_gbp"] or 0) for row in rows]
        wins = [r for r in results if r > 0]
        losses = [r for r in results if r < 0]
        total_pl = sum(results)
        win_rate = (len(wins) / total * 100) if total else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0)
        avg_r = sum(float(row["r_multiple"] or 0) for row in rows) / total if total else 0
        today = self.db.trades_today(dt.date.today().isoformat())
        daily_pl = sum(float(row["result_gbp"] or 0) for row in today)
        best_trade = max(results) if results else 0
        worst_trade = min(results) if results else 0

        def grouped_best(field: str) -> tuple[str, str]:
            totals: dict[str, float] = {}
            for row in rows:
                key = row[field] or "Unknown"
                totals[key] = totals.get(key, 0) + float(row["result_gbp"] or 0)
            if not totals:
                return "-", "-"
            best = max(totals, key=totals.get)
            worst = min(totals, key=totals.get)
            return f"{best} ({totals[best]:.2f})", f"{worst} ({totals[worst]:.2f})"

        best_instrument, worst_instrument = grouped_best("instrument")
        best_setup, _ = grouped_best("setup_type")
        mistakes: dict[str, int] = {}
        for row in rows:
            mistake = str(row["mistake_made"] or "").strip()
            if mistake:
                mistakes[mistake] = mistakes.get(mistake, 0) + 1
        most_common_mistake = max(mistakes, key=mistakes.get) if mistakes else "-"
        loss_status = "Daily loss limit hit - stop trading." if self._daily_loss_hit() else "Within limit"
        trade_status = "Max trades reached - stop trading." if self._max_trades_hit() else "Within limit"

        values = {
            "Total trades": str(total),
            "Total P/L": f"GBP {total_pl:,.2f}",
            "Win rate %": f"{win_rate:.1f}%",
            "Average win": f"GBP {avg_win:,.2f}",
            "Average loss": f"GBP {avg_loss:,.2f}",
            "Best trade": f"GBP {best_trade:,.2f}",
            "Worst trade": f"GBP {worst_trade:,.2f}",
            "Profit factor": f"{profit_factor:.2f}",
            "Average R multiple": f"{avg_r:.2f}",
            "Best instrument": best_instrument,
            "Worst instrument": worst_instrument,
            "Most profitable setup": best_setup,
            "Most common mistake": most_common_mistake,
            "Daily P/L": f"GBP {daily_pl:,.2f}",
            "Daily loss limit status": loss_status,
            "Trades taken today": str(len(today)),
            "Max trades per day status": trade_status,
        }
        for key, value in values.items():
            label = self.metric_labels[key]
            label.configure(text=value)
            if key in {"Total P/L", "Daily P/L"}:
                label.configure(fg=self.colors["green"] if not value.startswith("GBP -") else self.colors["red"])
            elif key in {"Best trade", "Average win"}:
                label.configure(fg=self.colors["green"])
            elif key in {"Worst trade", "Average loss"}:
                label.configure(fg=self.colors["red"] if value != "GBP 0.00" else self.colors["text"])
            elif "stop trading" in value:
                label.configure(fg=self.colors["red"])
            else:
                label.configure(fg=self.colors["text"])

        status_lines = ["No calculator = no trade."]
        if self._daily_loss_hit():
            status_lines.append("Daily loss limit hit - stop trading.")
        if self._max_trades_hit():
            status_lines.append("Max trades reached - stop trading.")
        if len(status_lines) == 1:
            status_lines.append("Risk controls are currently within limits.")
        for child in self.risk_status_frame.winfo_children():
            child.destroy()
        for idx, line in enumerate(status_lines):
            color = self.colors["red"] if "stop trading" in line else self.colors["muted"]
            ttk.Label(self.risk_status_frame, text=f"- {line}", style="Subtle.TLabel", foreground=color).grid(
                row=idx, column=0, sticky="w", pady=3
            )

    def save_settings(self) -> None:
        for key, var in self.setting_vars.items():
            self.db.set_setting(key, var.get())
        self.vars["max_risk"].set(self.db.get_setting("default_risk", DEFAULT_SETTINGS["default_risk"]))
        self.vars["custom_buffer"].set(self.db.get_setting("default_buffer", DEFAULT_SETTINGS["default_buffer"]))
        self._apply_instrument_profile()
        self.refresh_dashboard()
        messagebox.showinfo("Saved", "Settings saved.")

    def _load_settings(self) -> None:
        for key, var in self.setting_vars.items():
            var.set(self.db.get_setting(key, DEFAULT_SETTINGS.get(key, "")))

    def save_api_settings(self) -> None:
        save_env({key: var.get() for key, var in self.api_vars.items()})
        self.market_data = MarketDataService(load_env())
        messagebox.showinfo("Saved", "API keys saved locally to .env.")

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
