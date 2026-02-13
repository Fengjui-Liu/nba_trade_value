from src.dashboard.dashboard_logic import (
    build_explain_bullets,
    build_metric_pills,
    build_trade_signature,
)


def test_trade_signature_is_order_invariant_within_sides():
    s1 = build_trade_signature(["B", "A"], ["Y", "X"])
    s2 = build_trade_signature(["A", "B"], ["X", "Y"])
    assert s1 == s2


def test_metric_pills_expected_fields():
    m = build_metric_pills({"salary_match": True, "value_difference": 3.5, "salary_diff_m": 1.2})
    assert m["salary_match_status"] == "PASS"
    assert m["trade_value_delta"] == "+3.5"
    assert m["cap_impact_m"] == "1.20M"


def test_explain_bullets_include_salary_and_balance():
    bullets = build_explain_bullets({"salary_match": False, "value_difference": 0.2})
    assert any("Salary matching failed" in b for b in bullets)
    assert any("balanced" in b.lower() for b in bullets)
