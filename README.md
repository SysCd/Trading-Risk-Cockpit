# Trading Risk Cockpit

Trading Risk Cockpit is a local Python 3 desktop app for pre-trade sizing, risk checks, journaling, and simple performance review. It uses `tkinter` for the GUI, SQLite for storage, and CSV export for external analysis.

## Run on macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

`tkinter` ships with the standard Python installers on macOS. The app stores its journal in `trading_risk_cockpit.sqlite3` in the project folder.

## Core Formulas

- Stop distance = `ABS(entry - stop)`
- Stop-loss % = `stop distance / entry`
- Units = `Max GBP Risk / (Stop distance * FX rate to GBP)`
- Exposure local = `Units * Entry`
- Exposure GBP = `Units * Entry * FX rate to GBP`
- Potential GBP profit = `Units * ABS(Take Profit - Entry) * FX rate to GBP`
- Potential GBP loss = `Max GBP Risk`
- Net expected profit = `Potential GBP profit - spread cost - overnight fee - commission`
- Risk:Reward = `Potential GBP profit / Max GBP Risk`
- Long invalidation stop = `Support * (1 - Buffer%)`
- Short invalidation stop = `Resistance * (1 + Buffer%)`

## Validation Rules

- Long trades require stop below entry and take profit above entry.
- Short trades require stop above entry and take profit below entry.
- Risk:Reward must be at least `2`.
- Max risk above `GBP 50` shows a warning.
- Stop-loss under `0.3%` shows a "Stop may be too tight" warning.
- CFDs show: "Risk is based on exposure, not margin."
- 3x ETPs show: "Use wider stop and smaller size."

## AMD CFD Example

Example inputs:

- Instrument: `AMD`
- Asset type: `CFD`
- Currency: `USD`
- FX rate to GBP: `0.79`
- Direction: `Long`
- Entry: `160`
- Stop: `155`
- Take profit: `172`
- Max GBP risk: `50`
- Support line: `156`
- Buffer: `0.8%`
- Spread cost: `1.50`

Expected interpretation:

- Stop distance is `5`.
- Position size is approximately `12.66` contracts or units.
- Exposure is approximately `USD 2,025.32`, or `GBP 1,600.00`.
- Potential profit is approximately `GBP 120.00`.
- Risk:Reward is approximately `2.40`.
- The CFD exposure warning is shown.

## CSV Export

Use **Export CSV** from the Journal tab. The app writes the full journal table, including setup type, emotion, result, R multiple, mistakes, lessons, screenshot path, and notes. The default export folder is `exports/`, which is ignored by Git.

## Screenshots

Add screenshots here after capturing the running app:

- Calculator tab screenshot placeholder
- Journal tab screenshot placeholder
- Dashboard tab screenshot placeholder

## Trading Rules Displayed In The App

- No calculator = no trade.
- Buy low only when support is confirmed.
- Risk is based on exposure, not margin.
- Small position first. Let winners grow.
- Stop-loss goes where the idea is invalidated.

## Disclaimer

This project is an educational tool only. It is not financial advice, investment advice, trading advice, or a recommendation to buy or sell any financial instrument. Trading involves risk, and you are responsible for your own decisions.
