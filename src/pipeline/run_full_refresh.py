"""
One-command data refresh pipeline.

Steps:
1. Fetch player stats
2. Fetch salary data
3. Merge stats + salary
4. Run model outputs
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import pandas as pd

from src import main as app_main
from src.config import CURRENT_SEASON, SEASON_END_YEAR
from src.data_collection import fix_names_and_merge, get_player_stats, get_salary_espn


@dataclass
class RefreshPaths:
    stats_csv: Path
    salary_csv: Path
    merged_csv: Path
    trade_value_full_csv: Path
    trade_value_ranking_csv: Path


def _log(msg: str) -> None:
    print(f"[refresh] {msg}")


def _file_exists(path: Path) -> bool:
    return path.exists()


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def build_paths(season: str, raw_dir: Path, processed_dir: Path) -> RefreshPaths:
    return RefreshPaths(
        stats_csv=raw_dir / f"player_stats_{season}.csv",
        salary_csv=raw_dir / f"player_salaries_{season}.csv",
        merged_csv=processed_dir / "players_with_salary.csv",
        trade_value_full_csv=processed_dir / "trade_value_full.csv",
        trade_value_ranking_csv=processed_dir / "trade_value_ranking.csv",
    )


def run_refresh(
    season: str = CURRENT_SEASON,
    salary_year: int = SEASON_END_YEAR,
    max_pages: int = 30,
    delay_sec: float = 0.8,
    force: bool = False,
    raw_dir: str = "data/raw",
    processed_dir: str = "data/processed",
) -> Dict[str, str]:
    """
    Run the full data-refresh pipeline with idempotent caching.

    Returns a dict with per-step status and key artifact paths.
    """
    raw_path = Path(raw_dir)
    processed_path = Path(processed_dir)
    paths = build_paths(season=season, raw_dir=raw_path, processed_dir=processed_path)

    status: Dict[str, str] = {}

    _log("starting full refresh")
    _log(f"season={season} salary_year={salary_year} force={force}")

    # Step 1: fetch stats
    if _file_exists(paths.stats_csv) and not force:
        _log(f"step 1/4 stats cached: {paths.stats_csv}")
        status["stats"] = "cached"
    else:
        _log("step 1/4 fetching stats")
        df_advanced, df_base, df_bio = get_player_stats.get_player_advanced_stats(season=season)
        df_stats = get_player_stats.merge_player_data(df_advanced, df_base, df_bio)
        _write_csv(df_stats, paths.stats_csv)
        _log(f"stats written: {paths.stats_csv}")
        status["stats"] = "refreshed"

    # Step 2: fetch salary
    if _file_exists(paths.salary_csv) and not force:
        _log(f"step 2/4 salary cached: {paths.salary_csv}")
        status["salary"] = "cached"
    else:
        _log("step 2/4 fetching salary")
        df_salary = get_salary_espn.get_espn_salaries(
            year=salary_year,
            max_pages=max_pages,
            delay_sec=delay_sec,
        )
        if df_salary.empty:
            raise RuntimeError("salary fetch returned empty dataset")
        _write_csv(df_salary, paths.salary_csv)
        _log(f"salary written: {paths.salary_csv}")
        status["salary"] = "refreshed"

    # Step 3: merge
    if _file_exists(paths.merged_csv) and not force:
        _log(f"step 3/4 merged cached: {paths.merged_csv}")
        status["merge"] = "cached"
    else:
        _log("step 3/4 merging stats + salary")
        fix_names_and_merge.fix_and_merge(
            stats_path=str(paths.stats_csv),
            salary_path=str(paths.salary_csv),
            output_path=str(paths.merged_csv),
        )
        _log(f"merged written: {paths.merged_csv}")
        status["merge"] = "refreshed"

    # Step 4: run outputs
    outputs_exist = _file_exists(paths.trade_value_full_csv) and _file_exists(paths.trade_value_ranking_csv)
    if outputs_exist and not force:
        _log(f"step 4/4 outputs cached: {paths.trade_value_full_csv}, {paths.trade_value_ranking_csv}")
        status["outputs"] = "cached"
    else:
        _log("step 4/4 running output pipeline")
        app_main.run_pipeline(
            data_path=str(paths.merged_csv),
            output_dir=str(processed_path),
            include_ai_analysis=False,
            target_team=None,
        )
        _log("output pipeline completed")
        status["outputs"] = "refreshed"

    status["stats_csv"] = str(paths.stats_csv)
    status["salary_csv"] = str(paths.salary_csv)
    status["merged_csv"] = str(paths.merged_csv)
    status["trade_value_full_csv"] = str(paths.trade_value_full_csv)
    status["trade_value_ranking_csv"] = str(paths.trade_value_ranking_csv)

    _log("refresh finished")
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full data refresh pipeline")
    parser.add_argument("--season", type=str, default=CURRENT_SEASON, help="Season string, e.g. 2025-26")
    parser.add_argument("--year", type=int, default=SEASON_END_YEAR, help="Salary page year, e.g. 2026")
    parser.add_argument("--max-pages", type=int, default=30, help="Max salary pages to fetch")
    parser.add_argument("--delay", type=float, default=0.8, help="Delay between salary requests (sec)")
    parser.add_argument("--force", action="store_true", help="Force refresh even if artifacts already exist")
    parser.add_argument("--raw-dir", type=str, default="data/raw", help="Raw data directory")
    parser.add_argument("--processed-dir", type=str, default="data/processed", help="Processed data directory")
    args = parser.parse_args()

    try:
        run_refresh(
            season=args.season,
            salary_year=args.year,
            max_pages=args.max_pages,
            delay_sec=args.delay,
            force=args.force,
            raw_dir=args.raw_dir,
            processed_dir=args.processed_dir,
        )
        return 0
    except Exception as exc:
        _log(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

