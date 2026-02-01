"""
合約模組 (Contract Module)
==========================
推斷與分析球員合約細節

功能：
• 合約類型分類
• 剩餘年限推估
• 交易限制評估
• 選秀權價值計算
• 薪資匹配分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

# 2025-26 NBA 薪資帽相關 (預估)
SALARY_CAP_2026 = 153.0  # $153M
LUXURY_TAX_2026 = 186.0  # $186M
FIRST_APRON = 193.0
SECOND_APRON = 205.0

# 最大薪資比例
MAX_SALARY_PCT = {
    '0-6': 0.25,   # 25% = ~$38.3M
    '7-9': 0.30,   # 30% = ~$45.9M
    '10+': 0.35,   # 35% = ~$53.6M (Supermax)
}

# 選秀權價值 (基於歷史數據分析)
DRAFT_PICK_VALUE = {
    1: 55.0, 2: 45.0, 3: 40.0, 4: 36.0, 5: 33.0,
    6: 30.0, 7: 28.0, 8: 26.0, 9: 24.0, 10: 22.0,
    11: 20.0, 12: 18.5, 13: 17.0, 14: 15.5, 15: 14.0,
    16: 13.0, 17: 12.0, 18: 11.0, 19: 10.0, 20: 9.5,
    21: 9.0, 22: 8.5, 23: 8.0, 24: 7.5, 25: 7.0,
    26: 6.5, 27: 6.0, 28: 5.5, 29: 5.0, 30: 4.5,
    # 次輪
    31: 4.0, 32: 3.8, 33: 3.6, 34: 3.4, 35: 3.2,
    36: 3.0, 37: 2.8, 38: 2.6, 39: 2.4, 40: 2.2,
    41: 2.0, 42: 1.9, 43: 1.8, 44: 1.7, 45: 1.6,
    46: 1.5, 47: 1.4, 48: 1.3, 49: 1.2, 50: 1.1,
    51: 1.0, 52: 0.9, 53: 0.8, 54: 0.7, 55: 0.6,
    56: 0.5, 57: 0.4, 58: 0.3,
}

# 合約類型定義
CONTRACT_TYPES = {
    'SUPERMAX': '超級頂薪',
    'MAX': '頂薪',
    'NEAR_MAX': '準頂薪',
    'HIGH_VALUE': '高薪',
    'MID_LEVEL': '中產',
    'ROLE_PLAYER': '角色球員',
    'ROOKIE_SCALE': '新秀合約',
    'ROOKIE_EXT': '新秀延長',
    'MINIMUM': '底薪',
    'TWO_WAY': '雙向合約',
}


class ContractModule:
    """合約分析模組"""
    
    def __init__(self, salary_cap: float = SALARY_CAP_2026):
        self.salary_cap = salary_cap
        
    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        主要分析入口
        
        新增欄位：
        - CONTRACT_TYPE: 合約類型
        - CONTRACT_TYPE_CN: 合約類型中文
        - YEARS_REMAINING: 推估剩餘年限
        - TOTAL_CONTRACT_VALUE: 推估合約總值
        - TRADE_RESTRICTIONS: 交易限制
        - TRADE_KICKER: 交易獎金條款
        - EXTENSION_ELIGIBLE: 是否可續約
        - CONTRACT_FLEXIBILITY: 合約彈性分數
        - SALARY_MATCH_RANGE: 薪資匹配範圍
        """
        df = df.copy()
        
        # 1. 合約類型分類
        contract_info = df.apply(self._classify_contract, axis=1)
        df['CONTRACT_TYPE'] = contract_info.apply(lambda x: x[0])
        df['CONTRACT_TYPE_CN'] = contract_info.apply(lambda x: x[1])
        
        # 2. 推估剩餘年限
        df['YEARS_REMAINING'] = df.apply(self._estimate_years_remaining, axis=1)
        
        # 3. 推估合約總值
        df['TOTAL_CONTRACT_VALUE'] = (
            df['SALARY_M'] * df['YEARS_REMAINING']
        ).round(2)
        
        # 4. 交易限制
        df['TRADE_RESTRICTIONS'] = df.apply(self._assess_trade_restrictions, axis=1)
        
        # 5. 交易獎金條款 (Trade Kicker)
        df['TRADE_KICKER_LIKELY'] = df.apply(self._has_trade_kicker, axis=1)
        
        # 6. 是否可續約
        df['EXTENSION_ELIGIBLE'] = df.apply(self._check_extension_eligible, axis=1)
        
        # 7. 合約彈性分數
        df['CONTRACT_FLEXIBILITY'] = df.apply(self._calculate_flexibility, axis=1)
        
        # 8. 薪資匹配範圍 (NBA CBA: 125% + $100K)
        df['SALARY_MATCH_MIN'] = ((df['SALARY_M'] - 0.1) / 1.25).clip(lower=0).round(2)
        df['SALARY_MATCH_MAX'] = (df['SALARY_M'] * 1.25 + 0.1).round(2)
        
        return df
    
    def _classify_contract(self, row: pd.Series) -> Tuple[str, str]:
        """分類合約類型"""
        salary_m = row.get('SALARY_M', 0)
        age = row.get('AGE', 27)
        
        if pd.isna(salary_m) or salary_m <= 0:
            return ('UNKNOWN', '未知')
        
        supermax_threshold = self.salary_cap * 0.35
        max_threshold = self.salary_cap * 0.30
        near_max_threshold = self.salary_cap * 0.25
        
        # 超級頂薪
        if salary_m >= supermax_threshold:
            return ('SUPERMAX', CONTRACT_TYPES['SUPERMAX'])
        
        # 頂薪
        if salary_m >= max_threshold:
            return ('MAX', CONTRACT_TYPES['MAX'])
        
        # 準頂薪
        if salary_m >= near_max_threshold:
            return ('NEAR_MAX', CONTRACT_TYPES['NEAR_MAX'])
        
        # 新秀合約 (年輕 + 特定薪資範圍)
        if age <= 24 and 1.5 <= salary_m <= 15:
            if salary_m <= 6:
                return ('ROOKIE_SCALE', CONTRACT_TYPES['ROOKIE_SCALE'])
            else:
                return ('ROOKIE_EXT', CONTRACT_TYPES['ROOKIE_EXT'])
        
        # 高薪
        if salary_m >= 20:
            return ('HIGH_VALUE', CONTRACT_TYPES['HIGH_VALUE'])
        
        # 中產等級
        if 10 <= salary_m < 20:
            return ('MID_LEVEL', CONTRACT_TYPES['MID_LEVEL'])
        
        # 角色球員
        if 3 <= salary_m < 10:
            return ('ROLE_PLAYER', CONTRACT_TYPES['ROLE_PLAYER'])
        
        # 底薪或雙向
        if salary_m < 2:
            return ('TWO_WAY', CONTRACT_TYPES['TWO_WAY'])
        
        return ('MINIMUM', CONTRACT_TYPES['MINIMUM'])
    
    def _estimate_years_remaining(self, row: pd.Series) -> int:
        """
        推估剩餘合約年限
        
        基於合約類型、年齡、薪資等因素推估
        """
        contract_type = row.get('CONTRACT_TYPE', 'UNKNOWN')
        age = row.get('AGE', 27)
        salary_m = row.get('SALARY_M', 0)
        
        # 新秀合約通常 2-4 年
        if contract_type == 'ROOKIE_SCALE':
            years_in_league = max(0, int(age) - 19)
            return max(1, 4 - years_in_league)
        
        # 新秀延長 4-5 年
        if contract_type == 'ROOKIE_EXT':
            return 4
        
        # 超級頂薪 4-5 年
        if contract_type == 'SUPERMAX':
            if age >= 33:
                return 2
            return 4
        
        # 頂薪 3-4 年
        if contract_type == 'MAX':
            if age >= 32:
                return 2
            return 3
        
        # 準頂薪 3-4 年
        if contract_type == 'NEAR_MAX':
            return 3
        
        # 高薪 2-4 年
        if contract_type == 'HIGH_VALUE':
            return 3
        
        # 中產 2-3 年
        if contract_type == 'MID_LEVEL':
            return 2
        
        # 角色球員 2-3 年
        if contract_type == 'ROLE_PLAYER':
            return 2
        
        # 底薪/雙向 1-2 年
        return 1
    
    def _assess_trade_restrictions(self, row: pd.Series) -> str:
        """評估交易限制"""
        restrictions = []
        
        contract_type = row.get('CONTRACT_TYPE', '')
        age = row.get('AGE', 27)
        salary_m = row.get('SALARY_M', 0)
        years_remaining = row.get('YEARS_REMAINING', 2)
        
        # No-Trade Clause (NTC) - 通常給資深超級巨星
        if contract_type == 'SUPERMAX' and age >= 30:
            restrictions.append('NTC')
        
        # 新秀延長 6 個月限制
        if contract_type == 'ROOKIE_EXT' and age <= 25:
            restrictions.append('ROOKIE_EXT_WAIT')
        
        # 簽約後 3 個月不可交易
        # (無法從數據判斷，標記高薪新簽約可能性)
        if contract_type in ['MAX', 'SUPERMAX'] and age <= 28:
            restrictions.append('POSSIBLE_3MO_WAIT')
        
        # 薪資匹配困難
        if salary_m >= 45:
            restrictions.append('HARD_TO_MATCH')
        elif salary_m >= 35:
            restrictions.append('DIFFICULT_TO_MATCH')
        
        return '|'.join(restrictions) if restrictions else 'NONE'
    
    def _has_trade_kicker(self, row: pd.Series) -> bool:
        """推測是否有交易獎金條款"""
        contract_type = row.get('CONTRACT_TYPE', '')
        salary_m = row.get('SALARY_M', 0)
        
        # 高薪合約通常有 Trade Kicker (最高 15%)
        return contract_type in ['SUPERMAX', 'MAX', 'NEAR_MAX'] and salary_m >= 25
    
    def _check_extension_eligible(self, row: pd.Series) -> str:
        """檢查是否可續約"""
        contract_type = row.get('CONTRACT_TYPE', '')
        age = row.get('AGE', 27)
        years_remaining = row.get('YEARS_REMAINING', 2)
        
        # 新秀合約第 3/4 年可延長
        if contract_type == 'ROOKIE_SCALE' and years_remaining <= 2:
            return 'ROOKIE_EXTENSION_ELIGIBLE'
        
        # 合約最後 1-2 年可延長
        if years_remaining <= 2:
            if age <= 30:
                return 'EXTENSION_ELIGIBLE'
            else:
                return 'EXTENSION_ELIGIBLE_LIMITED'
        
        return 'NOT_YET_ELIGIBLE'
    
    def _calculate_flexibility(self, row: pd.Series) -> float:
        """
        計算合約彈性分數 (0-100)
        
        考量：短約、低薪、無限制 = 高彈性
        """
        salary_m = row.get('SALARY_M', 0)
        years_remaining = row.get('YEARS_REMAINING', 2)
        restrictions = row.get('TRADE_RESTRICTIONS', 'NONE')
        
        score = 50.0
        
        # 薪資影響 (低薪 = 高彈性)
        if salary_m < 5:
            score += 25
        elif salary_m < 10:
            score += 15
        elif salary_m < 20:
            score += 5
        elif salary_m < 35:
            score -= 10
        else:
            score -= 25
        
        # 年限影響 (短約 = 高彈性)
        if years_remaining == 1:
            score += 20
        elif years_remaining == 2:
            score += 10
        elif years_remaining >= 4:
            score -= 15
        
        # 限制影響
        if 'NTC' in restrictions:
            score -= 30
        if 'HARD_TO_MATCH' in restrictions:
            score -= 20
        if 'DIFFICULT_TO_MATCH' in restrictions:
            score -= 10
        
        return max(0, min(100, round(score, 1)))
    
    def get_salary_matching_options(self, df: pd.DataFrame, 
                                    target_salary_m: float,
                                    team: str = None,
                                    max_players: int = 3) -> pd.DataFrame:
        """
        找出可用於薪資匹配的球員組合
        
        NBA CBA 規則：
        - 稅線以下：可接收 175% + $100K 或 $5M (取較大者)
        - 稅線以上：可接收 125% + $100K
        """
        candidates = df.copy()
        
        if team:
            candidates = candidates[candidates['TEAM_ABBREVIATION'] == team]
        
        # 計算匹配範圍
        min_match = (target_salary_m - 0.1) / 1.25
        max_match = target_salary_m * 1.25 + 0.1
        
        # 單一球員匹配
        single_match = candidates[
            (candidates['SALARY_M'] >= min_match) & 
            (candidates['SALARY_M'] <= max_match)
        ].copy()
        
        if len(single_match) > 0:
            single_match['MATCH_TYPE'] = 'SINGLE'
            return single_match.nlargest(10, 'CONTRACT_FLEXIBILITY')
        
        # 多球員組合 (簡化：只找 2 人組合)
        results = []
        candidates_sorted = candidates.sort_values('SALARY_M', ascending=False)
        
        for i, row1 in candidates_sorted.iterrows():
            remaining = target_salary_m - row1['SALARY_M']
            if remaining > 0:
                for j, row2 in candidates_sorted.iterrows():
                    if i != j:
                        combined = row1['SALARY_M'] + row2['SALARY_M']
                        if min_match <= combined <= max_match:
                            results.append({
                                'PLAYERS': f"{row1['PLAYER_NAME']} + {row2['PLAYER_NAME']}",
                                'COMBINED_SALARY': combined,
                                'MATCH_TYPE': 'COMBO_2'
                            })
                            if len(results) >= 5:
                                break
            if len(results) >= 5:
                break
        
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    @staticmethod
    def get_draft_pick_value(pick_number: int, 
                             protections: str = None,
                             years_out: int = 0) -> float:
        """
        計算選秀權價值
        
        參數：
        - pick_number: 選秀順位
        - protections: 保護條款 (e.g., "TOP_5", "TOP_10", "LOTTERY")
        - years_out: 幾年後的選秀權 (遠期價值遞減)
        """
        base_value = DRAFT_PICK_VALUE.get(pick_number, 0.5)
        
        # 保護條款折扣
        protection_discount = 1.0
        if protections:
            if 'TOP_3' in protections:
                protection_discount = 0.7
            elif 'TOP_5' in protections:
                protection_discount = 0.75
            elif 'TOP_10' in protections:
                protection_discount = 0.8
            elif 'LOTTERY' in protections:
                protection_discount = 0.85
        
        # 遠期選秀權折扣 (每年 -10%)
        future_discount = 0.9 ** years_out
        
        return round(base_value * protection_discount * future_discount, 1)
    
    def report(self, df: pd.DataFrame) -> str:
        """產生合約分析報告"""
        lines = []
        lines.append("=" * 70)
        lines.append("📜 合約模組分析報告")
        lines.append("=" * 70)
        
        # 合約類型分布
        lines.append("\n▸ 合約類型分布：")
        type_counts = df['CONTRACT_TYPE_CN'].value_counts()
        for ctype, count in type_counts.items():
            lines.append(f"  {ctype:12s}: {count:3d} 人")
        
        # 剩餘年限分布
        lines.append("\n▸ 剩餘年限分布：")
        years_counts = df['YEARS_REMAINING'].value_counts().sort_index()
        for years, count in years_counts.items():
            lines.append(f"  {years} 年: {count:3d} 人")
        
        # 最高合約彈性
        lines.append("\n▸ 合約彈性最高 Top 10 (易於交易)：")
        top_flex = df.nlargest(10, 'CONTRACT_FLEXIBILITY')
        for _, row in top_flex.iterrows():
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"彈性={row['CONTRACT_FLEXIBILITY']:5.1f}  "
                f"薪資=${row['SALARY_M']:5.1f}M  "
                f"剩餘={row['YEARS_REMAINING']}年"
            )
        
        # 最難交易的合約
        lines.append("\n▸ 最難交易的合約 (彈性最低)：")
        worst_flex = df.nsmallest(10, 'CONTRACT_FLEXIBILITY')
        for _, row in worst_flex.iterrows():
            restrictions = row.get('TRADE_RESTRICTIONS', 'NONE')
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"彈性={row['CONTRACT_FLEXIBILITY']:5.1f}  "
                f"薪資=${row['SALARY_M']:5.1f}M  "
                f"限制={restrictions}"
            )
        
        # 可續約球員
        lines.append("\n▸ 可續約的高價值球員：")
        extension_eligible = df[
            df['EXTENSION_ELIGIBLE'].str.contains('ELIGIBLE') &
            (df['TRADE_VALUE'] >= 60)
        ].nlargest(10, 'TRADE_VALUE')
        for _, row in extension_eligible.iterrows():
            lines.append(
                f"  {row['PLAYER_NAME']:25s} "
                f"交易價值={row['TRADE_VALUE']:5.1f}  "
                f"狀態={row['EXTENSION_ELIGIBLE']}"
            )
        
        return "\n".join(lines)