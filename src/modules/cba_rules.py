"""
CBA salary matching rule engine (v1).

Scope:
- Tax/apron-aware salary matching bounds
- Basic second apron aggregation constraints
"""

from __future__ import annotations

from typing import Dict, Optional

try:
    from src.config import FIRST_APRON_M, LUXURY_TAX_M, SECOND_APRON_M
except ImportError:
    from config import FIRST_APRON_M, LUXURY_TAX_M, SECOND_APRON_M

try:
    from .rule_types import RULE_VERSION, RuleDecision, TaxState, TeamCBAContext, TradeSideInput
except ImportError:
    from src.modules.rule_types import RULE_VERSION, RuleDecision, TaxState, TeamCBAContext, TradeSideInput


def infer_tax_state(payroll_m: float) -> TaxState:
    payroll = float(payroll_m or 0.0)
    if payroll >= SECOND_APRON_M:
        return TaxState.APRON_2
    if payroll >= FIRST_APRON_M:
        return TaxState.APRON_1
    if payroll >= LUXURY_TAX_M:
        return TaxState.TAX
    return TaxState.BELOW_TAX


def build_context(team_code: str, payroll_m: float) -> TeamCBAContext:
    return TeamCBAContext(
        team_code=team_code,
        payroll_m=round(float(payroll_m or 0.0), 2),
        tax_state=infer_tax_state(payroll_m),
    )


def _tiered_2023_max_incoming(outgoing_m: float) -> float:
    outgoing = max(0.0, float(outgoing_m or 0.0))
    if outgoing <= 7.5:
        return round(outgoing * 2.0 + 0.25, 2)
    if outgoing <= 29.0:
        return round(outgoing + 7.5, 2)
    return round(outgoing * 1.25 + 0.25, 2)


def _strict_125_max_incoming(outgoing_m: float) -> float:
    outgoing = max(0.0, float(outgoing_m or 0.0))
    return round(outgoing * 1.25 + 0.25, 2)


def _apron2_max_incoming(outgoing_m: float) -> float:
    # v1 approximation: highly restrictive at second apron.
    outgoing = max(0.0, float(outgoing_m or 0.0))
    return round(outgoing * 1.10, 2)


def max_incoming_salary(outgoing_m: float, tax_state: TaxState) -> float:
    if tax_state == TaxState.BELOW_TAX:
        return _tiered_2023_max_incoming(outgoing_m)
    if tax_state in (TaxState.TAX, TaxState.APRON_1):
        return min(_tiered_2023_max_incoming(outgoing_m), _strict_125_max_incoming(outgoing_m))
    return _apron2_max_incoming(outgoing_m)


def evaluate_side(side: TradeSideInput, context: TeamCBAContext) -> RuleDecision:
    outgoing = max(0.0, float(side.outgoing_salary_m or 0.0))
    incoming = max(0.0, float(side.incoming_salary_m or 0.0))
    reasons = []
    warnings = []

    if outgoing == 0:
        ok = incoming == 0
        if not ok:
            reasons.append("cannot_take_salary_without_outgoing")
        return RuleDecision(ok=ok, max_incoming_m=0.0, reasons=reasons, warnings=warnings)

    max_incoming = max_incoming_salary(outgoing, context.tax_state)

    # v1 aggregation constraint approximation
    if context.tax_state == TaxState.APRON_2 and side.outgoing_players > 1:
        reasons.append("second_apron_cannot_aggregate_multiple_outgoing")

    if context.tax_state == TaxState.APRON_2 and incoming > outgoing:
        reasons.append("second_apron_cannot_take_more_salary")

    if incoming > max_incoming:
        reasons.append("incoming_exceeds_max_incoming")

    if context.tax_state == TaxState.APRON_1:
        warnings.append("first_apron_rules_are_approximate_v1")
    if context.tax_state == TaxState.APRON_2:
        warnings.append("second_apron_rules_are_approximate_v1")

    return RuleDecision(
        ok=len(reasons) == 0,
        max_incoming_m=round(max_incoming, 2),
        reasons=reasons,
        warnings=warnings,
    )


def evaluate_trade(
    side_a: TradeSideInput,
    side_b: TradeSideInput,
    context_a: TeamCBAContext,
    context_b: TeamCBAContext,
) -> Dict[str, object]:
    decision_a = evaluate_side(side_a, context_a)
    decision_b = evaluate_side(side_b, context_b)
    return {
        "rule_version": RULE_VERSION,
        "team_a": decision_a,
        "team_b": decision_b,
        "salary_match": decision_a.ok and decision_b.ok,
    }


def legacy_is_salary_match(
    outgoing_m: float,
    incoming_m: float,
    rule: str = "tiered_2023",
    context: Optional[TeamCBAContext] = None,
    outgoing_players: int = 1,
) -> bool:
    outgoing = max(0.0, float(outgoing_m or 0.0))
    incoming = max(0.0, float(incoming_m or 0.0))
    if rule == "simple_125":
        return incoming <= round(outgoing * 1.25 + 0.1, 2) if outgoing > 0 else incoming == 0
    if rule == "tiered_2023":
        return incoming <= _tiered_2023_max_incoming(outgoing) if outgoing > 0 else incoming == 0

    # cba_v1 path
    cba_context = context or build_context(team_code="UNK", payroll_m=0.0)
    decision = evaluate_side(
        TradeSideInput(
            team_code=cba_context.team_code,
            outgoing_salary_m=outgoing,
            incoming_salary_m=incoming,
            outgoing_players=outgoing_players,
        ),
        cba_context,
    )
    return decision.ok

