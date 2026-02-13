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

try:
    from src.config import SALARY_CAP_M, LUXURY_TAX_M, FIRST_APRON_M, SECOND_APRON_M
except ImportError:
    from config import SALARY_CAP_M, LUXURY_TAX_M, FIRST_APRON_M, SECOND_APRON_M

try:
    from src.models.scoring_config import get_default_scoring_config
except ImportError:
    from models.scoring_config import get_default_scoring_config


# 2025-26 NBA 薪資帽 (預估)
SALARY_CAP_2026 = int(SALARY_CAP_M * 1_000_000)
LUXURY_TAX_2026 = int(LUXURY_TAX_M * 1_000_000)
FIRST_APRON_2026 = int(FIRST_APRON_M * 1_000_000)
SECOND_APRON_2026 = int(SECOND_APRON_M * 1_000_000)

# 最大薪資比例（依年資）
MAX_SALARY_PCT = {
    "0-6": 0.25,   # 0-6 年年資：薪資帽 25%
    "7-9": 0.30,   # 7-9 年年資：薪資帽 30%
    "10+": 0.35,   # 10+ 年年資：薪資帽 35%
}


class SalaryModule:
    """薪資分析模組"""

    def __init__(self, salary_cap=SALARY_CAP_2026, scoring_config=None):
        self.salary_cap = salary_cap
        self.luxury_tax = LUXURY_TAX_2026
        self.scoring_config = scoring_config or get_default_scoring_config()
        self.salary_tiers = self.scoring_config["salary_model"]["salary_tiers"]
        self.market_segments = self.scoring_config["salary_model"]["market_segments"]
        self.age_discounts = self.scoring_config["salary_model"]["age_discounts"]

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
        for tier_name, min_salary in self.salary_tiers:
            if salary_m >= float(min_salary):
                return str(tier_name)
        return "MINIMUM"

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

        market_val = 0.0
        for threshold, min_val, max_val in self.market_segments:
            threshold = float(threshold)
            min_val = float(min_val)
            max_val = float(max_val)
            if score >= threshold:
                if threshold >= 90:
                    market_val = min_val + (score - threshold) / 10 * (max_val - min_val)
                elif threshold > 0:
                    market_val = min_val + (score - threshold) / 20 * (max_val - min_val)
                else:
                    market_val = max(1.0, score / 30 * max_val)
                break

        # 年齡折扣（影響未來合約預期）
        if not pd.isna(age):
            if age >= 35:
                market_val *= float(self.age_discounts["gte_35"])
            elif age >= 33:
                market_val *= float(self.age_discounts["gte_33"])
            elif age >= 31:
                market_val *= float(self.age_discounts["gte_31"])

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
