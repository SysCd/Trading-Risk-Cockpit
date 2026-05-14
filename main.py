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
    "TECH100": ("Index", "USD"),
    "NDX": ("Index", "USD"),
    "USA500": ("Index", "USD"),
    "SPX": ("Index", "USD"),
    "GER40": ("Index", "EUR"),
    "UK100": ("Index", "GBP"),
    "XAGUSD": ("Commodity", "USD"),
    "XAUUSD": ("Commodity", "USD"),
    "OIL": ("Commodity", "USD"),
    "BTCUSD": ("Crypto", "USD"),
    "ETHUSD": ("Crypto", "USD"),
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
        bg = "#f5f7fa"
        panel = "#ffffff"
        text = "#1f2937"
        accent = "#2563eb"
        self.configure(bg=bg)
        style.configure(".", background=bg, foreground=text, font=("Helvetica Neue", 12))
        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel, relief="solid", borderwidth=1)
        style.configure("Advanced.TFrame", background=panel)
        style.configure("TLabel", background=bg, foreground=text)
        style.configure("Panel.TLabel", background=panel)
        style.configure("Header.TLabel", font=("Helvetica Neue", 20, "bold"), background=bg)
        style.configure("Rule.TLabel", font=("Helvetica Neue", 11, "bold"), background=panel, foreground="#334155")
        style.configure("TButton", padding=(10, 6), font=("Helvetica Neue", 11))
        style.configure("Accent.TButton", background=accent, foreground="#ffffff")
        style.configure("Risk.TButton", padding=(8, 5), font=("Helvetica Neue", 11, "bold"))
        style.configure("Treeview", rowheight=28, font=("Helvetica Neue", 11), background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=("Helvetica Neue", 11, "bold"))
        style.configure("TNotebook.Tab", padding=(16, 8), font=("Helvetica Neue", 12, "bold"))
        self.colors = {
            "green": "#047857",
            "green_bg": "#dcfce7",
            "red": "#b91c1c",
            "red_bg": "#fee2e2",
            "yellow": "#a16207",
            "yellow_bg": "#fef3c7",
            "orange": "#b45309",
            "muted": "#64748b",
            "text": text,
            "panel": panel,
        }

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(18, 14, 18, 4))
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

    def _panel(self, parent: tk.Widget, padding: int = 12) -> ttk.Frame:
        return ttk.Frame(parent, style="Panel.TFrame", padding=padding)

    def _build_calculator_tab(self) -> None:
        self.calculator_tab.columnconfigure(0, weight=2)
        self.calculator_tab.columnconfigure(1, weight=2)
        self.calculator_tab.rowconfigure(0, weight=1)

        inputs = self._panel(self.calculator_tab)
        inputs.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = ttk.Frame(self.calculator_tab)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=0)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        quality = self._panel(right)
        quality.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        outputs = self._panel(right)
        outputs.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.checklist_panel = self._panel(right)
        self.checklist_panel.grid(row=2, column=0, sticky="nsew")

        self._build_inputs(inputs)
        self._build_quality_dashboard(quality)
        self._build_outputs(outputs)
        self._build_checklist(self.checklist_panel)
        self._toggle_advanced()

    def _add_entry(self, parent: ttk.Frame, row: int, label: str, key: str, default: str = "", width: int | None = None) -> ttk.Entry:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        var = tk.StringVar(value=default)
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 0))
        self.vars[key] = var
        return entry

    def _add_combo(self, parent: ttk.Frame, row: int, label: str, key: str, values: tuple[str, ...], default: str) -> ttk.Combobox:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        var = tk.StringVar(value=default)
        combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly")
        combo.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 0))
        self.vars[key] = var
        return combo

    def _build_inputs(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="Quick Trade Mode", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
        ttk.Label(
            parent,
            text="Six fields, calculate, done. Advanced data auto-fills from profiles and settings.",
            style="Panel.TLabel",
            foreground=self.colors["muted"],
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self._add_entry(parent, 2, "Instrument", "instrument", "AMD")
        self.vars["instrument"].trace_add("write", lambda *_: self._on_instrument_change())
        self._add_combo(parent, 3, "Direction", "direction", DIRECTIONS, "Long")
        entry = self._add_entry(parent, 4, "Entry price", "entry", "160")
        ttk.Button(parent, text="Refresh price", command=self.refresh_price).grid(row=4, column=2, sticky="ew", padx=(8, 0), pady=4)
        self._add_entry(parent, 5, "Stop price", "stop", "155")
        self._add_entry(parent, 6, "Take profit price", "take_profit", "172")
        self._add_entry(parent, 7, "Max GBP risk", "max_risk", DEFAULT_SETTINGS["default_risk"])

        risk_buttons = ttk.Frame(parent, style="Panel.TFrame")
        risk_buttons.grid(row=8, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=(0, 8))
        for value in RISK_BUTTONS:
            ttk.Button(risk_buttons, text=f"£{value}", style="Risk.TButton", command=lambda v=value: self.vars["max_risk"].set(v)).pack(
                side="left", padx=(0, 6)
            )

        ttk.Label(parent, textvariable=self.last_price_var, style="Panel.TLabel", foreground=self.colors["muted"]).grid(
            row=9, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )

        self.advanced_button = ttk.Button(parent, text="Show Advanced fields", command=self._toggle_advanced_requested)
        self.advanced_button.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(8, 6))
        self.advanced_frame = ttk.Frame(parent, style="Advanced.TFrame")
        self.advanced_frame.columnconfigure(1, weight=1)

        self._add_combo(self.advanced_frame, 0, "Asset type", "asset_type", ASSET_TYPES, "CFD")
        self._add_combo(self.advanced_frame, 1, "Currency", "currency", CURRENCIES, "USD")
        self._add_entry(self.advanced_frame, 2, "FX rate to GBP", "fx_rate", DEFAULT_SETTINGS["fx_USD"])
        ttk.Button(self.advanced_frame, text="Refresh FX", command=self.refresh_fx).grid(row=2, column=2, sticky="ew", padx=(8, 0), pady=4)
        ttk.Label(self.advanced_frame, textvariable=self.last_fx_var, style="Panel.TLabel", foreground=self.colors["muted"]).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        self._add_entry(self.advanced_frame, 4, "Support / resistance line", "support", "")
        self._add_entry(self.advanced_frame, 5, "Custom buffer %", "custom_buffer", DEFAULT_SETTINGS["default_buffer"])
        self._add_entry(self.advanced_frame, 6, "Spread cost", "spread_cost", "0")
        self._add_entry(self.advanced_frame, 7, "Overnight fee", "overnight_fee", "0")
        self._add_entry(self.advanced_frame, 8, "Commission", "commission", "0")
        self._add_entry(self.advanced_frame, 9, "Screenshot path", "screenshot_path", "")
        ttk.Label(self.advanced_frame, text="Notes / setup reason", style="Panel.TLabel").grid(row=10, column=0, sticky="nw", pady=4)
        self.notes_text = tk.Text(self.advanced_frame, height=4, wrap="word", font=("Helvetica Neue", 12), relief="solid", bd=1)
        self.notes_text.grid(row=10, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4)

        buttons = ttk.Frame(parent, style="Panel.TFrame")
        buttons.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="Calculate", style="Accent.TButton", command=self.calculate).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Save Trade", command=self.save_trade).pack(side="left", padx=4)
        ttk.Button(buttons, text="Clear Form", command=self.clear_form).pack(side="left", padx=4)
        ttk.Button(buttons, text="Copy Calculation Result", command=self.copy_calculation).pack(side="left", padx=4)

        rules = self._panel(parent, padding=10)
        rules.grid(row=13, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        for idx, text in enumerate(
            (
                "No calculator = no trade.",
                "Buy low only when support is confirmed.",
                "Risk is based on exposure, not margin.",
                "Small position first. Let winners grow.",
                "Stop-loss goes where the idea is invalidated.",
            )
        ):
            ttk.Label(rules, text=text, style="Rule.TLabel").grid(row=idx, column=0, sticky="w", pady=2)
        entry.focus_set()

    def _build_quality_dashboard(self, parent: ttk.Frame) -> None:
        parent.columnconfigure((0, 1, 2), weight=1)
        ttk.Label(parent, text="Trade Quality Dashboard", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
        labels = (
            "Risk:Reward",
            "Stop-loss %",
            "Entry distance",
            "Risk size",
            "Exposure size",
            "Overall verdict",
        )
        for idx, label in enumerate(labels):
            frame = tk.Frame(parent, bg="#f8fafc", highlightbackground="#d8dee8", highlightthickness=1, padx=10, pady=8)
            frame.grid(row=1 + idx // 3, column=idx % 3, sticky="ew", padx=4, pady=4)
            title = tk.Label(frame, text=label, bg="#f8fafc", fg=self.colors["muted"], font=("Helvetica Neue", 10, "bold"))
            title.pack(anchor="w")
            value = tk.Label(frame, text="-", bg="#f8fafc", fg=self.colors["text"], font=("Helvetica Neue", 14, "bold"))
            value.pack(anchor="w")
            self.quality_cards[label] = {"frame": frame, "title": title, "value": value}

        ttk.Label(parent, text="What must improve?", style="Panel.TLabel", font=("Helvetica Neue", 13, "bold")).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(10, 3)
        )
        self.improve_text = tk.Text(parent, height=3, wrap="word", font=("Helvetica Neue", 11), relief="solid", bd=1)
        self.improve_text.grid(row=4, column=0, columnspan=3, sticky="ew")
        self._write_improvements(["Calculate a trade to see improvement notes."])

    def _build_outputs(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="Outputs", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        rows = [
            ("Stop distance", "stop_distance"),
            ("Stop-loss %", "stop_loss_percent"),
            ("Invalidation stop", "invalidation_stop"),
            ("Units / shares / contracts", "units"),
            ("Exposure local", "exposure_local"),
            ("Exposure GBP", "exposure_gbp"),
            ("Potential GBP profit", "potential_profit"),
            ("Potential GBP loss", "potential_loss"),
            ("Net expected profit", "net_profit"),
            ("Risk:Reward", "risk_reward"),
            ("Trade valid?", "valid"),
            ("Risk label", "risk_label"),
        ]
        for row, (label, key) in enumerate(rows, start=1):
            ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=4)
            value = ttk.Label(parent, text="-", style="Panel.TLabel", font=("Helvetica Neue", 12, "bold"))
            value.grid(row=row, column=1, sticky="e", pady=4)
            self.output_labels[key] = value
        ttk.Label(parent, text="Warnings", style="Panel.TLabel", font=("Helvetica Neue", 13, "bold")).grid(
            row=13, column=0, columnspan=2, sticky="w", pady=(12, 4)
        )
        self.warning_text = tk.Text(parent, height=6, wrap="word", font=("Helvetica Neue", 12), relief="solid", bd=1)
        self.warning_text.grid(row=14, column=0, columnspan=2, sticky="nsew")
        parent.rowconfigure(14, weight=1)

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
        ttk.Button(controls, text="Delete Selected Trade", command=self.delete_selected_trade).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Update Result for Selected Trade", command=self.update_selected_result).pack(side="left", padx=4)
        ttk.Button(controls, text="Export CSV", command=self.export_csv).pack(side="left", padx=4)

        self.tree = ttk.Treeview(self.journal_tab, columns=TRADE_COLUMNS, show="headings", selectmode="browse")
        for column in TRADE_COLUMNS:
            self.tree.heading(column, text=column.replace("_", " ").title())
            width = 90 if column not in {"notes", "lesson_learned"} else 180
            self.tree.column(column, width=width, minwidth=70, stretch=True)
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_trade_select)
        scroll_y = ttk.Scrollbar(self.journal_tab, orient="vertical", command=self.tree.yview)
        scroll_y.grid(row=1, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(self.journal_tab, orient="horizontal", command=self.tree.xview)
        scroll_x.grid(row=2, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    def _build_dashboard_tab(self) -> None:
        self.dashboard_tab.columnconfigure(0, weight=1)
        self.dashboard_tab.columnconfigure(1, weight=1)
        metrics = self._panel(self.dashboard_tab)
        metrics.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.dashboard_tab.rowconfigure(0, weight=1)
        metrics.columnconfigure(1, weight=1)
        ttk.Label(metrics, text="Performance", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        self.metric_labels: dict[str, ttk.Label] = {}
        for idx, label in enumerate(
            (
                "Total trades",
                "Total P/L",
                "Win rate %",
                "Average win",
                "Average loss",
                "Profit factor",
                "Average R multiple",
                "Best instrument",
                "Worst instrument",
                "Most profitable setup",
                "Most common mistake",
                "Daily P/L",
                "Daily loss limit status",
                "Trades taken today",
                "Max trades per day status",
            ),
            start=1,
        ):
            ttk.Label(metrics, text=label, style="Panel.TLabel").grid(row=idx, column=0, sticky="w", pady=5)
            value = ttk.Label(metrics, text="-", style="Panel.TLabel", font=("Helvetica Neue", 12, "bold"))
            value.grid(row=idx, column=1, sticky="e", pady=5)
            self.metric_labels[label] = value

        notice = self._panel(self.dashboard_tab)
        notice.grid(row=0, column=1, sticky="nsew")
        ttk.Label(notice, text="Risk desk", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).pack(anchor="w")
        self.risk_status = tk.Text(notice, height=12, wrap="word", font=("Helvetica Neue", 14), relief="solid", bd=1)
        self.risk_status.pack(fill="both", expand=True, pady=(10, 0))

    def _build_settings_tab(self) -> None:
        self.settings_tab.columnconfigure(0, weight=1)
        self.settings_tab.columnconfigure(1, weight=1)
        trading = self._panel(self.settings_tab)
        trading.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        trading.columnconfigure(1, weight=1)
        ttk.Label(trading, text="Trade defaults", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        setting_rows = [
            ("Default risk", "default_risk"),
            ("Hard max risk", "hard_max_risk"),
            ("Default buffer %", "default_buffer"),
            ("Max daily loss", "daily_loss_limit"),
            ("Max trades per day", "max_trades_per_day"),
            ("Default exposure limit", "default_exposure_limit"),
        ]
        for row, (label, key) in enumerate(setting_rows, start=1):
            self._settings_entry(trading, row, label, key)
        ttk.Label(trading, text="Default FX rates to GBP", style="Panel.TLabel", font=("Helvetica Neue", 13, "bold")).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(16, 6)
        )
        for offset, currency in enumerate(FX_CURRENCIES, start=9):
            self._settings_entry(trading, offset, currency, f"fx_{currency}")
        ttk.Button(trading, text="Save Settings", style="Accent.TButton", command=self.save_settings).grid(
            row=17, column=0, columnspan=2, sticky="ew", pady=(16, 0)
        )

        api = self._panel(self.settings_tab)
        api.grid(row=0, column=1, sticky="nsew")
        api.columnconfigure(1, weight=1)
        ttk.Label(api, text="API keys", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        ttk.Label(
            api,
            text="Keys are saved locally in .env and ignored by Git. API support is read-only.",
            style="Panel.TLabel",
            foreground=self.colors["muted"],
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        api_rows = [
            ("Trading 212 API key", "TRADING212_API_KEY"),
            ("IG API key", "IG_API_KEY"),
            ("IG username", "IG_USERNAME"),
            ("IG password", "IG_PASSWORD"),
            ("IG account type", "IG_ACCOUNT_TYPE"),
            ("Market data API key", "MARKET_DATA_API_KEY"),
        ]
        for row, (label, key) in enumerate(api_rows, start=2):
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
        ttk.Button(api, text="Save API Keys", command=self.save_api_settings).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        ttk.Label(
            api,
            text="Safety: the app never auto-submits trades. yfinance data may be delayed.",
            style="Panel.TLabel",
            foreground=self.colors["orange"],
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(16, 0))

    def _settings_entry(self, parent: ttk.Frame, row: int, label: str, key: str) -> None:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        var = tk.StringVar(value=DEFAULT_SETTINGS.get(key, ""))
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=5, padx=(8, 0))
        self.setting_vars[key] = var

    def _toggle_advanced_requested(self) -> None:
        self.advanced_visible.set(not self.advanced_visible.get())
        self._toggle_advanced()

    def _toggle_advanced(self) -> None:
        if self.advanced_visible.get():
            self.advanced_frame.grid(row=11, column=0, columnspan=3, sticky="ew")
            self.checklist_panel.grid()
            self.advanced_button.configure(text="Hide Advanced fields")
        else:
            self.advanced_frame.grid_remove()
            self.checklist_panel.grid_remove()
            self.advanced_button.configure(text="Show Advanced fields")

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
        self._apply_instrument_profile()

    def _apply_instrument_profile(self) -> None:
        instrument = self.vars.get("instrument")
        if not instrument:
            return
        profile = INSTRUMENT_PROFILES.get(instrument.get().strip().upper())
        if not profile:
            return
        asset_type, currency = profile
        self.vars["asset_type"].set(asset_type)
        self.vars["currency"].set(currency)
        fx = "1" if currency == "GBP" else self.db.get_setting(f"fx_{currency}", DEFAULT_SETTINGS.get(f"fx_{currency}", "1"))
        self.vars["fx_rate"].set(fx)
        self.last_fx_var.set(f"FX source: saved {currency} default")

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
            "exposure_local": f"{result.exposure_local:,.2f} {values.currency}",
            "exposure_gbp": f"GBP {result.exposure_gbp:,.2f}",
            "potential_profit": f"GBP {result.potential_profit_gbp:,.2f}",
            "potential_loss": f"GBP {result.potential_loss_gbp:,.2f}",
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
        self.output_labels["valid"].configure(foreground=self.colors["green"] if result.valid else self.colors["red"])
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
        status_rank = {"green": 0, "yellow": 1, "red": 2}
        red_count = 0
        yellow_count = 0

        for label, assessment in assessments.items():
            if label == "Overall verdict":
                continue
            status = assessment["status"]
            red_count += status == "red"
            yellow_count += status == "yellow"
            self._set_quality_card(label, assessment["value"], status)
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

        self._set_quality_card("Overall verdict", verdict, verdict_status)
        self._write_improvements(reasons or ["No obvious issues."])
        return reasons

    def _quality_assessments(self, values: TradeInputs, result) -> dict[str, dict[str, object]]:
        stop_loss_pct = result.stop_loss_percent * 100
        entry_distance = self._entry_distance_percent(values)
        default_risk = self._setting_float("default_risk", DEFAULT_SETTINGS["default_risk"])
        hard_risk = self._setting_float("hard_max_risk", DEFAULT_SETTINGS["hard_max_risk"])
        exposure_limit = self._setting_float("default_exposure_limit", DEFAULT_SETTINGS["default_exposure_limit"])

        rr_status = "green" if result.risk_reward >= 2 else "yellow" if result.risk_reward >= 1.5 else "red"
        rr_reasons = [] if rr_status == "green" else ["Risk:Reward too low"]

        stop_status, stop_reason = self._stop_loss_status(values, stop_loss_pct)
        distance_status = "green" if 0 <= entry_distance <= 1 else "yellow" if entry_distance <= 2 else "red"
        distance_reasons = [] if distance_status == "green" else ["Entry too far from support"]

        if values.max_risk_gbp <= default_risk:
            risk_status = "green"
        elif values.max_risk_gbp <= hard_risk:
            risk_status = "yellow"
        else:
            risk_status = "red"
        risk_reasons = [] if risk_status == "green" else ["Position too large"]

        if result.exposure_gbp <= exposure_limit:
            exposure_status = "green"
        elif result.exposure_gbp <= exposure_limit * 1.5:
            exposure_status = "yellow"
        else:
            exposure_status = "red"
        exposure_reasons = [] if exposure_status == "green" else ["Position too large"]

        return {
            "Risk:Reward": {
                "value": f"{result.risk_reward:.2f}",
                "status": rr_status,
                "reasons": rr_reasons,
            },
            "Stop-loss %": {
                "value": f"{stop_loss_pct:.2f}%",
                "status": stop_status,
                "reasons": [stop_reason] if stop_reason else [],
            },
            "Entry distance": {
                "value": f"{entry_distance:.2f}%",
                "status": distance_status,
                "reasons": distance_reasons,
            },
            "Risk size": {
                "value": f"GBP {values.max_risk_gbp:.2f}",
                "status": risk_status,
                "reasons": risk_reasons,
            },
            "Exposure size": {
                "value": f"GBP {result.exposure_gbp:,.0f}",
                "status": exposure_status,
                "reasons": exposure_reasons,
            },
            "Overall verdict": {"value": "-", "status": "yellow", "reasons": []},
        }

    def _entry_distance_percent(self, values: TradeInputs) -> float:
        if values.support_line <= 0:
            return 999.0
        if values.direction == "Short":
            return max(0.0, (values.support_line - values.entry_price) / values.support_line * 100)
        return max(0.0, (values.entry_price - values.support_line) / values.support_line * 100)

    def _stop_loss_status(self, values: TradeInputs, stop_loss_pct: float) -> tuple[str, str]:
        green, yellow = self._stop_loss_ranges(values)
        if green[0] <= stop_loss_pct <= green[1]:
            return "green", ""
        if yellow[0] <= stop_loss_pct <= yellow[1]:
            reason = "Stop too tight" if stop_loss_pct < green[0] else "Stop too wide"
            return "yellow", reason
        reason = "Stop too tight" if stop_loss_pct < yellow[0] else "Stop too wide"
        return "red", reason

    def _stop_loss_ranges(self, values: TradeInputs) -> tuple[tuple[float, float], tuple[float, float]]:
        instrument = values.instrument.upper()
        asset_type = values.asset_type
        if asset_type == "Index":
            return (0.3, 1.2), (0.2, 1.8)
        if asset_type == "3x ETP":
            return (2.0, 6.0), (1.5, 8.0)
        if instrument in {"XAUUSD", "XAGUSD"}:
            return (0.5, 2.0), (0.3, 3.0)
        if instrument == "OIL":
            return (0.8, 3.0), (0.5, 4.0)
        if asset_type == "Forex":
            return (0.2, 0.8), (0.1, 1.2)
        if asset_type == "Crypto":
            return (2.0, 6.0), (1.0, 10.0)
        return (0.8, 2.5), (0.5, 3.5)

    def _set_quality_card(self, label: str, value: str, status: str) -> None:
        colors = {
            "green": (self.colors["green_bg"], self.colors["green"]),
            "yellow": (self.colors["yellow_bg"], self.colors["yellow"]),
            "red": (self.colors["red_bg"], self.colors["red"]),
        }
        bg, fg = colors[status]
        card = self.quality_cards[label]
        frame = card["frame"]
        title = card["title"]
        value_label = card["value"]
        assert isinstance(frame, tk.Frame)
        assert isinstance(title, tk.Label)
        assert isinstance(value_label, tk.Label)
        frame.configure(bg=bg)
        title.configure(bg=bg, fg=fg)
        value_label.configure(text=value, bg=bg, fg=fg)

    def _write_improvements(self, reasons: list[str]) -> None:
        cleaned: list[str] = []
        for reason in reasons:
            if reason and reason not in cleaned:
                cleaned.append(reason)
        self.improve_text.configure(state="normal")
        self.improve_text.delete("1.0", "end")
        self.improve_text.insert("1.0", "\n".join(cleaned[:8]))
        self.improve_text.configure(state="disabled")

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
        self.last_price_var.set(f"Last price: {quote.value:.4f} from {quote.source}{delay} at {quote.timestamp}")

    def refresh_fx(self) -> None:
        currency = self.vars["currency"].get()
        quote = self.market_data.latest_fx_to_gbp(currency)
        if quote is None:
            self.last_fx_var.set("FX source: unavailable, saved/manual rate active")
            self._write_warnings(["Live FX unavailable. Keep manual entry available."])
            return
        self.vars["fx_rate"].set(f"{quote.value:.6f}")
        delay = " delayed" if quote.delayed else ""
        self.last_fx_var.set(f"FX source: {quote.source}{delay} at {quote.timestamp}")

    def _write_warnings(self, messages: list[str]) -> None:
        self.warning_text.configure(state="normal")
        self.warning_text.delete("1.0", "end")
        self.warning_text.insert("1.0", "\n".join(messages) if messages else "No warnings.")
        self.warning_text.configure(state="disabled")

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
            label.configure(text="-", foreground=self.colors["text"])
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
            self.tree.insert("", "end", iid=str(row["id"]), values=values)

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
                label.configure(foreground=self.colors["green"] if not value.startswith("GBP -") else self.colors["red"])
            elif "stop trading" in value:
                label.configure(foreground=self.colors["red"])
            else:
                label.configure(foreground=self.colors["text"])

        status_lines = ["No calculator = no trade."]
        if self._daily_loss_hit():
            status_lines.append("Daily loss limit hit - stop trading.")
        if self._max_trades_hit():
            status_lines.append("Max trades reached - stop trading.")
        if len(status_lines) == 1:
            status_lines.append("Risk controls are currently within limits.")
        self.risk_status.configure(state="normal")
        self.risk_status.delete("1.0", "end")
        self.risk_status.insert("1.0", "\n".join(status_lines))
        self.risk_status.configure(state="disabled")

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
