"""
適配度模組 (Fit Module)
=======================
分析球員與球隊陣容的適配程度

功能：
• 打法風格分類
• 與現有陣容互補性分析
• 位置彈性評估
• 進攻/防守角色適配
"""

import pandas as pd
import numpy as np

try:
    from src.models.scoring_config import get_default_scoring_config
except ImportError:
    from models.scoring_config import get_default_scoring_config


# 打法風格定義
PLAY_STYLES = {
    'SCORING_GUARD': '得分後衛型',       # 高得分、高使用率、外線射手
    'PLAYMAKER': '組織者型',             # 高助攻、中高使用率
    'THREE_AND_D': '3D 球員型',          # 中低使用率、高三分命中率、低失誤
    'RIM_PROTECTOR': '護框中鋒型',       # 高籃板、高阻攻、低使用率
    'STRETCH_BIG': '空間型大個子',       # 大個子+三分能力
    'TWO_WAY_WING': '雙向側翼型',       # 均衡攻防、側翼身材
    'PAINT_BEAST': '禁區猛獸型',         # 高籃板、高 FG%、高得分
    'FLOOR_GENERAL': '地板指揮官型',     # 超高助攻、控制比賽節奏
    'VERSATILE_SCORER': '多元得分手型',  # 高得分、多樣化得分方式
    'ROLE_PLAYER': '角色球員型',         # 一般分類
}

# 位置身高推估 (英呎-英寸 → 位置)
POSITION_HEIGHT_MAP = {
    (72, 76): ['PG'],           # 6-0 ~ 6-4
    (76, 79): ['PG', 'SG'],    # 6-4 ~ 6-7
    (79, 81): ['SG', 'SF'],    # 6-7 ~ 6-9
    (81, 83): ['SF', 'PF'],    # 6-9 ~ 6-11
    (83, 90): ['PF', 'C'],     # 6-11 ~ 7+
}


class FitModule:
    """適配度分析模組"""

    def __init__(self, scoring_config=None):
        self.scoring_config = scoring_config or get_default_scoring_config()
        self.versatility_weights = self.scoring_config["fit_model"]["versatility_weights"]
        self.def_role_scores = self.scoring_config["fit_model"]["defense_role_scores"]

    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        主要分析入口

        輸入 DataFrame 需包含基本統計與進階數據
        輸出新增：PLAY_STYLE, PLAY_STYLE_CN, OFFENSIVE_ROLE, DEFENSIVE_ROLE,
                  POSITION_FLEX, POSITIONS, FIT_VERSATILITY_SCORE
        """
        df = df.copy()

        # 1. 分類打法風格
        styles = df.apply(self._classify_play_style, axis=1)
        df['PLAY_STYLE'] = styles.apply(lambda x: x[0])
        df['PLAY_STYLE_CN'] = styles.apply(lambda x: x[1])

        # 2. 進攻角色
        df['OFFENSIVE_ROLE'] = df.apply(self._classify_offensive_role, axis=1)

        # 3. 防守角色
        df['DEFENSIVE_ROLE'] = df.apply(self._classify_defensive_role, axis=1)

        # 4. 位置彈性
        positions = df['PLAYER_HEIGHT'].apply(self._estimate_positions)
        df['POSITIONS'] = positions.apply(lambda x: '/'.join(x) if x else 'UNKNOWN')
        df['POSITION_FLEX'] = positions.apply(lambda x: len(x) if x else 0)

        # 5. 綜合適配彈性分數
        df['FIT_VERSATILITY_SCORE'] = self._calculate_versatility(df)

        return df

    def _classify_play_style(self, row: pd.Series) -> tuple:
        """
        根據球員數據分類打法風格

        回傳 (英文代碼, 中文名稱)
        """
        pts = row.get('PTS', 0)
        ast = row.get('AST', 0)
        reb = row.get('REB', 0)
        blk = row.get('BLK', 0)
        stl = row.get('STL', 0)
        fg3_pct = row.get('FG3_PCT', 0)
        fg_pct = row.get('FG_PCT', 0)
        usg = row.get('USG_PCT', 0)
        height = self._parse_height_inches(row.get('PLAYER_HEIGHT', ''))
        ts_pct = row.get('TS_PCT', 0)

        is_big = height >= 81 if height else False  # 6-9+

        # 地板指揮官：超高助攻
        if ast >= 8 and usg >= 0.22:
            return ('FLOOR_GENERAL', PLAY_STYLES['FLOOR_GENERAL'])

        # 禁區猛獸：大個子 + 高籃板 + 高得分
        if is_big and reb >= 9 and pts >= 18 and fg_pct >= 0.55:
            return ('PAINT_BEAST', PLAY_STYLES['PAINT_BEAST'])

        # 護框中鋒：大個子 + 高籃板 + 高阻攻
        if is_big and blk >= 1.5 and reb >= 7:
            return ('RIM_PROTECTOR', PLAY_STYLES['RIM_PROTECTOR'])

        # 空間型大個子：大個子 + 能投三分
        if is_big and fg3_pct >= 0.33:
            return ('STRETCH_BIG', PLAY_STYLES['STRETCH_BIG'])

        # 多元得分手：高得分 + 高使用率 + 高效率
        if pts >= 22 and usg >= 0.28 and ts_pct >= 0.56:
            return ('VERSATILE_SCORER', PLAY_STYLES['VERSATILE_SCORER'])

        # 得分後衛型：高得分 + 外線能力
        if pts >= 18 and fg3_pct >= 0.35 and usg >= 0.25:
            return ('SCORING_GUARD', PLAY_STYLES['SCORING_GUARD'])

        # 組織者：中高助攻
        if ast >= 5 and usg >= 0.20:
            return ('PLAYMAKER', PLAY_STYLES['PLAYMAKER'])

        # 雙向側翼：均衡攻防
        if not is_big and stl >= 1.0 and pts >= 12 and fg3_pct >= 0.33:
            return ('TWO_WAY_WING', PLAY_STYLES['TWO_WAY_WING'])

        # 3D 球員：低使用率 + 三分能力
        if fg3_pct >= 0.36 and usg < 0.22 and stl >= 0.5:
            return ('THREE_AND_D', PLAY_STYLES['THREE_AND_D'])

        return ('ROLE_PLAYER', PLAY_STYLES['ROLE_PLAYER'])

    def _classify_offensive_role(self, row: pd.Series) -> str:
        """分類進攻角色"""
        pts = row.get('PTS', 0)
        ast = row.get('AST', 0)
        usg = row.get('USG_PCT', 0)

        if pts >= 25 and usg >= 0.30:
            return 'PRIMARY_SCORER'    # 第一得分手
        elif ast >= 7:
            return 'PRIMARY_PLAYMAKER' # 主要組織者
        elif pts >= 18 and usg >= 0.23:
            return 'SECONDARY_SCORER'  # 第二得分手
        elif ast >= 4:
            return 'SECONDARY_PLAYMAKER'  # 次要組織者
        elif row.get('FG3_PCT', 0) >= 0.36:
            return 'FLOOR_SPACER'      # 空間拉開者
        else:
            return 'FINISHER'          # 終結者/角色球員

    def _classify_defensive_role(self, row: pd.Series) -> str:
        """分類防守角色"""
        blk = row.get('BLK', 0)
        stl = row.get('STL', 0)
        reb = row.get('REB', 0)
        height = self._parse_height_inches(row.get('PLAYER_HEIGHT', ''))
        def_rating = row.get('DEF_RATING', 115)

        is_big = height >= 81 if height else False

        if is_big and blk >= 1.5:
            return 'RIM_PROTECTOR'     # 護框者
        elif is_big and reb >= 8:
            return 'REBOUNDER'         # 籃板專家
        elif stl >= 1.5:
            return 'PERIMETER_STOPPER' # 外線防守者
        elif stl >= 1.0 and blk >= 0.5:
            return 'VERSATILE_DEFENDER' # 全能防守者
        elif def_rating <= 108:
            return 'SOLID_DEFENDER'    # 穩定防守者
        else:
            return 'LIMITED_DEFENDER'  # 有限防守者

    def _parse_height_inches(self, height_str) -> int:
        """將身高字串 '6-11' 轉為英寸"""
        if pd.isna(height_str) or not height_str:
            return 0
        height_str = str(height_str)
        try:
            parts = height_str.split('-')
            if len(parts) == 2:
                return int(parts[0]) * 12 + int(parts[1])
        except (ValueError, IndexError):
            pass
        return 0

    def _estimate_positions(self, height_str) -> list:
        """根據身高推估可能的位置"""
        inches = self._parse_height_inches(height_str)
        if inches == 0:
            return []

        positions = set()
        for (low, high), pos_list in POSITION_HEIGHT_MAP.items():
            if low <= inches < high:
                positions.update(pos_list)

        return sorted(positions) if positions else ['C'] if inches >= 83 else ['PG']

    def _calculate_versatility(self, df: pd.DataFrame) -> pd.Series:
        """
        計算綜合適配彈性分數 (0-100)

        考量因素：
        - 位置彈性 (30%)
        - 攻防角色多樣性 (30%)
        - 統計均衡度 (40%)
        """
        # 位置彈性分數
        pos_score = (df['POSITION_FLEX'] / 2 * 100).clip(upper=100)

        # 統計均衡度 (越均衡越高)
        stats_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK']
        available = [c for c in stats_cols if c in df.columns]
        if available:
            normalized = df[available].apply(lambda x: x.rank(pct=True))
            # 用最小值來衡量均衡度 — 越沒有短板越好
            balance_score = (normalized.min(axis=1) * 100).round(1)
        else:
            balance_score = pd.Series(50, index=df.index)

        # 攻防角色分數 — 非 LIMITED_DEFENDER 得分
        def_role_score = df['DEFENSIVE_ROLE'].apply(
            lambda x: self.def_role_scores["elite"] if x in ('VERSATILE_DEFENDER', 'PERIMETER_STOPPER')
            else self.def_role_scores["solid"] if x in ('RIM_PROTECTOR', 'REBOUNDER', 'SOLID_DEFENDER')
            else self.def_role_scores["weak"]
        )

        w = self.versatility_weights
        versatility = (
            pos_score * w["position"] +
            def_role_score * w["defense"] +
            balance_score * w["balance"]
        ).round(1)

        return versatility

    def evaluate_team_fit(self, player_row: pd.Series, team_df: pd.DataFrame) -> dict:
        """
        評估某球員對特定球隊的適配度

        回傳適配度報告 dict
        """
        result = {
            'player': player_row.get('PLAYER_NAME', 'Unknown'),
            'play_style': player_row.get('PLAY_STYLE_CN', ''),
            'scores': {},
            'analysis': [],
        }

        team_styles = team_df['PLAY_STYLE'].value_counts()
        player_style = player_row.get('PLAY_STYLE', '')

        # 互補性：如果球隊缺少該風格的球員，互補度更高
        style_count = team_styles.get(player_style, 0)
        if style_count == 0:
            result['scores']['complementarity'] = 90
            result['analysis'].append(f"球隊缺少 {player_row.get('PLAY_STYLE_CN', '')} 風格球員，互補性極高")
        elif style_count == 1:
            result['scores']['complementarity'] = 70
            result['analysis'].append(f"球隊已有 1 名相同風格球員，互補性中等")
        else:
            result['scores']['complementarity'] = 40
            result['analysis'].append(f"球隊已有 {style_count} 名相同風格球員，互補性較低")

        # 位置需求
        player_positions = player_row.get('POSITIONS', '').split('/')
        team_positions = team_df['POSITIONS'].str.split('/').explode().value_counts()
        thin_positions = [p for p in ['PG', 'SG', 'SF', 'PF', 'C']
                          if team_positions.get(p, 0) < 3]

        overlap = set(player_positions) & set(thin_positions)
        if overlap:
            result['scores']['position_need'] = 85
            result['analysis'].append(f"球隊在 {'/'.join(overlap)} 位置薄弱，該球員可填補")
        else:
            result['scores']['position_need'] = 50

        # 綜合適配分數
        scores = result['scores']
        result['overall_fit'] = round(
            scores.get('complementarity', 50) * 0.5 +
            scores.get('position_need', 50) * 0.5,
            1
        )

        return result

    def report(self, df: pd.DataFrame) -> str:
        """產生適配度分析報告"""
        lines = []
        lines.append("=" * 70)
        lines.append("🧩 適配度模組分析報告")
        lines.append("=" * 70)

        # 打法風格分布
        lines.append("\n▸ 打法風格分布：")
        style_counts = df['PLAY_STYLE_CN'].value_counts()
        for style, count in style_counts.items():
            lines.append(f"  {style:15s}: {count:3d} 人")

        # 進攻角色分布
        lines.append("\n▸ 進攻角色分布：")
        off_counts = df['OFFENSIVE_ROLE'].value_counts()
        for role, count in off_counts.items():
            lines.append(f"  {role:22s}: {count:3d} 人")

        # 防守角色分布
        lines.append("\n▸ 防守角色分布：")
        def_counts = df['DEFENSIVE_ROLE'].value_counts()
        for role, count in def_counts.items():
            lines.append(f"  {role:22s}: {count:3d} 人")

        # 最高適配彈性
        lines.append("\n▸ 適配彈性最高 Top 15：")
        top_flex = df.nlargest(15, 'FIT_VERSATILITY_SCORE')
        for _, row in top_flex.iterrows():
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"彈性={row['FIT_VERSATILITY_SCORE']:5.1f}  "
                f"位置={row['POSITIONS']:8s}  "
                f"風格={row['PLAY_STYLE_CN']}"
            )

        return "\n".join(lines)
