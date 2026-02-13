import pandas as pd

from src.modules.fit_module import FitModule


def test_fit_module_analyze_classifies_playstyle_and_positions():
    df = pd.DataFrame(
        [
            {
                "PLAYER_NAME": "FloorGeneral",
                "PTS": 18,
                "AST": 10,
                "REB": 4,
                "STL": 1.2,
                "BLK": 0.2,
                "FG3_PCT": 0.37,
                "FG_PCT": 0.47,
                "USG_PCT": 0.25,
                "PLAYER_HEIGHT": "6-3",
                "TS_PCT": 0.59,
                "DEF_RATING": 109,
            },
            {
                "PLAYER_NAME": "RimProtector",
                "PTS": 13,
                "AST": 2,
                "REB": 11,
                "STL": 0.6,
                "BLK": 2.3,
                "FG3_PCT": 0.18,
                "FG_PCT": 0.58,
                "USG_PCT": 0.18,
                "PLAYER_HEIGHT": "7-0",
                "TS_PCT": 0.61,
                "DEF_RATING": 104,
            },
        ]
    )

    result = FitModule().analyze(df)

    floor_general = result[result["PLAYER_NAME"] == "FloorGeneral"].iloc[0]
    rim_protector = result[result["PLAYER_NAME"] == "RimProtector"].iloc[0]

    assert floor_general["PLAY_STYLE"] == "FLOOR_GENERAL"
    assert floor_general["POSITIONS"] == "PG"

    assert rim_protector["PLAY_STYLE"] == "RIM_PROTECTOR"
    assert rim_protector["DEFENSIVE_ROLE"] == "RIM_PROTECTOR"
    assert rim_protector["POSITIONS"] == "C/PF"
