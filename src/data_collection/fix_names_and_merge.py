"""
修正球員名稱匹配問題，合併薪資與統計資料。
"""

import argparse
import re
import unicodedata
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


def normalize_name(name: str) -> str:
    """將特殊字符與標點規範化。"""
    if pd.isna(name):
        return ""
    normalized = unicodedata.normalize("NFD", str(name))
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.lower()
    ascii_name = re.sub(r"[^a-z0-9 ]", "", ascii_name)
    ascii_name = re.sub(r"\s+", " ", ascii_name).strip()
    return ascii_name


def _normalize_team(team: str) -> str:
    if pd.isna(team):
        return ""
    return re.sub(r"[^A-Z]", "", str(team).upper())


def fix_and_merge(
    stats_path: str = f"data/raw/player_stats_{CURRENT_SEASON}.csv",
    salary_path: str = f"data/raw/player_salaries_{CURRENT_SEASON}.csv",
    output_path: str = "data/processed/players_with_salary.csv",
) -> pd.DataFrame:
    """修正名稱後重新合併。"""
    df_stats = pd.read_csv(stats_path)
    df_salary = pd.read_csv(salary_path)

    print(f"進階數據：{len(df_stats)} 名球員")
    print(f"薪資數據：{len(df_salary)} 名球員")

    df_stats = df_stats.copy()
    df_salary = df_salary.copy()
    df_stats["NAME_KEY"] = df_stats["PLAYER_NAME"].apply(normalize_name)
    df_salary["NAME_KEY"] = df_salary["PLAYER_NAME"].apply(normalize_name)
    df_stats["TEAM_KEY"] = df_stats["TEAM_ABBREVIATION"].apply(_normalize_team)
    df_salary["TEAM_KEY"] = df_salary["TEAM"].apply(_normalize_team)
    df_stats["MERGE_KEY"] = df_stats["NAME_KEY"] + "|" + df_stats["TEAM_KEY"]
    df_salary["MERGE_KEY"] = df_salary["NAME_KEY"] + "|" + df_salary["TEAM_KEY"]

    salary_cols = ["MERGE_KEY", "NAME_KEY", "SALARY", "SALARY_M"]

    # 先用 名稱+球隊 合併
    merged = df_stats.merge(
        df_salary[salary_cols].drop_duplicates(subset=["MERGE_KEY"]),
        on="MERGE_KEY",
        how="left",
        suffixes=("", "_SAL"),
    )

    # 再用唯一名稱補齊尚未匹配者
    unmatched_mask = merged["SALARY"].isna()
    salary_name_unique = df_salary.groupby("NAME_KEY").filter(lambda g: len(g) == 1)
    name_lookup = salary_name_unique.set_index("NAME_KEY")[["SALARY", "SALARY_M"]]

    if unmatched_mask.any():
        fallback = merged.loc[unmatched_mask, "NAME_KEY"].map(name_lookup["SALARY"])
        fallback_m = merged.loc[unmatched_mask, "NAME_KEY"].map(name_lookup["SALARY_M"])
        merged.loc[unmatched_mask, "SALARY"] = fallback
        merged.loc[unmatched_mask, "SALARY_M"] = fallback_m

    matched = merged["SALARY"].notna().sum()
    print(f"\n成功匹配薪資：{matched} 名球員")
    print(f"未匹配薪資：{len(merged) - matched} 名球員")

    df_final = merged[merged["SALARY"].notna()].copy()
    drop_cols = [c for c in ["NAME_KEY", "TEAM_KEY", "MERGE_KEY", "NAME_KEY_SAL"] if c in df_final.columns]
    df_final = df_final.drop(columns=drop_cols)
    df_final = df_final.sort_values("PTS", ascending=False).reset_index(drop=True)

    df_final.to_csv(output_path, index=False)
    print(f"\n合併數據已儲存至 {output_path}")
    print(f"共 {len(df_final)} 名球員")

    print("\n前 10 名球員預覽：")
    cols = ["PLAYER_NAME", "TEAM_ABBREVIATION", "PTS", "EFG_PCT", "TS_PCT", "SALARY_M"]
    available = [c for c in cols if c in df_final.columns]
    print(df_final[available].head(10).to_string(index=False))

    return df_final


def main():
    parser = argparse.ArgumentParser(description="合併球員統計與薪資資料")
    parser.add_argument("--stats", type=str, default=f"data/raw/player_stats_{CURRENT_SEASON}.csv")
    parser.add_argument("--salary", type=str, default=f"data/raw/player_salaries_{CURRENT_SEASON}.csv")
    parser.add_argument("--output", type=str, default="data/processed/players_with_salary.csv")
    args = parser.parse_args()

    fix_and_merge(stats_path=args.stats, salary_path=args.salary, output_path=args.output)


if __name__ == "__main__":
    main()
