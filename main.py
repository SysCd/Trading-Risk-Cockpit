"""Trading Risk Cockpit tkinter application."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from calculator import (
    ASSET_TYPES,
    BUFFER_OPTIONS,
    CURRENCIES,
    DIRECTIONS,
    TradeInputs,
    calculate_trade,
    grade_checklist,
)
from database import TRADE_COLUMNS, TradingDatabase


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


class TradingRiskCockpit(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Trading Risk Cockpit")
        self.geometry("1280x820")
        self.minsize(1100, 720)
        self.db = TradingDatabase()
        self.current_result = None
        self.selected_trade_id: int | None = None
        self.vars: dict[str, tk.Variable] = {}
        self.output_labels: dict[str, ttk.Label] = {}
        self.check_vars: list[tk.BooleanVar] = []

        self._setup_style()
        self._build_ui()
        self._load_settings()
        self.refresh_journal()
        self.refresh_dashboard()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        bg = "#f5f7fa"
        panel = "#ffffff"
        border = "#d8dee8"
        text = "#1f2937"
        accent = "#2563eb"
        self.configure(bg=bg)
        style.configure(".", background=bg, foreground=text, font=("Helvetica Neue", 12))
        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel, relief="solid", borderwidth=1)
        style.configure("TLabel", background=bg, foreground=text)
        style.configure("Panel.TLabel", background=panel)
        style.configure("Header.TLabel", font=("Helvetica Neue", 20, "bold"), background=bg)
        style.configure("Rule.TLabel", font=("Helvetica Neue", 11, "bold"), background=panel, foreground="#334155")
        style.configure("TButton", padding=(10, 6), font=("Helvetica Neue", 11))
        style.map("TButton", background=[("active", "#e5edff")])
        style.configure("Accent.TButton", background=accent, foreground="#ffffff")
        style.configure("Treeview", rowheight=28, font=("Helvetica Neue", 11), background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=("Helvetica Neue", 11, "bold"))
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 8), font=("Helvetica Neue", 12, "bold"))
        self.colors = {
            "green": "#047857",
            "red": "#b91c1c",
            "orange": "#b45309",
            "muted": "#64748b",
            "panel": panel,
            "border": border,
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
        self.notebook.add(self.calculator_tab, text="Calculator")
        self.notebook.add(self.journal_tab, text="Journal")
        self.notebook.add(self.dashboard_tab, text="Dashboard")

        self._build_calculator_tab()
        self._build_journal_tab()
        self._build_dashboard_tab()

    def _panel(self, parent: tk.Widget, padding: int = 12) -> ttk.Frame:
        return ttk.Frame(parent, style="Panel.TFrame", padding=padding)

    def _build_calculator_tab(self) -> None:
        self.calculator_tab.columnconfigure(0, weight=2)
        self.calculator_tab.columnconfigure(1, weight=2)
        self.calculator_tab.rowconfigure(1, weight=1)

        inputs = self._panel(self.calculator_tab)
        inputs.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10), pady=0)
        outputs = self._panel(self.calculator_tab)
        outputs.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        checklist = self._panel(self.calculator_tab)
        checklist.grid(row=1, column=1, sticky="nsew")

        self._build_inputs(inputs)
        self._build_outputs(outputs)
        self._build_checklist(checklist)

    def _add_entry(self, parent: ttk.Frame, row: int, label: str, key: str, default: str = "") -> None:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        var = tk.StringVar(value=default)
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 0))
        self.vars[key] = var

    def _add_combo(self, parent: ttk.Frame, row: int, label: str, key: str, values: tuple[str, ...], default: str) -> None:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        var = tk.StringVar(value=default)
        combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly")
        combo.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 0))
        self.vars[key] = var

    def _build_inputs(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="Pre-trade calculator", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        fields = [
            ("Instrument / ticker", "instrument", "AMD"),
            ("FX rate to GBP", "fx_rate", "0.79"),
            ("Entry price", "entry", "160"),
            ("Stop price", "stop", "155"),
            ("Take profit price", "take_profit", "172"),
            ("Max GBP risk", "max_risk", "50"),
            ("Support / resistance line", "support", "156"),
            ("Custom buffer %", "custom_buffer", "0.8"),
            ("Spread cost", "spread_cost", "1.50"),
            ("Overnight fee", "overnight_fee", "0"),
            ("Commission", "commission", "0"),
        ]
        self._add_combo(parent, 1, "Asset type", "asset_type", ASSET_TYPES, "CFD")
        self._add_combo(parent, 2, "Currency", "currency", CURRENCIES, "USD")
        self._add_combo(parent, 3, "Direction", "direction", DIRECTIONS, "Long")
        self._add_combo(parent, 4, "Buffer", "buffer_option", BUFFER_OPTIONS, "0.8%")
        for offset, (label, key, default) in enumerate(fields, start=5):
            self._add_entry(parent, offset, label, key, default)

        ttk.Label(parent, text="Notes / setup reason", style="Panel.TLabel").grid(row=16, column=0, sticky="nw", pady=4)
        self.notes_text = tk.Text(parent, height=4, wrap="word", font=("Helvetica Neue", 12), relief="solid", bd=1)
        self.notes_text.grid(row=16, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.notes_text.insert("1.0", "Support bounce near prior demand.")

        buttons = ttk.Frame(parent, style="Panel.TFrame")
        buttons.grid(row=17, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="Calculate", style="Accent.TButton", command=self.calculate).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Save Trade", command=self.save_trade).pack(side="left", padx=4)
        ttk.Button(buttons, text="Clear Form", command=self.clear_form).pack(side="left", padx=4)
        ttk.Button(buttons, text="Copy Calculation Result", command=self.copy_calculation).pack(side="left", padx=4)

        rules = self._panel(parent, padding=10)
        rules.grid(row=18, column=0, columnspan=2, sticky="ew", pady=(12, 0))
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
        ttk.Label(parent, text="Pre-trade checklist", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).grid(
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
        settings = self._panel(self.dashboard_tab)
        settings.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Label(settings, text="Risk controls", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).pack(side="left", padx=(0, 18))
        self.daily_loss_limit = tk.StringVar(value="150")
        self.max_trades_per_day = tk.StringVar(value="3")
        ttk.Label(settings, text="Daily loss limit", style="Panel.TLabel").pack(side="left")
        ttk.Entry(settings, textvariable=self.daily_loss_limit, width=10).pack(side="left", padx=(6, 18))
        ttk.Label(settings, text="Max trades per day", style="Panel.TLabel").pack(side="left")
        ttk.Entry(settings, textvariable=self.max_trades_per_day, width=8).pack(side="left", padx=(6, 18))
        ttk.Button(settings, text="Save Settings", command=self.save_settings).pack(side="left")

        metrics = self._panel(self.dashboard_tab)
        metrics.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        self.dashboard_tab.rowconfigure(1, weight=1)
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
        notice.grid(row=1, column=1, sticky="nsew")
        ttk.Label(notice, text="Risk desk", style="Panel.TLabel", font=("Helvetica Neue", 16, "bold")).pack(anchor="w")
        self.risk_status = tk.Text(notice, height=12, wrap="word", font=("Helvetica Neue", 14), relief="solid", bd=1)
        self.risk_status.pack(fill="both", expand=True, pady=(10, 0))

    def _float(self, key: str) -> float:
        return float(str(self.vars[key].get()).replace(",", "").strip())

    def _buffer_percent(self) -> float:
        option = self.vars["buffer_option"].get()
        if option == "Custom":
            return self._float("custom_buffer") / 100
        return float(option.replace("%", "")) / 100

    def _trade_inputs(self) -> TradeInputs:
        return TradeInputs(
            instrument=self.vars["instrument"].get().strip(),
            asset_type=self.vars["asset_type"].get(),
            currency=self.vars["currency"].get(),
            fx_rate_to_gbp=self._float("fx_rate"),
            direction=self.vars["direction"].get(),
            entry_price=self._float("entry"),
            stop_price=self._float("stop"),
            take_profit_price=self._float("take_profit"),
            max_risk_gbp=self._float("max_risk"),
            support_line=self._float("support"),
            buffer_percent=self._buffer_percent(),
            spread_cost=self._float("spread_cost"),
            overnight_fee=self._float("overnight_fee"),
            commission=self._float("commission"),
            notes=self.notes_text.get("1.0", "end").strip(),
        )

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
        self.output_labels["net_profit"].configure(
            foreground=self.colors["green"] if result.net_expected_profit_gbp >= 0 else self.colors["red"]
        )
        self.output_labels["valid"].configure(foreground=self.colors["green"] if result.valid else self.colors["red"])
        self.output_labels["risk_label"].configure(
            foreground=self.colors["green"] if result.risk_label in {"Safe", "Moderate"} else self.colors["orange"]
        )
        self._write_warnings(result.errors + result.warnings)
        self._sync_checklist_from_result(result)
        self.refresh_dashboard()

    def _write_warnings(self, messages: list[str]) -> None:
        self.warning_text.configure(state="normal")
        self.warning_text.delete("1.0", "end")
        if messages:
            self.warning_text.insert("1.0", "\n".join(messages))
        else:
            self.warning_text.insert("1.0", "No warnings.")
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
        invalid = False
        if self.current_result is not None and not self.current_result.valid:
            invalid = True
        if len(self.check_vars) >= 8 and not self.check_vars[5].get():
            invalid = True
        if len(self.check_vars) >= 8 and not self.check_vars[7].get():
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
        if not self.current_result.valid:
            if not messagebox.askyesno("Invalid trade", "This trade is invalid. Save it as a journal record anyway?"):
                return
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "created_at": now,
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
            "screenshot_path": "",
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
        for key, var in self.vars.items():
            if key in {"asset_type", "currency", "direction", "buffer_option"}:
                continue
            var.set("")
        self.notes_text.delete("1.0", "end")
        self.current_result = None
        for label in self.output_labels.values():
            label.configure(text="-", foreground="#1f2937")
        self._write_warnings(["No calculator = no trade."])
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
            limit = abs(float(self.daily_loss_limit.get()))
        except ValueError:
            return False
        daily_pl = sum(float(row["result_gbp"] or 0) for row in self.db.trades_today(dt.date.today().isoformat()))
        return daily_pl <= -limit

    def _max_trades_hit(self) -> bool:
        try:
            max_trades = int(float(self.max_trades_per_day.get()))
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
                label.configure(foreground="#1f2937")

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
        self.db.set_setting("daily_loss_limit", self.daily_loss_limit.get())
        self.db.set_setting("max_trades_per_day", self.max_trades_per_day.get())
        self.refresh_dashboard()
        messagebox.showinfo("Saved", "Risk settings saved.")

    def _load_settings(self) -> None:
        self.daily_loss_limit.set(self.db.get_setting("daily_loss_limit", "150"))
        self.max_trades_per_day.set(self.db.get_setting("max_trades_per_day", "3"))

    def _on_close(self) -> None:
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = TradingRiskCockpit()
    app.mainloop()
