"""Trade quality scoring and improvement hints."""

from __future__ import annotations

from calculator import CalculationResult, TradeInputs
from .validation import status_from_counts


def entry_distance_percent(values: TradeInputs) -> float:
    if values.support_line <= 0:
        return 999.0
    if values.direction == "Short":
        return max(0.0, (values.support_line - values.entry_price) / values.support_line * 100)
    return max(0.0, (values.entry_price - values.support_line) / values.support_line * 100)


def stop_loss_ranges(values: TradeInputs) -> tuple[tuple[float, float], tuple[float, float], str]:
    instrument = values.instrument.upper()
    asset_type = values.asset_type
    if asset_type == "Index":
        return (0.3, 1.2), (0.2, 1.8), "Target: 0.3%-1.2%"
    if asset_type == "3x ETP":
        return (2.0, 6.0), (1.5, 8.0), "Target: 2%-6%"
    if instrument in {"XAUUSD", "XAGUSD"}:
        return (0.5, 2.0), (0.3, 3.0), "Target: 0.5%-2%"
    if instrument in {"OIL", "CRUDE"}:
        return (0.8, 3.0), (0.5, 4.0), "Target: 0.8%-3%"
    if asset_type == "Forex":
        return (0.2, 0.8), (0.1, 1.2), "Target: 0.2%-0.8%"
    if asset_type == "Crypto":
        return (2.0, 6.0), (1.0, 10.0), "Target: 2%-6%"
    return (0.8, 2.5), (0.5, 3.5), "Target: 0.8%-2.5%"


def _stop_status(values: TradeInputs, stop_pct: float) -> tuple[str, str, str]:
    green, yellow, target = stop_loss_ranges(values)
    if green[0] <= stop_pct <= green[1]:
        return "good", target, ""
    if yellow[0] <= stop_pct <= yellow[1]:
        if stop_pct < green[0]:
            return "ok", target, f"Stop too tight by {green[0] - stop_pct:.2f}%"
        return "ok", target, f"Stop too wide by {stop_pct - green[1]:.2f}%"
    if stop_pct < yellow[0]:
        return "bad", target, f"Stop too tight by {green[0] - stop_pct:.2f}%"
    return "bad", target, f"Stop too wide by {stop_pct - green[1]:.2f}%"


def quality_assessments(
    values: TradeInputs,
    result: CalculationResult,
    default_risk: float,
    hard_risk: float,
    exposure_limit: float,
    daily_loss_hit: bool,
    max_trades_hit: bool,
) -> tuple[dict[str, dict[str, str]], list[str]]:
    stop_pct = result.stop_loss_percent * 100
    entry_distance = entry_distance_percent(values)
    reasons: list[str] = []

    rr_status = "good" if result.risk_reward >= 2 else "ok" if result.risk_reward >= 1.5 else "bad"
    rr_gap = "" if result.risk_reward >= 2 else f"Need R:R +{2 - result.risk_reward:.2f}"
    if rr_status != "good":
        reasons.append("Risk:Reward too low")

    stop_status, stop_target, stop_gap = _stop_status(values, stop_pct)
    if stop_gap:
        reasons.append("Stop too tight" if "tight" in stop_gap else "Stop too wide")

    distance_status = "good" if entry_distance <= 1 else "ok" if entry_distance <= 2 else "bad"
    distance_gap = "" if entry_distance <= 1 else f"Entry {entry_distance - 1:.2f}% too far"
    if distance_status != "good":
        reasons.append("Entry too far from support" if values.direction == "Long" else "Entry too far from resistance")

    risk_status = "good" if values.max_risk_gbp <= default_risk else "ok" if values.max_risk_gbp <= hard_risk else "bad"
    risk_gap = "" if risk_status == "good" else f"Risk GBP {values.max_risk_gbp - default_risk:.2f} over"
    if risk_status != "good":
        reasons.append("Position too large")

    exposure_status = "good" if result.exposure_gbp <= exposure_limit else "ok" if result.exposure_gbp <= exposure_limit * 1.5 else "bad"
    exposure_gap = "" if exposure_status == "good" else f"Exposure GBP {result.exposure_gbp - exposure_limit:,.0f} over"
    if exposure_status != "good" and "Position too large" not in reasons:
        reasons.append("Position too large")

    invalid = not result.valid or daily_loss_hit or max_trades_hit
    red_count = sum(1 for status in [rr_status, stop_status, distance_status, risk_status, exposure_status] if status == "bad")
    yellow_count = sum(1 for status in [rr_status, stop_status, distance_status, risk_status, exposure_status] if status == "ok")
    verdict, verdict_status = status_from_counts(red_count, yellow_count, invalid)

    if not result.valid:
        reasons.insert(0, "Trade invalid")
    if daily_loss_hit:
        reasons.insert(0, "Daily loss limit hit")
    if max_trades_hit:
        reasons.insert(0, "Max trades reached")

    distance_target = "Target: 0%-1% from resistance" if values.direction == "Short" else "Target: 0%-1% from support"
    assessments = {
        "Risk:Reward": {"value": f"{result.risk_reward:.2f}", "target": "Target: 2.0+", "status": rr_status, "hint": rr_gap},
        "Stop-loss %": {"value": f"{stop_pct:.2f}%", "target": stop_target, "status": stop_status, "hint": stop_gap},
        "Entry distance": {"value": f"{entry_distance:.2f}%", "target": distance_target, "status": distance_status, "hint": distance_gap},
        "Risk size": {"value": f"GBP {values.max_risk_gbp:.2f}", "target": f"Target: <= GBP {default_risk:g}", "status": risk_status, "hint": risk_gap},
        "Exposure size": {
            "value": f"GBP {result.exposure_gbp:,.0f} exposure",
            "target": f"Target: <= GBP {exposure_limit:g}",
            "status": exposure_status,
            "hint": exposure_gap,
        },
        "Margin required": {
            "value": f"GBP {result.required_margin_gbp:,.0f}",
            "target": "Based on leverage used",
            "status": exposure_status,
            "hint": f"Leverage: {result.leverage:g}x",
        },
        "Overall verdict": {"value": verdict, "target": "Target: Ideal / Acceptable", "status": verdict_status, "hint": ""},
    }
    clean_reasons: list[str] = []
    for reason in reasons:
        if reason and reason not in clean_reasons:
            clean_reasons.append(reason)
    return assessments, clean_reasons or ["No major issues"]
