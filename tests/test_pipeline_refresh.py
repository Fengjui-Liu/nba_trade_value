import pandas as pd

from src.pipeline import run_full_refresh


def test_run_refresh_executes_steps_in_order_and_outputs_paths(monkeypatch, tmp_path):
    call_order = []
    existing_paths = set()

    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"

    df_stub = pd.DataFrame([{"PLAYER_NAME": "A"}])
    df_salary = pd.DataFrame([{"PLAYER_NAME": "B", "SALARY": 1000000, "SALARY_M": 1.0}])

    def fake_exists(path):
        return str(path) in existing_paths

    def fake_write_csv(df, path):
        call_order.append(f"write_csv:{path.name}")
        existing_paths.add(str(path))

    def fake_get_player_advanced_stats(season):
        call_order.append("fetch_stats")
        return df_stub, df_stub, df_stub

    def fake_merge_player_data(df_advanced, df_base, df_bio):
        call_order.append("merge_stats_frames")
        return df_stub

    def fake_get_espn_salaries(year, max_pages, delay_sec):
        call_order.append("fetch_salary")
        return df_salary

    def fake_fix_and_merge(stats_path, salary_path, output_path):
        call_order.append("merge_stats_salary")
        existing_paths.add(str(output_path))
        return pd.DataFrame([{"PLAYER_NAME": "M"}])

    def fake_run_pipeline(data_path, output_dir, include_ai_analysis, target_team):
        call_order.append("run_outputs")
        existing_paths.add(str(processed_dir / "trade_value_full.csv"))
        existing_paths.add(str(processed_dir / "trade_value_ranking.csv"))
        return pd.DataFrame([{"PLAYER_NAME": "Z"}])

    monkeypatch.setattr(run_full_refresh, "_file_exists", fake_exists)
    monkeypatch.setattr(run_full_refresh, "_write_csv", fake_write_csv)
    monkeypatch.setattr(run_full_refresh.get_player_stats, "get_player_advanced_stats", fake_get_player_advanced_stats)
    monkeypatch.setattr(run_full_refresh.get_player_stats, "merge_player_data", fake_merge_player_data)
    monkeypatch.setattr(run_full_refresh.get_salary_espn, "get_espn_salaries", fake_get_espn_salaries)
    monkeypatch.setattr(run_full_refresh.fix_names_and_merge, "fix_and_merge", fake_fix_and_merge)
    monkeypatch.setattr(run_full_refresh.app_main, "run_pipeline", fake_run_pipeline)

    result = run_full_refresh.run_refresh(
        season="2025-26",
        salary_year=2026,
        force=False,
        raw_dir=str(raw_dir),
        processed_dir=str(processed_dir),
    )

    assert call_order == [
        "fetch_stats",
        "merge_stats_frames",
        "write_csv:player_stats_2025-26.csv",
        "fetch_salary",
        "write_csv:player_salaries_2025-26.csv",
        "merge_stats_salary",
        "run_outputs",
    ]
    assert result["stats"] == "refreshed"
    assert result["salary"] == "refreshed"
    assert result["merge"] == "refreshed"
    assert result["outputs"] == "refreshed"
    assert result["stats_csv"].endswith("player_stats_2025-26.csv")
    assert result["salary_csv"].endswith("player_salaries_2025-26.csv")
    assert result["merged_csv"].endswith("players_with_salary.csv")
    assert result["trade_value_full_csv"].endswith("trade_value_full.csv")
    assert result["trade_value_ranking_csv"].endswith("trade_value_ranking.csv")


def test_run_refresh_skips_all_steps_when_cached(monkeypatch, tmp_path):
    call_order = []

    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    paths = run_full_refresh.build_paths("2025-26", raw_dir, processed_dir)
    existing_paths = {
        str(paths.stats_csv),
        str(paths.salary_csv),
        str(paths.merged_csv),
        str(paths.trade_value_full_csv),
        str(paths.trade_value_ranking_csv),
    }

    monkeypatch.setattr(run_full_refresh, "_file_exists", lambda path: str(path) in existing_paths)
    monkeypatch.setattr(run_full_refresh.get_player_stats, "get_player_advanced_stats", lambda season: call_order.append("fetch_stats"))
    monkeypatch.setattr(run_full_refresh.get_salary_espn, "get_espn_salaries", lambda year, max_pages, delay_sec: call_order.append("fetch_salary"))
    monkeypatch.setattr(run_full_refresh.fix_names_and_merge, "fix_and_merge", lambda stats_path, salary_path, output_path: call_order.append("merge"))
    monkeypatch.setattr(run_full_refresh.app_main, "run_pipeline", lambda data_path, output_dir, include_ai_analysis, target_team: call_order.append("outputs"))

    result = run_full_refresh.run_refresh(
        season="2025-26",
        salary_year=2026,
        force=False,
        raw_dir=str(raw_dir),
        processed_dir=str(processed_dir),
    )

    assert call_order == []
    assert result["stats"] == "cached"
    assert result["salary"] == "cached"
    assert result["merge"] == "cached"
    assert result["outputs"] == "cached"

