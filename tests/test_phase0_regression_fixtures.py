import json
from pathlib import Path

import pandas as pd

from src.modules.trade_value_engine import TradeValueEngine


FIXTURES_DIR = Path(__file__).parent / "fixtures"
PLAYERS_FIXTURE = FIXTURES_DIR / "sample_players_with_salary.csv"
TRADES_FIXTURE = FIXTURES_DIR / "sample_trade_packages.json"


def test_golden_players_fixture_invariants():
    df = pd.read_csv(PLAYERS_FIXTURE)

    required_columns = {
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "AGE",
        "SALARY",
        "SALARY_M",
        "TRADE_VALUE",
        "SURPLUS_VALUE_M",
    }
    assert required_columns.issubset(df.columns)
    assert not df.empty

    assert df["PLAYER_NAME"].isna().sum() == 0
    assert df["TEAM_ABBREVIATION"].isna().sum() == 0
    assert (df["SALARY_M"] >= 0).all()
    assert (df["AGE"].between(18, 45)).all()
    assert df["TEAM_ABBREVIATION"].str.fullmatch(r"[A-Z]{3}").all()

    expected_salary_m = (df["SALARY"] / 1_000_000).round(2)
    assert expected_salary_m.equals(df["SALARY_M"].round(2))


def test_golden_trade_fixture_schema_and_unique_ids():
    payload = json.loads(TRADES_FIXTURE.read_text(encoding="utf-8"))
    scenarios = payload["scenarios"]

    assert isinstance(scenarios, list)
    assert len(scenarios) >= 1

    ids = [s["id"] for s in scenarios]
    assert len(ids) == len(set(ids))

    for scenario in scenarios:
        assert scenario["team_a_gives"]
        assert scenario["team_b_gives"]
        assert "salary_match" in scenario["expected"]
        assert isinstance(scenario["expected"]["salary_match"], bool)

        a_set = set(scenario["team_a_gives"])
        b_set = set(scenario["team_b_gives"])
        assert a_set.isdisjoint(b_set)


def test_golden_trade_scenarios_match_expected_salary_result():
    df = pd.read_csv(PLAYERS_FIXTURE)
    payload = json.loads(TRADES_FIXTURE.read_text(encoding="utf-8"))
    engine = TradeValueEngine()

    known_players = set(df["PLAYER_NAME"].tolist())
    for scenario in payload["scenarios"]:
        assert set(scenario["team_a_gives"]).issubset(known_players)
        assert set(scenario["team_b_gives"]).issubset(known_players)

        result = engine.simulate_trade(
            df,
            team_a_gives=scenario["team_a_gives"],
            team_b_gives=scenario["team_b_gives"],
        )
        assert result["salary_match"] is scenario["expected"]["salary_match"]

