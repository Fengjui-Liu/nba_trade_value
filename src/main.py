"""
NBA 球員交易價值評估系統 - 主程式
=================================

整合三大模組：
  1. 薪資模組 (Salary Module)
  2. 進階數據模組 (Advanced Stats Module)
  3. 適配度模組 (Fit Module)

最終輸出：Surplus Value 排名與交易價值分析
"""

import sys
import os
import pandas as pd

# 加入專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.modules.salary_module import SalaryModule
from src.modules.advanced_stats_module import AdvancedStatsModule
from src.modules.fit_module import FitModule
from src.modules.trade_value_engine import TradeValueEngine


def load_data(data_path="data/processed/players_with_salary.csv") -> pd.DataFrame:
    """載入已合併的球員數據"""
    df = pd.read_csv(data_path)
    print(f"載入 {len(df)} 名球員數據")
    print(f"欄位：{list(df.columns)}")
    return df


def run_pipeline(data_path="data/processed/players_with_salary.csv",
                 output_dir="data/processed") -> pd.DataFrame:
    """
    執行完整評估流水線

    流程：
    1. 載入數據
    2. 進階數據模組 → VALUE_SCORE_ADJ
    3. 薪資模組 → MARKET_VALUE_M, SALARY_SURPLUS_M
    4. 適配度模組 → PLAY_STYLE, FIT_VERSATILITY_SCORE
    5. 交易價值引擎 → TRADE_VALUE, SURPLUS_VALUE_M
    """
    print("=" * 70)
    print("🏀 NBA 球員交易價值評估系統")
    print("=" * 70)

    # 載入數據
    print("\n[1/5] 載入球員數據...")
    df = load_data(data_path)

    # 進階數據模組
    print("\n[2/5] 執行進階數據分析...")
    stats_module = AdvancedStatsModule(min_gp=20, min_minutes=15)
    df = stats_module.analyze(df)
    print(f"  篩選後：{len(df)} 名球員")
    print(f"  新增欄位：PER_APPROX, BPM_APPROX, VORP_APPROX, WIN_SHARES_APPROX")
    print(f"  VALUE_SCORE 範圍：{df['VALUE_SCORE'].min():.1f} ~ {df['VALUE_SCORE'].max():.1f}")

    # 薪資模組
    print("\n[3/5] 執行薪資分析...")
    salary_module = SalaryModule()
    df = salary_module.analyze(df)
    print(f"  新增欄位：CAP_PCT, SALARY_TIER, MARKET_VALUE_M, SALARY_SURPLUS_M")
    print(f"  薪資帽佔比範圍：{df['CAP_PCT'].min():.1f}% ~ {df['CAP_PCT'].max():.1f}%")

    # 適配度模組
    print("\n[4/5] 執行適配度分析...")
    fit_module = FitModule()
    df = fit_module.analyze(df)
    print(f"  新增欄位：PLAY_STYLE, OFFENSIVE_ROLE, DEFENSIVE_ROLE, POSITIONS")
    style_counts = df['PLAY_STYLE'].value_counts()
    print(f"  打法風格分類：{len(style_counts)} 種")

    # 交易價值引擎
    print("\n[5/5] 計算最終交易價值...")
    engine = TradeValueEngine()
    df = engine.calculate(df)
    print(f"  TRADE_VALUE 範圍：{df['TRADE_VALUE'].min():.1f} ~ {df['TRADE_VALUE'].max():.1f}")
    tier_counts = df['TRADE_VALUE_TIER'].value_counts()
    for tier, count in tier_counts.items():
        print(f"    {tier}: {count} 人")

    # 輸出完整報告
    print("\n" + stats_module.report(df))
    print("\n" + salary_module.report(df))
    print("\n" + fit_module.report(df))
    print("\n" + engine.report(df))

    # 儲存結果
    os.makedirs(output_dir, exist_ok=True)

    # 完整結果
    full_output = os.path.join(output_dir, "trade_value_full.csv")
    df.to_csv(full_output, index=False)
    print(f"\n完整結果已儲存至 {full_output}")

    # 精簡排名
    ranking_cols = [
        'PLAYER_NAME', 'TEAM_ABBREVIATION', 'AGE', 'GP', 'MIN',
        'PTS', 'REB', 'AST', 'STL', 'BLK',
        'PIE', 'TS_PCT', 'NET_RATING',
        'PER_APPROX', 'BPM_APPROX', 'VORP_APPROX', 'WIN_SHARES_APPROX',
        'VALUE_SCORE', 'AGE_ADJ', 'VALUE_SCORE_ADJ',
        'SALARY_M', 'CAP_PCT', 'SALARY_TIER',
        'MARKET_VALUE_M', 'SURPLUS_VALUE_M',
        'PLAY_STYLE', 'PLAY_STYLE_CN',
        'OFFENSIVE_ROLE', 'DEFENSIVE_ROLE',
        'POSITIONS', 'POSITION_FLEX', 'FIT_VERSATILITY_SCORE',
        'TRADE_VALUE', 'TRADE_VALUE_TIER',
    ]
    available_cols = [c for c in ranking_cols if c in df.columns]
    ranking_output = os.path.join(output_dir, "trade_value_ranking.csv")
    df[available_cols].to_csv(ranking_output, index=False)
    print(f"排名結果已儲存至 {ranking_output}")

    return df


def demo_trade_simulation(df: pd.DataFrame):
    """示範：交易模擬"""
    engine = TradeValueEngine()

    print("\n" + "=" * 70)
    print("📋 交易模擬示範")
    print("=" * 70)

    # 示範比較球員
    stars = ['Shai Gilgeous-Alexander', 'Luka Doncic', 'Jayson Tatum',
             'Anthony Edwards', 'Jalen Williams']
    existing = [n for n in stars if n in df['PLAYER_NAME'].values]
    if existing:
        print("\n▸ 球星比較：")
        comparison = engine.compare_players(df, existing)
        display_cols = ['PLAYER_NAME', 'AGE', 'PTS', 'TRADE_VALUE',
                        'SALARY_M', 'SURPLUS_VALUE_M', 'TRADE_VALUE_TIER']
        avail = [c for c in display_cols if c in comparison.columns]
        print(comparison[avail].to_string(index=False))

    # 示範搜尋交易目標
    print("\n▸ 搜尋交易目標（預算 $15M 以下, 25 歲以下）：")
    targets = engine.get_trade_targets(df, budget_m=15, max_age=25, top_n=10)
    if len(targets) > 0:
        target_cols = ['PLAYER_NAME', 'AGE', 'SALARY_M', 'TRADE_VALUE',
                       'SURPLUS_VALUE_M', 'PLAY_STYLE_CN']
        avail = [c for c in target_cols if c in targets.columns]
        print(targets[avail].to_string(index=False))


if __name__ == "__main__":
    df = run_pipeline()
    demo_trade_simulation(df)
