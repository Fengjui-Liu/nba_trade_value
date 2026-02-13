import pandas as pd

from src.modules.salary_module import SalaryModule


def test_salary_module_analyze_adds_expected_columns_and_values():
    df = pd.DataFrame(
        [
            {"PLAYER_NAME": "Prime", "SALARY_M": 30.0, "VALUE_SCORE": 70.0, "AGE": 28},
            {"PLAYER_NAME": "Veteran", "SALARY_M": 5.0, "VALUE_SCORE": 90.0, "AGE": 35},
        ]
    )

    result = SalaryModule().analyze(df)

    for col in ["CAP_PCT", "SALARY_TIER", "MARKET_VALUE_M", "SALARY_SURPLUS_M", "CONTRACT_VALUE_RATIO"]:
        assert col in result.columns

    prime = result[result["PLAYER_NAME"] == "Prime"].iloc[0]
    veteran = result[result["PLAYER_NAME"] == "Veteran"].iloc[0]

    assert prime["SALARY_TIER"] == "MAX"
    assert prime["MARKET_VALUE_M"] == 20.0
    assert prime["SALARY_SURPLUS_M"] == -10.0
    assert prime["CONTRACT_VALUE_RATIO"] == 0.67

    # Score 90 maps to 40M, then 35+ age discount (x0.70).
    assert veteran["MARKET_VALUE_M"] == 28.0
    assert veteran["SALARY_SURPLUS_M"] == 23.0

