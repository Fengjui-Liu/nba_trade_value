"""
交易價值引擎 (Trade Value Engine)
=================================
整合三大模組，計算球員最終交易價值

核心公式：
  Surplus Value = 表現價值 (Market Value) - 實際薪資 (Actual Salary)

權重：
  - 進階數據 VALUE_SCORE_ADJ: 50%
  - 薪資效率 CONTRACT_VALUE_RATIO: 25%
  - 適配彈性 FIT_VERSATILITY_SCORE: 25%
"""

import pandas as pd
import numpy as np


class TradeValueEngine:
    """交易價值計算引擎"""

    # 權重配置
    WEIGHTS = {
        'performance': 0.50,  # 進階數據表現
        'contract': 0.25,     # 薪資效率
        'fit': 0.25,          # 適配彈性
    }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算最終交易價值

        輸入：經過三大模組分析後的 DataFrame
        輸出：新增 TRADE_VALUE, TRADE_VALUE_TIER, SURPLUS_VALUE_M 欄位
        """
        df = df.copy()

        # 1. 標準化各模組分數到 0-100
        df['PERF_SCORE_NORM'] = self._normalize(df['VALUE_SCORE_ADJ'])
        df['CONTRACT_SCORE_NORM'] = self._normalize(
            df['CONTRACT_VALUE_RATIO'].clip(upper=5)  # 避免極端值
        )
        df['FIT_SCORE_NORM'] = self._normalize(df['FIT_VERSATILITY_SCORE'])

        # 2. 加權綜合交易價值
        df['TRADE_VALUE'] = (
            df['PERF_SCORE_NORM'] * self.WEIGHTS['performance'] +
            df['CONTRACT_SCORE_NORM'] * self.WEIGHTS['contract'] +
            df['FIT_SCORE_NORM'] * self.WEIGHTS['fit']
        ).round(1)

        # 3. 交易價值等級
        df['TRADE_VALUE_TIER'] = df['TRADE_VALUE'].apply(self._classify_trade_tier)

        # 4. 剩餘價值 (已由薪資模組計算，此處整合)
        if 'SALARY_SURPLUS_M' in df.columns:
            df['SURPLUS_VALUE_M'] = df['SALARY_SURPLUS_M']
        else:
            df['SURPLUS_VALUE_M'] = (df['MARKET_VALUE_M'] - df['SALARY_M']).round(2)

        # 排序
        df = df.sort_values('TRADE_VALUE', ascending=False).reset_index(drop=True)

        return df

    def _normalize(self, series: pd.Series) -> pd.Series:
        """將序列標準化到 0-100"""
        s = series.fillna(0)
        min_val = s.min()
        max_val = s.max()
        if max_val == min_val:
            return pd.Series(50, index=series.index)
        return ((s - min_val) / (max_val - min_val) * 100).round(1)

    def _classify_trade_tier(self, value: float) -> str:
        """交易價值等級分類"""
        if value >= 85:
            return 'UNTOUCHABLE'   # 不可交易等級
        elif value >= 70:
            return 'FRANCHISE'     # 基石球員
        elif value >= 55:
            return 'ALL_STAR'      # 全明星等級
        elif value >= 40:
            return 'QUALITY_STARTER'  # 優質先發
        elif value >= 25:
            return 'ROTATION'      # 輪替球員
        else:
            return 'TRADEABLE'     # 可交易

    def get_trade_targets(self, df: pd.DataFrame, budget_m: float,
                          positions: list = None, style: str = None,
                          max_age: int = None, top_n: int = 20) -> pd.DataFrame:
        """
        搜尋符合條件的交易目標

        參數：
        - budget_m: 薪資預算 (百萬)
        - positions: 需要的位置列表 (e.g. ['PG', 'SG'])
        - style: 需要的打法風格
        - max_age: 最大年齡
        - top_n: 回傳筆數
        """
        candidates = df.copy()

        # 薪資篩選
        candidates = candidates[candidates['SALARY_M'] <= budget_m]

        # 位置篩選
        if positions:
            mask = candidates['POSITIONS'].apply(
                lambda x: any(p in str(x) for p in positions)
            )
            candidates = candidates[mask]

        # 風格篩選
        if style:
            candidates = candidates[candidates['PLAY_STYLE'] == style]

        # 年齡篩選
        if max_age:
            candidates = candidates[candidates['AGE'] <= max_age]

        return candidates.nlargest(top_n, 'TRADE_VALUE')

    def compare_players(self, df: pd.DataFrame, player_names: list) -> pd.DataFrame:
        """
        比較指定球員的交易價值

        回傳選定球員的詳細比較表
        """
        compare_cols = [
            'PLAYER_NAME', 'TEAM_ABBREVIATION', 'AGE',
            'PTS', 'REB', 'AST',
            'PER_APPROX', 'BPM_APPROX', 'VORP_APPROX', 'WIN_SHARES_APPROX',
            'PLAY_STYLE_CN', 'OFFENSIVE_ROLE', 'DEFENSIVE_ROLE',
            'POSITIONS', 'FIT_VERSATILITY_SCORE',
            'SALARY_M', 'CAP_PCT', 'SALARY_TIER',
            'MARKET_VALUE_M', 'SURPLUS_VALUE_M',
            'TRADE_VALUE', 'TRADE_VALUE_TIER',
        ]

        available_cols = [c for c in compare_cols if c in df.columns]
        mask = df['PLAYER_NAME'].isin(player_names)
        return df.loc[mask, available_cols].sort_values('TRADE_VALUE', ascending=False)

    def simulate_trade(self, df: pd.DataFrame,
                       team_a_gives: list, team_b_gives: list) -> dict:
        """
        模擬交易，比較雙方交換價值

        參數：
        - team_a_gives: A 隊送出的球員名單
        - team_b_gives: B 隊送出的球員名單

        回傳：交易分析 dict
        """
        def _get_package_value(names):
            players = df[df['PLAYER_NAME'].isin(names)]
            return {
                'players': names,
                'total_salary_m': round(players['SALARY_M'].sum(), 2),
                'total_trade_value': round(players['TRADE_VALUE'].sum(), 1),
                'total_surplus_m': round(players['SURPLUS_VALUE_M'].sum(), 2),
                'avg_age': round(players['AGE'].mean(), 1),
                'details': players[['PLAYER_NAME', 'AGE', 'SALARY_M',
                                    'TRADE_VALUE', 'SURPLUS_VALUE_M']].to_dict('records')
            }

        pkg_a = _get_package_value(team_a_gives)
        pkg_b = _get_package_value(team_b_gives)

        # 薪資匹配檢查 (NBA CBA 規則: 差距不能超過 125% + 100K)
        salary_diff = abs(pkg_a['total_salary_m'] - pkg_b['total_salary_m'])
        higher_salary = max(pkg_a['total_salary_m'], pkg_b['total_salary_m'])
        lower_salary = min(pkg_a['total_salary_m'], pkg_b['total_salary_m'])
        salary_match = lower_salary * 1.25 + 0.1 >= higher_salary

        value_diff = pkg_a['total_trade_value'] - pkg_b['total_trade_value']

        return {
            'team_a_package': pkg_a,
            'team_b_package': pkg_b,
            'salary_match': salary_match,
            'salary_diff_m': round(salary_diff, 2),
            'value_difference': round(value_diff, 1),
            'verdict': (
                '交易價值大致平衡' if abs(value_diff) < 5
                else f"{'A 隊' if value_diff > 0 else 'B 隊'}送出更多價值 ({abs(value_diff):.1f})"
            )
        }

    def report(self, df: pd.DataFrame) -> str:
        """產生最終交易價值報告"""
        lines = []
        lines.append("=" * 70)
        lines.append("🏀 NBA 球員交易價值總報告")
        lines.append("=" * 70)

        # 交易價值等級分布
        lines.append("\n▸ 交易價值等級分布：")
        tier_order = ['UNTOUCHABLE', 'FRANCHISE', 'ALL_STAR',
                      'QUALITY_STARTER', 'ROTATION', 'TRADEABLE']
        tier_counts = df['TRADE_VALUE_TIER'].value_counts()
        for tier in tier_order:
            count = tier_counts.get(tier, 0)
            lines.append(f"  {tier:20s}: {count:3d} 人")

        # Top 20 交易價值
        lines.append("\n▸ 交易價值 Top 20：")
        lines.append(f"  {'球員':25s} {'年齡':>4s} {'交易價值':>8s} "
                     f"{'薪資($M)':>9s} {'市值($M)':>9s} {'剩餘($M)':>9s} {'等級':12s}")
        lines.append("  " + "-" * 85)
        top20 = df.nlargest(20, 'TRADE_VALUE')
        for _, row in top20.iterrows():
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"{row['AGE']:4.0f} "
                f"{row['TRADE_VALUE']:8.1f} "
                f"{row['SALARY_M']:9.1f} "
                f"{row['MARKET_VALUE_M']:9.1f} "
                f"{row['SURPLUS_VALUE_M']:+9.1f} "
                f"{row['TRADE_VALUE_TIER']:12s}"
            )

        # 最佳性價比 (高剩餘價值)
        lines.append("\n▸ 最佳交易目標 (剩餘價值最高)：")
        best_surplus = df.nlargest(10, 'SURPLUS_VALUE_M')
        for _, row in best_surplus.iterrows():
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"剩餘=+${row['SURPLUS_VALUE_M']:.1f}M  "
                f"薪資=${row['SALARY_M']:.1f}M  "
                f"風格={row.get('PLAY_STYLE_CN', 'N/A')}"
            )

        return "\n".join(lines)
