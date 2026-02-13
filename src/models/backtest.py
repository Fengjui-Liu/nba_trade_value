"""
Backtest module for evaluating trade simulation outcomes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.modules.trade_value_engine import TradeValueEngine


def _parse_players(raw: str) -> List[str]:
    if pd.isna(raw) or not str(raw).strip():
        return []
    return [p.strip() for p in str(raw).split("|") if p.strip()]


def run_backtest(
    player_data_path: str = "data/processed/trade_value_full.csv",
    trades_path: str = "data/historical_trades/canonical_trades.csv",
) -> Dict[str, object]:
    df = pd.read_csv(player_data_path)
    trades = pd.read_csv(trades_path)
    engine = TradeValueEngine()

    rows = []
    correct = 0
    scored = 0

    for _, t in trades.iterrows():
        a_gives = _parse_players(t["team_a_gives"])
        b_gives = _parse_players(t["team_b_gives"])
        result = engine.simulate_trade(df, team_a_gives=a_gives, team_b_gives=b_gives)
        value_diff = float(result["value_difference"])

        if abs(value_diff) < 5:
            predicted = "balanced"
        elif value_diff > 0:
            predicted = "team_b"
        else:
            predicted = "team_a"

        expected = str(t.get("expected_winner", "balanced"))
        is_correct = predicted == expected
        scored += 1
        if is_correct:
            correct += 1

        rows.append(
            {
                "trade_id": t["trade_id"],
                "predicted_winner": predicted,
                "expected_winner": expected,
                "salary_match": bool(result["salary_match"]),
                "value_difference": value_diff,
                "correct": is_correct,
            }
        )

    details = pd.DataFrame(rows)
    accuracy = (correct / scored) if scored else 0.0
    return {
        "num_trades": scored,
        "accuracy": round(accuracy, 4),
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run historical trade backtest")
    parser.add_argument("--player-data", type=str, default="data/processed/trade_value_full.csv")
    parser.add_argument("--trades", type=str, default="data/historical_trades/canonical_trades.csv")
    args = parser.parse_args()

    result = run_backtest(player_data_path=args.player_data, trades_path=args.trades)
    print(f"[backtest] trades={result['num_trades']} accuracy={result['accuracy']:.2%}")
    print(result["details"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

