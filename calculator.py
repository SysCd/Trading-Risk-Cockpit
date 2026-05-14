"""Calculation and validation logic for Trading Risk Cockpit."""

from __future__ import annotations

from dataclasses import dataclass, field


ASSET_TYPES = ("Stock", "CFD", "3x ETP", "Index", "Commodity", "Forex", "Crypto")
CURRENCIES = ("GBP", "USD", "EUR", "CHF", "JPY", "CAD", "AUD", "NZD")
DIRECTIONS = ("Long", "Short")
BUFFER_OPTIONS = ("0.5%", "0.8%", "1.0%", "Custom")


@dataclass
class TradeInputs:
    instrument: str
    asset_type: str
    currency: str
    fx_rate_to_gbp: float
    direction: str
    entry_price: float
    stop_price: float
    take_profit_price: float
    max_risk_gbp: float
    support_line: float
    buffer_percent: float
    leverage: float = 1.0
    spread_cost: float = 0.0
    overnight_fee: float = 0.0
    commission: float = 0.0
    notes: str = ""


@dataclass
class CalculationResult:
    stop_distance: float
    stop_loss_percent: float
    invalidation_stop_price: float
    units: float
    leverage: float
    exposure_local: float
    exposure_gbp: float
    required_margin_local: float
    required_margin_gbp: float
    potential_profit_gbp: float
    potential_loss_gbp: float
    net_expected_profit_gbp: float
    risk_reward: float
    valid: bool
    risk_label: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _risk_label(valid: bool, risk_reward: float, stop_loss_percent: float, max_risk: float) -> str:
    if not valid:
        return "Bad Trade"
    if risk_reward >= 3 and max_risk <= 50 and stop_loss_percent >= 0.003:
        return "Safe"
    if risk_reward >= 2.5 and max_risk <= 75:
        return "Moderate"
    return "Risky"


def calculate_trade(values: TradeInputs) -> CalculationResult:
    """Calculate trade sizing, risk, reward, and warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    if values.entry_price <= 0:
        errors.append("Entry price must be above zero.")
    if values.fx_rate_to_gbp <= 0:
        errors.append("FX rate to GBP must be above zero.")
    if values.max_risk_gbp <= 0:
        errors.append("Max GBP risk must be above zero.")
    if values.buffer_percent < 0:
        errors.append("Buffer percent cannot be negative.")
    if values.leverage <= 0:
        errors.append("Leverage must be above zero.")

    stop_distance = abs(values.entry_price - values.stop_price)
    if stop_distance <= 0:
        errors.append("Stop distance must be above zero.")

    if values.direction == "Long":
        if values.stop_price >= values.entry_price:
            errors.append("Long trades require the stop below entry.")
        if values.take_profit_price <= values.entry_price:
            errors.append("Long trades require take profit above entry.")
        invalidation_stop = values.support_line * (1 - values.buffer_percent)
    elif values.direction == "Short":
        if values.stop_price <= values.entry_price:
            errors.append("Short trades require the stop above entry.")
        if values.take_profit_price >= values.entry_price:
            errors.append("Short trades require take profit below entry.")
        invalidation_stop = values.support_line * (1 + values.buffer_percent)
    else:
        errors.append("Direction must be Long or Short.")
        invalidation_stop = values.support_line

    if errors:
        stop_loss_percent = stop_distance / values.entry_price if values.entry_price else 0
        return CalculationResult(
            stop_distance=stop_distance,
            stop_loss_percent=stop_loss_percent,
            invalidation_stop_price=invalidation_stop,
            units=0,
            leverage=max(values.leverage, 0),
            exposure_local=0,
            exposure_gbp=0,
            required_margin_local=0,
            required_margin_gbp=0,
            potential_profit_gbp=0,
            potential_loss_gbp=0,
            net_expected_profit_gbp=0,
            risk_reward=0,
            valid=False,
            risk_label="Bad Trade",
            warnings=warnings,
            errors=errors,
        )

    units = values.max_risk_gbp / (stop_distance * values.fx_rate_to_gbp)
    exposure_local = units * values.entry_price
    exposure_gbp = exposure_local * values.fx_rate_to_gbp
    required_margin_local = exposure_local / values.leverage
    required_margin_gbp = exposure_gbp / values.leverage
    potential_profit_gbp = units * abs(values.take_profit_price - values.entry_price) * values.fx_rate_to_gbp
    potential_loss_gbp = units * stop_distance * values.fx_rate_to_gbp
    total_costs = values.spread_cost + values.overnight_fee + values.commission
    net_expected_profit_gbp = potential_profit_gbp - total_costs
    risk_reward = potential_profit_gbp / values.max_risk_gbp if values.max_risk_gbp else 0
    stop_loss_percent = stop_distance / values.entry_price

    if risk_reward < 2:
        errors.append("Risk:Reward must be at least 2.")
    if values.max_risk_gbp > 50:
        warnings.append("Max GBP risk is above GBP 50.")
    if stop_loss_percent < 0.003:
        warnings.append("Stop may be too tight.")
    if values.asset_type == "CFD":
        warnings.append("Risk is based on exposure, not margin.")
    if values.asset_type == "3x ETP":
        warnings.append("Use wider stop and smaller size.")
    warnings.append("Leverage affects margin, not P/L.")

    valid = not errors
    return CalculationResult(
        stop_distance=stop_distance,
        stop_loss_percent=stop_loss_percent,
        invalidation_stop_price=invalidation_stop,
        units=units,
        leverage=values.leverage,
        exposure_local=exposure_local,
        exposure_gbp=exposure_gbp,
        required_margin_local=required_margin_local,
        required_margin_gbp=required_margin_gbp,
        potential_profit_gbp=potential_profit_gbp,
        potential_loss_gbp=potential_loss_gbp,
        net_expected_profit_gbp=net_expected_profit_gbp,
        risk_reward=risk_reward,
        valid=valid,
        risk_label=_risk_label(valid, risk_reward, stop_loss_percent, values.max_risk_gbp),
        warnings=warnings,
        errors=errors,
    )


def grade_checklist(passed: int, total: int, invalid_or_emotional: bool = False) -> str:
    """Return A/B/C/F grade from checklist state."""
    missed = total - passed
    if invalid_or_emotional:
        return "F"
    if missed <= 0:
        return "A"
    if missed == 1:
        return "B"
    if missed <= 3:
        return "C"
    return "F"
