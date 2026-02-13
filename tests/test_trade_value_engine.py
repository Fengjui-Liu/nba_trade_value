import pandas as pd

from src.modules.trade_value_engine import TradeValueEngine


def test_trade_value_engine_calculate_outputs_ranked_trade_values():
    df = pd.DataFrame(
        [
            {
                "PLAYER_NAME": "A",
                "VALUE_SCORE_ADJ": 90.0,
                "CONTRACT_VALUE_RATIO": 1.8,
                "FIT_VERSATILITY_SCORE": 80.0,
                "MARKET_VALUE_M": 40.0,
                "SALARY_M": 30.0,
            },
            {
                "PLAYER_NAME": "B",
                "VALUE_SCORE_ADJ": 60.0,
                "CONTRACT_VALUE_RATIO": 1.0,
                "FIT_VERSATILITY_SCORE": 55.0,
                "MARKET_VALUE_M": 18.0,
                "SALARY_M": 20.0,
            },
        ]
    )

    result = TradeValueEngine().calculate(df)

    assert list(result["PLAYER_NAME"]) == ["A", "B"]
    assert "TRADE_VALUE" in result.columns
    assert "TRADE_VALUE_TIER" in result.columns
    assert "SURPLUS_VALUE_M" in result.columns
    assert result.iloc[0]["TRADE_VALUE"] > result.iloc[1]["TRADE_VALUE"]
    assert result.iloc[0]["SURPLUS_VALUE_M"] == 10.0
    assert result.iloc[1]["SURPLUS_VALUE_M"] == -2.0

