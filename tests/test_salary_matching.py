import pandas as pd

from src.modules.contract_module import ContractModule
from src.modules.trade_value_engine import TradeValueEngine


def test_salary_match_tiered_rule_basic_ranges():
    # <= 7.5M bucket
    assert ContractModule.is_salary_match(5.0, 10.25, rule="tiered_2023")
    assert not ContractModule.is_salary_match(5.0, 10.30, rule="tiered_2023")

    # 7.5M ~ 29M bucket
    assert ContractModule.is_salary_match(20.0, 27.5, rule="tiered_2023")
    assert not ContractModule.is_salary_match(20.0, 27.6, rule="tiered_2023")

    # > 29M bucket
    assert ContractModule.is_salary_match(40.0, 50.25, rule="tiered_2023")
    assert not ContractModule.is_salary_match(40.0, 50.30, rule="tiered_2023")


def test_trade_engine_uses_salary_match_rule():
    df = pd.DataFrame(
        [
            {
                "PLAYER_NAME": "A1",
                "AGE": 25,
                "SALARY_M": 20.0,
                "TRADE_VALUE": 50.0,
                "SURPLUS_VALUE_M": 0.0,
            },
            {
                "PLAYER_NAME": "B1",
                "AGE": 25,
                "SALARY_M": 27.5,
                "TRADE_VALUE": 50.0,
                "SURPLUS_VALUE_M": 0.0,
            },
        ]
    )

    engine = TradeValueEngine()
    result = engine.simulate_trade(df, team_a_gives=["A1"], team_b_gives=["B1"])
    assert result["salary_match"] is True

