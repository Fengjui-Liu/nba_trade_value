import pandas as pd

from src.modules.contract_module import ContractModule


def test_contract_module_analyze_generates_contract_fields():
    df = pd.DataFrame(
        [
            {"PLAYER_NAME": "MaxStar", "AGE": 31, "SALARY_M": 50.0},
            {"PLAYER_NAME": "YoungProspect", "AGE": 22, "SALARY_M": 4.0},
        ]
    )

    result = ContractModule().analyze(df)

    expected_cols = [
        "CONTRACT_TYPE",
        "CONTRACT_TYPE_CN",
        "YEARS_REMAINING",
        "TRADE_RESTRICTIONS",
        "CONTRACT_FLEXIBILITY",
        "SALARY_MATCH_MAX",
    ]
    for col in expected_cols:
        assert col in result.columns

    max_star = result[result["PLAYER_NAME"] == "MaxStar"].iloc[0]
    prospect = result[result["PLAYER_NAME"] == "YoungProspect"].iloc[0]

    assert max_star["CONTRACT_TYPE"] == "MAX"
    assert max_star["YEARS_REMAINING"] == 3
    assert max_star["SALARY_MATCH_MAX"] == 62.75

    assert prospect["CONTRACT_TYPE"] == "ROOKIE_SCALE"
    assert prospect["YEARS_REMAINING"] == 1
    assert prospect["SALARY_MATCH_MAX"] == 8.25


def test_get_draft_pick_value_applies_protection_and_time_discount():
    base = ContractModule.get_draft_pick_value(5)
    protected = ContractModule.get_draft_pick_value(5, protections="TOP_5")
    future = ContractModule.get_draft_pick_value(5, years_out=2)

    assert base == 33.0
    assert protected == 24.8
    assert future == 26.7
