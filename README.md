# Trading Risk Cockpit

Trading Risk Cockpit is a local Python 3 desktop app for fast pre-trade sizing, risk checks, journaling, and simple performance review. It uses CustomTkinter for the modern desktop UI, SQLite for storage, optional Twelve Data / yfinance market data, and CSV export for external analysis.

## Run on macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The app stores its journal in `trading_risk_cockpit.sqlite3` in the project folder.

## Quick Trade Mode

The Calculator tab opens as a trader workstation with a left input panel, center trade quality panel, right summary panel, and bottom notes/rules/recent-activity strip. To calculate a trade, enter only:

- Instrument
- Direction
- Entry price
- Stop price
- Take profit price
- Max GBP risk

The app auto-fills the rest from instrument profiles and saved settings:

- Asset type and currency from the instrument profile
- FX rate from Settings
- Buffer default from Settings, initially `0.8%`
- Spread, overnight fee, and commission default to `0`
- Quick max-risk buttons: `£3`, `£5`, `£10`, `£20`, `£50`

Use **Show Advanced fields** to edit FX rate, asset type, leverage, support/resistance, buffer, costs, notes, checklist, and screenshot path.

## Instrument Autocomplete

The app preloads a local `data/instruments.json` catalog so suggestions appear instantly as you type. Search works by ticker, company/fund name, asset type, category, broker symbol, or API symbol.

Seeded examples include:

- Stocks/CFDs: `TSLA`, `NVDA`, `AMD`, `MSFT`, `AAPL`, `AMZN`, `GOOGL`, `META`, `PLTR`, `INTC`, `ASML`
- ETFs/ETPs: `VUAG`, `VUSA`, `QQQ`, `SPY`, `TQQQ`
- CFDs/indices/commodities/forex: `TECH100`, `NDX`, `USA500`, `GER40`, `UK100`, `XAUUSD`, `XAGUSD`, `CRUDE`, `EURUSD`, `GBPUSD`, `USDJPY`

Selecting a suggestion fills ticker, asset class, currency, leverage profile, and FX defaults, then can refresh price and FX data without blocking manual entry.

## Code Layout

- `main.py`: CustomTkinter app shell and workflow wiring
- `ui/`: theme, reusable components, modal dialogs, layout constants
- `data/`: local instrument catalog, catalog loader, market-data compatibility wrapper
- `logic/`: calculator compatibility wrapper, validation helpers, trade-quality recommendations
- `calculator.py`, `database.py`, `market_data.py`: core calculation, SQLite persistence, and market data providers

## Instrument Profiles

- `TSLA`, `NVDA`, `AMD`, `MSFT`, `PLTR`, `ASML`: USD stock/CFD profile
- `TECH100`, `USA500`: USD index
- `NDX`, `SPX`: USD index aliases
- `GER40`: EUR index
- `UK100`: GBP index
- `XAGUSD`, `XAUUSD`, `OIL`, `CRUDE`: USD commodity
- `BTCUSD`, `ETHUSD`: USD crypto
- Major forex pairs such as `EURUSD`, `GBPUSD`, and `USDJPY`: forex profile

## Leverage And Margin

The app auto-fills typical UK/EU retail CFD leverage defaults, and the leverage field can be manually overridden if your broker uses a different rate.

- Stock CFDs such as `TSLA`, `NVDA`, `AMD`, `MSFT`, `PLTR`, `ASML`: `5x`
- Major indices such as `TECH100`, `NDX`, `USA500`, `SPX`, `GER40`, `UK100`: `20x`
- Major forex pairs such as `EURUSD`, `GBPUSD`, `USDJPY`: `30x`
- Gold `XAUUSD`: `20x`
- Silver `XAGUSD`: `10x`
- Oil `OIL` / `CRUDE`: `10x`
- Crypto `BTCUSD`, `ETHUSD`: `2x`
- `3x ETP`: `1x` by default because it is already leveraged

Leverage affects margin, not P/L. For stock CFDs, `5x` leverage means `GBP 100` margin controls `GBP 500` exposure. Profit and loss are calculated from the `GBP 500` exposure, not from the `GBP 100` margin.

## Trade Quality Dashboard

The top-right calculator panel shows compact status cards for:

- Risk:Reward
- Stop-loss %
- Entry distance from support/resistance
- Risk size
- Exposure size
- Margin required
- Overall verdict

Cards use green for good, yellow for caution, and red for bad. Each card shows the current value, the target range, and a small gap line where useful, such as `Need R:R +0.25`, `Entry 0.8% too far`, or `Stop too tight by 0.2%`. The verdict is `Ideal`, `Acceptable`, `Borderline`, or `Avoid`. The "What must improve?" box gives concise reasons such as low Risk:Reward, entry too far from support, stop too tight or wide, oversized position, invalid trade, daily loss limit hit, or max trades reached.

## Settings

The Settings tab lets you edit:

- Default FX rates to GBP for USD, EUR, CHF, JPY, CAD, AUD, and NZD
- Default risk
- Hard max risk
- Default buffer
- Max daily loss
- Max trades per day
- Default exposure limit
- API keys for optional read-only market data integrations

API keys are saved locally in `.env`, which is ignored by Git.

## Optional Live Data

The app includes `market_data.py` with a provider interface, Twelve Data support, and a free/simple `yfinance` fallback where possible. It can fetch latest available FX rates and prices for common instruments, then fill Entry Price or FX Rate.

To use Twelve Data:

1. Create an account and API key at [twelvedata.com](https://twelvedata.com/).
2. Add the key in the Settings tab, or create a local `.env` file:

```bash
TWELVE_DATA_API_KEY=your_key_here
```

`.env` is ignored by Git. Never commit API keys.

Supported refresh targets include:

- FX: `USDGBP`, `EURGBP`, `CHFGBP`, `JPYGBP`, `CADGBP`, `AUDGBP`, `NZDGBP`
- Prices: `TSLA`, `NVDA`, `AMD`, `MSFT`, `PLTR`, `ASML`, `NDX` / `TECH100` where supported, `SPY`, `QQQ`, `XAG/USD`, `XAU/USD`, `BTC/USD`, `ETH/USD`, plus existing yfinance fallbacks for common indices and commodities.

Buttons:

- **Refresh price** fills Entry Price and shows timestamp/source.
- **Refresh FX** fills FX rate to GBP and shows timestamp/source.

If data fails, manual entry remains available. `Trading212Provider`, `IGProvider`, and `IBKRProvider` placeholders are included for future read-only integration. They do not place orders.

Safety notes:

- The app never auto-submits trades.
- Do not store API keys in GitHub.
- Market data is only for convenience/autofill.
- If live price differs from your broker, use broker price for final execution.
- Free market data can be delayed. The app warns when delayed/fallback data is used.

## Core Formulas

- Stop distance = `ABS(entry - stop)`
- Stop-loss % = `stop distance / entry`
- Units = `Max GBP Risk / (Stop distance * FX rate to GBP)`
- Exposure local = `Units * Entry`
- Exposure GBP = `Units * Entry * FX rate to GBP`
- Required margin local = `Exposure local / Leverage`
- Required margin GBP = `Exposure GBP / Leverage`
- Potential GBP profit = `Units * ABS(Take Profit - Entry) * FX rate to GBP`
- Potential GBP loss = `Units * ABS(Entry - Stop) * FX rate to GBP`
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
- At `5x` leverage, required margin is approximately `USD 405.06`, or `GBP 320.00`.
- Potential profit is approximately `GBP 120.00`.
- Potential loss is approximately `GBP 50.00`.
- Risk:Reward is approximately `2.40`.
- The CFD exposure and leverage warnings are shown.

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
