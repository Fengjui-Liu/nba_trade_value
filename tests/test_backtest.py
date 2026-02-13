from pathlib import Path

from src.models.backtest import run_backtest


def test_run_backtest_returns_metrics_and_details():
    player_data_path = Path("tests/fixtures/sample_players_with_salary.csv")
    trades_path = Path("data/historical_trades/canonical_trades.csv")

    result = run_backtest(player_data_path=str(player_data_path), trades_path=str(trades_path))
    assert result["num_trades"] == 3
    assert 0.0 <= result["accuracy"] <= 1.0
    assert len(result["details"]) == 3
    assert {"trade_id", "predicted_winner", "expected_winner", "salary_match", "correct"}.issubset(result["details"].columns)

