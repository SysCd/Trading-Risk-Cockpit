"""Validation helpers."""

from __future__ import annotations


def status_from_counts(red_count: int, yellow_count: int, invalid: bool) -> tuple[str, str]:
    if invalid:
        return "Invalid", "bad"
    if red_count >= 2:
        return "Risky", "bad"
    if red_count == 1:
        return "Borderline", "bad"
    if yellow_count:
        return "Acceptable", "ok"
    return "Ideal", "good"
