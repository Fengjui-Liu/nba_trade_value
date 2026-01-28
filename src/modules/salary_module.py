"""
薪資模組 (Salary Module)
========================
分析球員薪資結構、合約年限、薪資帽佔比、市場價值估算

功能：
• 當前薪資分析
• 合約年限評估
• 薪資帽佔比計算
• 基於表現的市場價值估算
"""

import pandas as pd
import numpy as np


# 2024-25 NBA 薪資帽
SALARY_CAP_2025 = 140_588_000
LUXURY_TAX_2025 = 170_814_000
FIRST_APRON_2025 = 178_132_000
SECOND_APRON_2025 = 188_931_000

# 最大薪資比例（依年資）
MAX_SALARY_PCT = {
    "0-6": 0.25,   # 0-6 年年資：薪資帽 25%
    "7-9": 0.30,   # 7-9 年年資：薪資帽 30%
    "10+": 0.35,   # 10+ 年年資：薪資帽 35%
}


class SalaryModule:
    """薪資分析模組"""

    def __init__(self, salary_cap=SALARY_CAP_2025):
        self.salary_cap = salary_cap
        self.luxury_tax = LUXURY_TAX_2025

    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        主要分析入口：計算薪資相關指標

        輸入 DataFrame 需包含：SALARY_M, AGE, VALUE_SCORE (來自進階數據模組)
        輸出新增欄位：CAP_PCT, SALARY_TIER, MARKET_VALUE_M, SALARY_SURPLUS_M, CONTRACT_VALUE_RATIO
        """
        df = df.copy()

        # 1. 薪資帽佔比
        df['CAP_PCT'] = (df['SALARY_M'] * 1e6 / self.salary_cap * 100).round(2)

        # 2. 薪資等級分類
        df['SALARY_TIER'] = df['SALARY_M'].apply(self._classify_salary_tier)

        # 3. 市場價值估算（基於表現分數）
        df['MARKET_VALUE_M'] = df.apply(
            lambda row: self._estimate_market_value(
                row.get('VALUE_SCORE_ADJ', row.get('VALUE_SCORE', 50)),
                row.get('AGE', 27)
            ),
            axis=1
        )

        # 4. 薪資剩餘價值
        df['SALARY_SURPLUS_M'] = (df['MARKET_VALUE_M'] - df['SALARY_M']).round(2)

        # 5. 合約性價比 (市場價值 / 實際薪資)
        df['CONTRACT_VALUE_RATIO'] = np.where(
            df['SALARY_M'] > 0,
            (df['MARKET_VALUE_M'] / df['SALARY_M']).round(2),
            np.nan
        )

        return df

    def _classify_salary_tier(self, salary_m: float) -> str:
        """將薪資分為等級"""
        if pd.isna(salary_m):
            return "UNKNOWN"
        if salary_m >= 40:
            return "SUPERMAX"     # 超級頂薪
        elif salary_m >= 30:
            return "MAX"          # 頂薪
        elif salary_m >= 20:
            return "NEAR_MAX"     # 接近頂薪
        elif salary_m >= 10:
            return "MID_LEVEL"    # 中產等級
        elif salary_m >= 5:
            return "ROLE_PLAYER"  # 角色球員
        elif salary_m >= 2:
            return "MINIMUM_PLUS" # 底薪+
        else:
            return "MINIMUM"      # 底薪

    def _estimate_market_value(self, value_score: float, age: float) -> float:
        """
        基於表現分數與年齡估算市場價值

        使用分段線性模型：
        - 分數 90+: 頂薪區間 ($40M-$51M)
        - 分數 70-90: 中高薪 ($20M-$40M)
        - 分數 50-70: 中薪 ($8M-$20M)
        - 分數 30-50: 角色球員 ($3M-$8M)
        - 分數 <30: 底薪區間 ($1M-$3M)
        """
        if pd.isna(value_score):
            return 0.0

        score = float(value_score)

        if score >= 90:
            market_val = 40 + (score - 90) / 10 * 11  # 40-51M
        elif score >= 70:
            market_val = 20 + (score - 70) / 20 * 20  # 20-40M
        elif score >= 50:
            market_val = 8 + (score - 50) / 20 * 12   # 8-20M
        elif score >= 30:
            market_val = 3 + (score - 30) / 20 * 5    # 3-8M
        else:
            market_val = max(1.0, score / 30 * 3)       # 1-3M

        # 年齡折扣（影響未來合約預期）
        if not pd.isna(age):
            if age >= 35:
                market_val *= 0.70
            elif age >= 33:
                market_val *= 0.85
            elif age >= 31:
                market_val *= 0.95

        return round(market_val, 2)

    def get_team_salary_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算各隊薪資結構摘要"""
        team_col = 'TEAM_ABBREVIATION'
        if team_col not in df.columns:
            return pd.DataFrame()

        summary = df.groupby(team_col).agg(
            TOTAL_SALARY_M=('SALARY_M', 'sum'),
            AVG_SALARY_M=('SALARY_M', 'mean'),
            MAX_SALARY_M=('SALARY_M', 'max'),
            NUM_PLAYERS=('SALARY_M', 'count'),
            TOTAL_SURPLUS_M=('SALARY_SURPLUS_M', 'sum'),
        ).round(2)

        summary['CAP_USAGE_PCT'] = (
            summary['TOTAL_SALARY_M'] * 1e6 / self.salary_cap * 100
        ).round(1)

        summary['OVER_TAX'] = summary['TOTAL_SALARY_M'] * 1e6 > self.luxury_tax

        return summary.sort_values('TOTAL_SURPLUS_M', ascending=False)

    def report(self, df: pd.DataFrame) -> str:
        """產生薪資分析報告"""
        lines = []
        lines.append("=" * 70)
        lines.append("💰 薪資模組分析報告")
        lines.append("=" * 70)

        # 薪資等級分布
        lines.append("\n▸ 薪資等級分布：")
        tier_counts = df['SALARY_TIER'].value_counts()
        for tier, count in tier_counts.items():
            lines.append(f"  {tier:15s}: {count:3d} 人")

        # 最佳性價比
        top_value = df.nlargest(10, 'SALARY_SURPLUS_M')
        lines.append("\n▸ 最佳性價比 Top 10：")
        for _, row in top_value.iterrows():
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"薪資=${row['SALARY_M']:5.1f}M  "
                f"市值=${row['MARKET_VALUE_M']:5.1f}M  "
                f"剩餘=+${row['SALARY_SURPLUS_M']:5.1f}M"
            )

        # 最不划算
        worst_value = df.nsmallest(10, 'SALARY_SURPLUS_M')
        lines.append("\n▸ 最不划算 Top 10：")
        for _, row in worst_value.iterrows():
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"薪資=${row['SALARY_M']:5.1f}M  "
                f"市值=${row['MARKET_VALUE_M']:5.1f}M  "
                f"剩餘=${row['SALARY_SURPLUS_M']:5.1f}M"
            )

        return "\n".join(lines)
