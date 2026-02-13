"""
檢查球員名稱匹配落差。
"""

import argparse
import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.config import CURRENT_SEASON
except ImportError:
    CURRENT_SEASON = "2025-26"

from src.data_collection.fix_names_and_merge import normalize_name


def check_missing_players(
    stats_path: str = f"data/raw/player_stats_{CURRENT_SEASON}.csv",
    salary_path: str = f"data/raw/player_salaries_{CURRENT_SEASON}.csv",
):
    """找出未匹配的球員。"""
    df_stats = pd.read_csv(stats_path)
    df_salary = pd.read_csv(salary_path)

    stats_keys = set(df_stats["PLAYER_NAME"].apply(normalize_name))
    salary_keys = set(df_salary["PLAYER_NAME"].apply(normalize_name))

    in_salary_not_stats = salary_keys - stats_keys
    in_stats_not_salary = stats_keys - salary_keys

    print("=" * 60)
    print("薪資表有，但數據表沒匹配到的前 20 名高薪球員：")
    print("=" * 60)
    top_salary = df_salary[df_salary["PLAYER_NAME"].apply(normalize_name).isin(in_salary_not_stats)].head(20)
    if top_salary.empty:
        print("（無）")
    else:
        print(top_salary[["PLAYER_NAME", "SALARY_M"]].to_string(index=False))

    print("\n" + "=" * 60)
    print("數據表有，但薪資表沒匹配到的前 20 名得分球員：")
    print("=" * 60)
    top_stats = df_stats[df_stats["PLAYER_NAME"].apply(normalize_name).isin(in_stats_not_salary)]
    top_stats = top_stats.sort_values("PTS", ascending=False).head(20)
    if top_stats.empty:
        print("（無）")
    else:
        print(top_stats[["PLAYER_NAME", "PTS"]].to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="檢查薪資與統計名單匹配落差")
    parser.add_argument("--stats", type=str, default=f"data/raw/player_stats_{CURRENT_SEASON}.csv")
    parser.add_argument("--salary", type=str, default=f"data/raw/player_salaries_{CURRENT_SEASON}.csv")
    args = parser.parse_args()
    check_missing_players(args.stats, args.salary)


if __name__ == "__main__":
    main()
