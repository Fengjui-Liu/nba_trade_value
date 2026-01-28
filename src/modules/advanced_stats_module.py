"""
進階數據模組 (Advanced Stats Module)
====================================
計算與整合進階籃球統計指標

功能：
• 效率值 (PER 近似)
• BPM / VORP 近似計算
• Win Shares 近似計算
• 年齡曲線預測
• 綜合價值評分 (VALUE_SCORE)
"""

import pandas as pd
import numpy as np


# 聯盟平均基準值 (2024-25 賽季近似)
LEAGUE_AVG = {
    'PTS': 14.0,
    'REB': 4.5,
    'AST': 3.0,
    'STL': 0.7,
    'BLK': 0.4,
    'FG_PCT': 0.460,
    'FG3_PCT': 0.360,
    'FT_PCT': 0.780,
    'TS_PCT': 0.570,
    'USG_PCT': 0.200,
    'PIE': 0.100,
    'NET_RATING': 0.0,
    'MIN': 20.0,
}

# 年齡曲線：球員表現相對於巔峰期的比例
AGE_CURVE = {
    19: 0.72, 20: 0.78, 21: 0.84, 22: 0.89, 23: 0.93,
    24: 0.96, 25: 0.98, 26: 1.00, 27: 1.00, 28: 0.99,
    29: 0.97, 30: 0.94, 31: 0.90, 32: 0.86, 33: 0.81,
    34: 0.75, 35: 0.69, 36: 0.62, 37: 0.55, 38: 0.48,
    39: 0.41, 40: 0.35,
}


class AdvancedStatsModule:
    """進階數據分析模組"""

    def __init__(self, min_gp=20, min_minutes=15):
        self.min_gp = min_gp
        self.min_minutes = min_minutes

    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        主要分析入口

        輸入 DataFrame 需包含基本統計欄位
        輸出新增：PER_APPROX, BPM_APPROX, VORP_APPROX, WIN_SHARES_APPROX,
                  AGE_CURVE_FACTOR, PROJECTED_VALUE, VALUE_SCORE, AGE_ADJ, VALUE_SCORE_ADJ
        """
        df = df.copy()

        # 篩選有效球員
        df = df[(df['GP'] >= self.min_gp) & (df['MIN'] >= self.min_minutes)].copy()

        # 1. PER 近似計算
        df['PER_APPROX'] = self._calculate_per_approx(df)

        # 2. BPM 近似計算
        df['BPM_APPROX'] = self._calculate_bpm_approx(df)

        # 3. VORP 近似計算 (BPM 基礎)
        df['VORP_APPROX'] = self._calculate_vorp_approx(df)

        # 4. Win Shares 近似計算
        df['WIN_SHARES_APPROX'] = self._calculate_win_shares_approx(df)

        # 5. 年齡曲線因子
        df['AGE_CURVE_FACTOR'] = df['AGE'].apply(self._get_age_curve_factor)

        # 6. 年齡調整後的預估未來價值
        df['PROJECTED_VALUE'] = (
            df['PER_APPROX'] * df['AGE_CURVE_FACTOR']
        ).round(2)

        # 7. 綜合價值評分
        df['VALUE_SCORE'] = self._calculate_value_score(df)

        # 8. 年齡調整分數
        df['AGE_ADJ'] = df['AGE'].apply(self._age_adjustment)
        df['VALUE_SCORE_ADJ'] = (df['VALUE_SCORE'] + df['AGE_ADJ']).round(1)

        return df.reset_index(drop=True)

    def _calculate_per_approx(self, df: pd.DataFrame) -> pd.Series:
        """
        PER 近似計算 (Player Efficiency Rating)

        簡化版 PER，基於每分鐘產出標準化
        正式 PER 需要隊伍節奏、聯盟調整等，此為近似值
        """
        per = (
            df['PTS'] * 1.0 +
            df['REB'] * 1.2 +
            df['AST'] * 1.5 +
            df['STL'] * 2.0 +
            df['BLK'] * 2.0 -
            (df['PTS'] / df['FG_PCT'].clip(lower=0.3) - df['PTS']) * 0.5 +  # 失誤懲罰近似
            df['TS_PCT'] * 10  # 效率加成
        )

        # 標準化到 PER 量表 (聯盟平均 ~15)
        per_normalized = (per / per.median() * 15).round(2)
        return per_normalized

    def _calculate_bpm_approx(self, df: pd.DataFrame) -> pd.Series:
        """
        BPM 近似計算 (Box Plus/Minus)

        基於 box score 統計估算每 100 回合的影響值
        聯盟平均 BPM = 0, 明星球員 > +4, MVP 級 > +8
        """
        # 以 NET_RATING 為基礎，加入個人貢獻調整
        bpm = (
            df['NET_RATING'] * 0.3 +
            (df['PTS'] - LEAGUE_AVG['PTS']) * 0.15 +
            (df['REB'] - LEAGUE_AVG['REB']) * 0.20 +
            (df['AST'] - LEAGUE_AVG['AST']) * 0.25 +
            (df['STL'] - LEAGUE_AVG['STL']) * 1.5 +
            (df['BLK'] - LEAGUE_AVG['BLK']) * 1.5 +
            (df['TS_PCT'] - LEAGUE_AVG['TS_PCT']) * 20
        ).round(2)

        return bpm

    def _calculate_vorp_approx(self, df: pd.DataFrame) -> pd.Series:
        """
        VORP 近似計算 (Value Over Replacement Player)

        VORP = (BPM - (-2.0)) * (MIN% * GP) / 82
        替補球員基準 BPM = -2.0
        """
        replacement_level = -2.0
        minutes_pct = df['MIN'] / 48.0
        vorp = ((df['BPM_APPROX'] - replacement_level) * minutes_pct * df['GP'] / 82).round(2)
        return vorp

    def _calculate_win_shares_approx(self, df: pd.DataFrame) -> pd.Series:
        """
        Win Shares 近似計算

        簡化公式：基於 PER、上場時間、比賽場次
        WS ≈ PER_APPROX * MIN * GP / (48 * 82 * 15) * 調整係數
        """
        # PER 15 = 聯盟平均，每 48 分鐘 82 場 ≈ 1 份完整賽季
        ws = (
            df['PER_APPROX'] * df['MIN'] * df['GP'] / (48 * 82 * 15) * 10
        ).round(2)

        return ws.clip(lower=0)

    def _get_age_curve_factor(self, age: float) -> float:
        """取得年齡曲線因子"""
        if pd.isna(age):
            return 1.0
        age_int = int(round(age))
        age_int = max(19, min(40, age_int))
        return AGE_CURVE.get(age_int, 0.5)

    def _age_adjustment(self, age: float) -> float:
        """年齡分數調整"""
        if pd.isna(age):
            return 0
        if age < 23:
            return 5    # 高潛力新秀
        elif age < 25:
            return 3    # 成長期
        elif age <= 28:
            return 0    # 巔峰期
        elif age <= 32:
            return -2   # 穩定期
        else:
            return -5   # 衰退風險

    def _calculate_value_score(self, df: pd.DataFrame) -> pd.Series:
        """
        綜合價值評分 (0-100 量表)

        權重：
        - PIE 指標: 25%
        - PER 近似: 20%
        - BPM 近似: 15%
        - 產量: 20%
        - 效率: 10%
        - Win Shares: 10%
        """
        # 各指標百分位排名
        pie_score = df['PIE'].rank(pct=True) * 100
        per_score = df['PER_APPROX'].rank(pct=True) * 100
        bpm_score = df['BPM_APPROX'].rank(pct=True) * 100
        ws_score = df['WIN_SHARES_APPROX'].rank(pct=True) * 100

        production_score = (
            df['PTS'].rank(pct=True) * 0.40 +
            df['REB'].rank(pct=True) * 0.25 +
            df['AST'].rank(pct=True) * 0.25 +
            df['STL'].rank(pct=True) * 0.05 +
            df['BLK'].rank(pct=True) * 0.05
        ) * 100

        ts_score = df['TS_PCT'].rank(pct=True) * 100

        value_score = (
            pie_score * 0.25 +
            per_score * 0.20 +
            bpm_score * 0.15 +
            production_score * 0.20 +
            ts_score * 0.10 +
            ws_score * 0.10
        ).round(1)

        return value_score

    def report(self, df: pd.DataFrame) -> str:
        """產生進階數據分析報告"""
        lines = []
        lines.append("=" * 70)
        lines.append("📊 進階數據模組分析報告")
        lines.append("=" * 70)

        # PER Top 15
        lines.append("\n▸ PER 近似值 Top 15：")
        top_per = df.nlargest(15, 'PER_APPROX')
        for _, row in top_per.iterrows():
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"PER={row['PER_APPROX']:5.1f}  "
                f"BPM={row['BPM_APPROX']:+5.1f}  "
                f"VORP={row['VORP_APPROX']:5.1f}  "
                f"WS={row['WIN_SHARES_APPROX']:4.1f}"
            )

        # VORP Top 15
        lines.append("\n▸ VORP 近似值 Top 15：")
        top_vorp = df.nlargest(15, 'VORP_APPROX')
        for _, row in top_vorp.iterrows():
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"VORP={row['VORP_APPROX']:5.1f}  "
                f"BPM={row['BPM_APPROX']:+5.1f}  "
                f"AGE={row['AGE']:.0f}  "
                f"年齡曲線={row['AGE_CURVE_FACTOR']:.2f}"
            )

        # VALUE_SCORE Top 15
        lines.append("\n▸ 綜合價值評分 Top 15：")
        top_val = df.nlargest(15, 'VALUE_SCORE_ADJ')
        for _, row in top_val.iterrows():
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"評分={row['VALUE_SCORE_ADJ']:5.1f}  "
                f"(原始={row['VALUE_SCORE']:5.1f}, 年齡調整={row['AGE_ADJ']:+.0f})"
            )

        return "\n".join(lines)
