"""SQLite storage for Trading Risk Cockpit."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path("trading_risk_cockpit.sqlite3")


TRADE_COLUMNS = [
    "id",
    "created_at",
    "instrument",
    "asset_type",
    "currency",
    "fx_rate",
    "direction",
    "entry",
    "stop",
    "take_profit",
    "max_risk",
    "units",
    "exposure_gbp",
    "potential_profit",
    "risk_reward",
    "setup_type",
    "emotion_before",
    "result_gbp",
    "win_loss",
    "r_multiple",
    "mistake_made",
    "lesson_learned",
    "screenshot_path",
    "notes",
]


class TradingDatabase:
    def __init__(self, path: Path | str = DB_PATH) -> None:
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                instrument TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                currency TEXT NOT NULL,
                fx_rate REAL NOT NULL,
                direction TEXT NOT NULL,
                entry REAL NOT NULL,
                stop REAL NOT NULL,
                take_profit REAL NOT NULL,
                max_risk REAL NOT NULL,
                units REAL NOT NULL,
                exposure_gbp REAL NOT NULL,
                potential_profit REAL NOT NULL,
                risk_reward REAL NOT NULL,
                setup_type TEXT NOT NULL,
                emotion_before TEXT NOT NULL,
                result_gbp REAL DEFAULT 0,
                win_loss TEXT DEFAULT '',
                r_multiple REAL DEFAULT 0,
                mistake_made TEXT DEFAULT '',
                lesson_learned TEXT DEFAULT '',
                screenshot_path TEXT DEFAULT '',
                notes TEXT DEFAULT ''
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def add_trade(self, data: dict[str, Any]) -> int:
        keys = [key for key in data.keys() if key != "id"]
        placeholders = ", ".join("?" for _ in keys)
        query = f"INSERT INTO trades ({', '.join(keys)}) VALUES ({placeholders})"
        cur = self.conn.execute(query, [data[key] for key in keys])
        self.conn.commit()
        return int(cur.lastrowid)

    def update_result(
        self,
        trade_id: int,
        result_gbp: float,
        win_loss: str,
        r_multiple: float,
        mistake_made: str,
        lesson_learned: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE trades
               SET result_gbp = ?,
                   win_loss = ?,
                   r_multiple = ?,
                   mistake_made = ?,
                   lesson_learned = ?
             WHERE id = ?
            """,
            (result_gbp, win_loss, r_multiple, mistake_made, lesson_learned, trade_id),
        )
        self.conn.commit()

    def delete_trade(self, trade_id: int) -> None:
        self.conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
        self.conn.commit()

    def all_trades(self) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM trades ORDER BY created_at DESC, id DESC"))

    def trades_today(self, date_prefix: str) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM trades WHERE created_at LIKE ? ORDER BY created_at DESC",
                (f"{date_prefix}%",),
            )
        )

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else default

    def export_csv(self, path: Path | str) -> None:
        rows = self.all_trades()
        with Path(path).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(TRADE_COLUMNS)
            for row in rows:
                writer.writerow([row[column] for column in TRADE_COLUMNS])

    def close(self) -> None:
        self.conn.close()
