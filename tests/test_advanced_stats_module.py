import pandas as pd

from src.modules.advanced_stats_module import AdvancedStatsModule


def test_advanced_stats_analyze_filters_and_generates_key_metrics():
    df = pd.DataFrame(
        [
            {
                "PLAYER_NAME": "Star",
                "GP": 70,
                "MIN": 35,
                "PTS": 29,
                "REB": 8,
                "AST": 7,
                "STL": 1.4,
                "BLK": 0.8,
                "FG_PCT": 0.51,
                "FG3_PCT": 0.39,
                "FT_PCT": 0.88,
                "TS_PCT": 0.62,
                "USG_PCT": 0.31,
                "PIE": 0.19,
                "NET_RATING": 9.5,
                "AGE": 26,
            },
            {
                "PLAYER_NAME": "Starter",
                "GP": 55,
                "MIN": 28,
                "PTS": 16,
                "REB": 5,
                "AST": 4,
                "STL": 0.9,
                "BLK": 0.5,
                "FG_PCT": 0.47,
                "FG3_PCT": 0.35,
                "FT_PCT": 0.80,
                "TS_PCT": 0.58,
                "USG_PCT": 0.22,
                "PIE": 0.12,
                "NET_RATING": 1.2,
                "AGE": 29,
            },
            {
                "PLAYER_NAME": "LowMinutes",
                "GP": 10,
                "MIN": 11,
                "PTS": 7,
                "REB": 2,
                "AST": 1,
                "STL": 0.3,
                "BLK": 0.1,
                "FG_PCT": 0.44,
                "FG3_PCT": 0.33,
                "FT_PCT": 0.75,
                "TS_PCT": 0.53,
                "USG_PCT": 0.18,
                "PIE": 0.07,
                "NET_RATING": -3.0,
                "AGE": 22,
            },
        ]
    )

    result = AdvancedStatsModule(min_gp=20, min_minutes=15).analyze(df)

    assert len(result) == 2
    assert set(result["PLAYER_NAME"]) == {"Star", "Starter"}
    for col in [
        "PER_APPROX",
        "BPM_APPROX",
        "VORP_APPROX",
        "WIN_SHARES_APPROX",
        "VALUE_SCORE",
        "VALUE_SCORE_ADJ",
    ]:
        assert col in result.columns
        assert result[col].notna().all()

