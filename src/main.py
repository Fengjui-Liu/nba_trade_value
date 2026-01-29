"""
NBA 球員交易價值評估系統 - 主程式 v2.0
======================================

整合五大模組：
  1. 薪資模組 (Salary Module)
  2. 進階數據模組 (Advanced Stats Module)
  3. 適配度模組 (Fit Module)
  4. 合約模組 (Contract Module) - 新增
  5. AI 分析模組 (AI Analysis Module) - 新增

最終輸出：Surplus Value 排名與交易價值分析
"""

import sys
import os
import pandas as pd
import argparse

# 加入專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.modules.salary_module import SalaryModule
from src.modules.advanced_stats_module import AdvancedStatsModule
from src.modules.fit_module import FitModule
from src.modules.trade_value_engine import TradeValueEngine
from src.modules.contract_module import ContractModule
from src.modules.ai_analysis_module import AIAnalysisModule


def load_data(data_path="data/processed/players_with_salary.csv") -> pd.DataFrame:
    """載入已合併的球員數據"""
    df = pd.read_csv(data_path)
    print(f"載入 {len(df)} 名球員數據")
    print(f"欄位：{list(df.columns)}")
    return df


def run_pipeline(data_path="data/processed/players_with_salary.csv",
                 output_dir="data/processed",
                 include_ai_analysis=False,
                 target_team=None) -> pd.DataFrame:
    """
    執行完整評估流水線

    流程：
    1. 載入數據
    2. 進階數據模組 → VALUE_SCORE_ADJ
    3. 薪資模組 → MARKET_VALUE_M, SALARY_SURPLUS_M
    4. 適配度模組 → PLAY_STYLE, FIT_VERSATILITY_SCORE
    5. 交易價值引擎 → TRADE_VALUE, SURPLUS_VALUE_M
    6. 合約模組 → CONTRACT_TYPE, YEARS_REMAINING, CONTRACT_FLEXIBILITY
    7. AI 分析 (可選) → 球隊分析報告
    """
    print("=" * 70)
    print("🏀 NBA 球員交易價值評估系統 v2.0")
    print("=" * 70)

    # 載入數據
    print("\n[1/7] 載入球員數據...")
    df = load_data(data_path)

    # 進階數據模組
    print("\n[2/7] 執行進階數據分析...")
    stats_module = AdvancedStatsModule(min_gp=20, min_minutes=15)
    df = stats_module.analyze(df)
    print(f"  篩選後：{len(df)} 名球員")
    print(f"  新增欄位：PER_APPROX, BPM_APPROX, VORP_APPROX, WIN_SHARES_APPROX")
    print(f"  VALUE_SCORE 範圍：{df['VALUE_SCORE'].min():.1f} ~ {df['VALUE_SCORE'].max():.1f}")

    # 薪資模組
    print("\n[3/7] 執行薪資分析...")
    salary_module = SalaryModule()
    df = salary_module.analyze(df)
    print(f"  新增欄位：CAP_PCT, SALARY_TIER, MARKET_VALUE_M, SALARY_SURPLUS_M")
    print(f"  薪資帽佔比範圍：{df['CAP_PCT'].min():.1f}% ~ {df['CAP_PCT'].max():.1f}%")

    # 適配度模組
    print("\n[4/7] 執行適配度分析...")
    fit_module = FitModule()
    df = fit_module.analyze(df)
    print(f"  新增欄位：PLAY_STYLE, OFFENSIVE_ROLE, DEFENSIVE_ROLE, POSITIONS")
    style_counts = df['PLAY_STYLE'].value_counts()
    print(f"  打法風格分類：{len(style_counts)} 種")

    # 交易價值引擎
    print("\n[5/7] 計算交易價值...")
    engine = TradeValueEngine()
    df = engine.calculate(df)
    print(f"  TRADE_VALUE 範圍：{df['TRADE_VALUE'].min():.1f} ~ {df['TRADE_VALUE'].max():.1f}")
    tier_counts = df['TRADE_VALUE_TIER'].value_counts()
    for tier, count in tier_counts.items():
        print(f"    {tier}: {count} 人")

    # 合約模組 (新增)
    print("\n[6/7] 執行合約分析...")
    contract_module = ContractModule()
    df = contract_module.analyze(df)
    print(f"  新增欄位：CONTRACT_TYPE, YEARS_REMAINING, CONTRACT_FLEXIBILITY")
    contract_counts = df['CONTRACT_TYPE_CN'].value_counts()
    for ctype, count in contract_counts.head(5).items():
        print(f"    {ctype}: {count} 人")

    # 輸出完整報告
    print("\n" + stats_module.report(df))
    print("\n" + salary_module.report(df))
    print("\n" + fit_module.report(df))
    print("\n" + contract_module.report(df))
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
        'CONTRACT_TYPE', 'CONTRACT_TYPE_CN', 'YEARS_REMAINING',
        'CONTRACT_FLEXIBILITY', 'TRADE_RESTRICTIONS',
        'TRADE_VALUE', 'TRADE_VALUE_TIER',
    ]
    available_cols = [c for c in ranking_cols if c in df.columns]
    ranking_output = os.path.join(output_dir, "trade_value_ranking.csv")
    df[available_cols].to_csv(ranking_output, index=False)
    print(f"排名結果已儲存至 {ranking_output}")

    # AI 分析 (可選)
    if include_ai_analysis and target_team:
        print(f"\n[7/7] 執行 AI 分析 ({target_team})...")
        ai_module = AIAnalysisModule()
        analysis = ai_module.analyze_team(df, target_team)
        report = ai_module.generate_natural_language_report(analysis)
        
        print("\n" + report)
        
        # 儲存 AI 報告
        ai_output = os.path.join(output_dir, f"ai_report_{target_team}.md")
        with open(ai_output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\nAI 分析報告已儲存至 {ai_output}")
    else:
        print("\n[7/7] 跳過 AI 分析 (使用 --ai-team 參數啟用)")

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


def demo_ai_analysis(df: pd.DataFrame, team: str = 'OKC'):
    """示範：AI 分析"""
    print("\n" + "=" * 70)
    print(f"🤖 AI 球隊分析示範 ({team})")
    print("=" * 70)
    
    ai_module = AIAnalysisModule()
    
    # 完整分析
    analysis = ai_module.analyze_team(df, team)
    
    # 生成報告
    report = ai_module.generate_natural_language_report(analysis)
    print(report)
    
    # 示範自然語言查詢
    print("\n" + "=" * 70)
    print("🔍 自然語言查詢示範")
    print("=" * 70)
    
    queries = [
        "誰是性價比最高的控球後衛？",
        "25歲以下最佳球員是誰？",
    ]
    
    for q in queries:
        print(f"\n問題：{q}")
        answer = ai_module.query(df, q)
        print(answer)


def demo_contract_analysis(df: pd.DataFrame):
    """示範：合約分析"""
    contract_module = ContractModule()
    
    print("\n" + "=" * 70)
    print("📜 合約分析示範")
    print("=" * 70)
    
    # 選秀權價值
    print("\n▸ 選秀權價值計算：")
    for pick in [1, 5, 10, 15, 20, 30]:
        value = contract_module.get_draft_pick_value(pick)
        protected_value = contract_module.get_draft_pick_value(pick, "TOP_5")
        future_value = contract_module.get_draft_pick_value(pick, years_out=2)
        print(f"  第 {pick:2d} 順位：價值 {value:.1f} | Top-5 保護: {protected_value:.1f} | 2年後: {future_value:.1f}")
    
    # 合約彈性排名
    print("\n▸ 合約彈性最高（最易交易）：")
    if 'CONTRACT_FLEXIBILITY' in df.columns:
        top_flex = df.nlargest(10, 'CONTRACT_FLEXIBILITY')
        display_cols = ['PLAYER_NAME', 'SALARY_M', 'YEARS_REMAINING', 
                       'CONTRACT_FLEXIBILITY', 'TRADE_RESTRICTIONS']
        avail = [c for c in display_cols if c in df.columns]
        print(top_flex[avail].to_string(index=False))


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(description='NBA 交易價值評估系統 v2.0')
    parser.add_argument('--data', type=str, default='data/processed/players_with_salary.csv',
                        help='輸入數據路徑')
    parser.add_argument('--output', type=str, default='data/processed',
                        help='輸出目錄')
    parser.add_argument('--ai-team', type=str, default=None,
                        help='執行 AI 分析的目標球隊 (例如: OKC, LAL)')
    parser.add_argument('--demo', action='store_true',
                        help='執行示範模式')
    parser.add_argument('--dashboard', action='store_true',
                        help='啟動 Streamlit 儀表板')
    parser.add_argument('--fetch-contracts', action='store_true',
                        help='從 Spotrac 抓取真實合約數據')
    parser.add_argument('--chat', action='store_true',
                        help='啟動 AI 對話模式')

    args = parser.parse_args()

    # 啟動儀表板
    if args.dashboard:
        print("🚀 啟動 Streamlit 儀表板...")
        print("   URL: http://localhost:8501")
        os.system('streamlit run src/dashboard/app.py')
        return

    # 抓取合約數據
    if args.fetch_contracts:
        print("📜 開始抓取真實合約數據...")
        from src.data_collection.fetch_all_contracts import fetch_all_contracts, merge_contracts_to_players
        players_df = pd.read_csv(args.data)
        fetch_all_contracts(players_df, delay=1.5, output_path="data/raw/player_contracts.json")
        print("✅ 合約數據抓取完成")
        return

    # AI 對話模式
    if args.chat:
        run_chat_mode(args.data)
        return

    # 執行主流程
    df = run_pipeline(
        data_path=args.data,
        output_dir=args.output,
        include_ai_analysis=args.ai_team is not None,
        target_team=args.ai_team
    )

    # 示範模式
    if args.demo:
        demo_trade_simulation(df)
        demo_contract_analysis(df)
        if args.ai_team:
            demo_ai_analysis(df, args.ai_team)
        else:
            demo_ai_analysis(df, 'OKC')


def run_chat_mode(data_path: str):
    """AI 對話模式"""
    print("=" * 70)
    print("🤖 NBA 交易價值評估系統 - AI 對話模式")
    print("=" * 70)
    print("輸入問題與 AI 對話，輸入 'exit' 或 'quit' 結束")
    print("-" * 70)

    # 載入數據
    df = pd.read_csv(data_path)
    print(f"已載入 {len(df)} 名球員數據\n")

    ai_module = AIAnalysisModule()

    # 檢查 API 狀態
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        print("✅ Claude API 已連接\n")
    else:
        print("⚠️ 未設置 ANTHROPIC_API_KEY，使用本地規則分析")
        print("   設置方式：export ANTHROPIC_API_KEY='your-key'\n")

    while True:
        try:
            question = input("你: ").strip()
            if not question:
                continue
            if question.lower() in ['exit', 'quit', 'q']:
                print("再見！👋")
                break

            print("\nAI: ", end="")
            response = ai_module.query(df, question, use_ai=bool(api_key))
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n再見！👋")
            break
        except Exception as e:
            print(f"錯誤: {e}\n")


if __name__ == "__main__":
    main()