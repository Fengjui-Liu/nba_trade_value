"""
Non-visual dashboard logic helpers.
"""

from __future__ import annotations

from typing import Dict, List


def build_trade_signature(team_a_gives: List[str], team_b_gives: List[str]) -> str:
    a = "|".join(sorted(team_a_gives or []))
    b = "|".join(sorted(team_b_gives or []))
    return f"A:{a}__B:{b}"


def build_metric_pills(trade_result: Dict) -> Dict[str, str]:
    salary_ok = bool(trade_result.get("salary_match", False))
    value_diff = float(trade_result.get("value_difference", 0.0) or 0.0)
    salary_diff = float(trade_result.get("salary_diff_m", 0.0) or 0.0)

    fit_score = max(0.0, 100.0 - abs(value_diff) * 4.0)

    return {
        "trade_value_delta": f"{value_diff:+.1f}",
        "salary_match_status": "PASS" if salary_ok else "FAIL",
        "cap_impact_m": f"{salary_diff:.2f}M",
        "fit_score": f"{fit_score:.1f}",
    }


def build_explain_bullets(trade_result: Dict) -> List[str]:
    bullets = []
    bullets.append("Salary matching passed under selected rule set." if trade_result.get("salary_match") else "Salary matching failed under selected rule set.")
    value_diff = float(trade_result.get("value_difference", 0.0) or 0.0)
    if abs(value_diff) < 5:
        bullets.append("Value exchange is broadly balanced.")
    elif value_diff > 0:
        bullets.append("Team A sends higher aggregate trade value.")
    else:
        bullets.append("Team B sends higher aggregate trade value.")

    if "cba" in trade_result:
        a_reasons = trade_result["cba"]["team_a"].get("reasons", [])
        b_reasons = trade_result["cba"]["team_b"].get("reasons", [])
        if a_reasons:
            bullets.append(f"Team A constraints: {', '.join(a_reasons)}")
        if b_reasons:
            bullets.append(f"Team B constraints: {', '.join(b_reasons)}")

    return bullets
