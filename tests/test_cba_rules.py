import pytest

from src.modules.cba_rules import build_context, evaluate_side, evaluate_trade, infer_tax_state, max_incoming_salary
from src.modules.rule_types import TaxState, TradeSideInput


@pytest.mark.parametrize(
    "payroll_m,expected",
    [
        (150.0, TaxState.BELOW_TAX),
        (187.0, TaxState.TAX),
        (194.0, TaxState.APRON_1),
        (206.0, TaxState.APRON_2),
    ],
)
def test_infer_tax_state_table(payroll_m, expected):
    assert infer_tax_state(payroll_m) == expected


@pytest.mark.parametrize(
    "tax_state,outgoing_m,expected_max",
    [
        (TaxState.BELOW_TAX, 5.0, 10.25),
        (TaxState.BELOW_TAX, 20.0, 27.5),
        (TaxState.TAX, 20.0, 25.25),
        (TaxState.APRON_1, 40.0, 50.25),
        (TaxState.APRON_2, 40.0, 44.0),
    ],
)
def test_max_incoming_salary_table(tax_state, outgoing_m, expected_max):
    assert max_incoming_salary(outgoing_m, tax_state) == expected_max


def test_second_apron_cannot_aggregate_multiple_outgoing():
    context = build_context("LAL", 210.0)
    side = TradeSideInput(
        team_code="LAL",
        outgoing_salary_m=30.0,
        incoming_salary_m=28.0,
        outgoing_players=2,
        incoming_players=1,
    )
    decision = evaluate_side(side, context)
    assert not decision.ok
    assert "second_apron_cannot_aggregate_multiple_outgoing" in decision.reasons


def test_second_apron_cannot_take_more_salary():
    context = build_context("PHX", 208.0)
    side = TradeSideInput(
        team_code="PHX",
        outgoing_salary_m=20.0,
        incoming_salary_m=21.0,
        outgoing_players=1,
        incoming_players=1,
    )
    decision = evaluate_side(side, context)
    assert not decision.ok
    assert "second_apron_cannot_take_more_salary" in decision.reasons


def test_trade_evaluation_bilateral_salary_match():
    side_a = TradeSideInput("OKC", outgoing_salary_m=20.0, incoming_salary_m=19.0, outgoing_players=1)
    side_b = TradeSideInput("LAL", outgoing_salary_m=19.0, incoming_salary_m=20.0, outgoing_players=1)
    result = evaluate_trade(
        side_a=side_a,
        side_b=side_b,
        context_a=build_context("OKC", 175.0),
        context_b=build_context("LAL", 170.0),
    )
    assert result["salary_match"] is True
    assert result["team_a"].ok is True
    assert result["team_b"].ok is True

