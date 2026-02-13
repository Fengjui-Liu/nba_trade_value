"""
AI 分析模組 (AI Analysis Module)
================================
整合 Claude API 提供智能球隊分析與交易建議

功能：
• 球隊陣容診斷
• 交易建議生成
• 補強方向分析
• 選秀策略建議
• 自然語言查詢
"""

import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from src.modules.ai_cache import TradeAICache
except ImportError:
    from ai_cache import TradeAICache


@dataclass
class TeamProfile:
    """球隊檔案"""
    team_code: str
    total_salary: float
    avg_age: float
    total_trade_value: float
    position_counts: Dict[str, int]
    style_counts: Dict[str, int]
    top_players: List[Dict]
    weaknesses: List[str]
    strengths: List[str]


class AIAnalysisModule:
    """AI 分析模組"""
    
    def __init__(self, api_key: str = None, ai_cache: TradeAICache = None):
        """
        初始化 AI 模組
        
        參數：
        - api_key: Anthropic API 金鑰 (可從環境變數讀取)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = "claude-sonnet-4-20250514"
        self.ai_cache = ai_cache or TradeAICache()

    @staticmethod
    def build_trade_signature(team_a_gives: List[str], team_b_gives: List[str]) -> str:
        a = "|".join(sorted(team_a_gives or []))
        b = "|".join(sorted(team_b_gives or []))
        return f"A:{a}__B:{b}"

    def get_trade_commentary(
        self,
        df: pd.DataFrame,
        team_a: str,
        team_a_gives: List[str],
        team_b: str,
        team_b_gives: List[str],
        rule_version: str,
        scoring_config_hash: str,
        use_ai: bool = False,
        response_length: str = "medium",
        token_mode: str = "standard",
    ) -> Dict[str, Any]:
        signature = self.build_trade_signature(team_a_gives, team_b_gives)
        cache_key = self.ai_cache.build_cache_key(rule_version, scoring_config_hash, signature)
        cached = self.ai_cache.get(cache_key)
        if cached:
            return {"text": cached.get("text", ""), "cache_hit": True, "cache_key": cache_key}

        # Deterministic local summary by default.
        summary = (
            f"{team_a} 送出 {', '.join(team_a_gives)}；"
            f"{team_b} 送出 {', '.join(team_b_gives)}。"
            f"模式={token_mode}/{response_length}。"
        )

        if use_ai and self.api_key:
            claude = ClaudeAnalysisEngine(self.api_key)
            if claude.is_available():
                summary = claude.simulate_trade_analysis(df, team_a, team_a_gives, team_b, team_b_gives)

        if response_length == "short":
            summary = summary[:240]
        elif response_length == "medium":
            summary = summary[:800]

        self.ai_cache.set(cache_key, {"text": summary})
        return {"text": summary, "cache_hit": False, "cache_key": cache_key}
        
    def analyze_team(self, df: pd.DataFrame, team: str) -> Dict[str, Any]:
        """
        全面分析球隊
        
        回傳包含多個面向的分析結果
        """
        team_df = df[df['TEAM_ABBREVIATION'] == team]
        
        if len(team_df) == 0:
            return {"error": f"找不到球隊: {team}"}
        
        # 建立球隊檔案
        profile = self._build_team_profile(df, team_df, team)
        
        # 執行各項分析
        result = {
            "team": team,
            "profile": self._profile_to_dict(profile),
            "roster_diagnosis": self._diagnose_roster(profile, team_df),
            "trade_suggestions": self._generate_trade_suggestions(df, team_df, profile),
            "draft_strategy": self._generate_draft_strategy(profile, team_df),
            "championship_window": self._assess_championship_window(profile, team_df),
        }
        
        return result
    
    def _build_team_profile(self, full_df: pd.DataFrame, 
                            team_df: pd.DataFrame, team: str) -> TeamProfile:
        """建立球隊檔案"""
        
        # 基本統計
        total_salary = team_df['SALARY_M'].sum()
        avg_age = team_df['AGE'].mean()
        total_trade_value = team_df['TRADE_VALUE'].sum()
        
        # 位置分布
        positions = team_df['POSITIONS'].str.split('/').explode()
        position_counts = positions.value_counts().to_dict()
        
        # 打法風格分布
        style_counts = team_df['PLAY_STYLE_CN'].value_counts().to_dict()
        
        # 頂級球員
        top_players = team_df.nlargest(5, 'TRADE_VALUE')[
            ['PLAYER_NAME', 'AGE', 'TRADE_VALUE', 'SALARY_M', 'PLAY_STYLE_CN']
        ].to_dict('records')
        
        # 分析優劣勢
        weaknesses = []
        strengths = []
        
        # 位置深度檢查
        for pos in ['PG', 'SG', 'SF', 'PF', 'C']:
            count = position_counts.get(pos, 0)
            if count < 2:
                weaknesses.append(f"{pos} 位置深度不足")
            elif count >= 4:
                strengths.append(f"{pos} 位置深度充足")
        
        # 打法風格檢查
        essential_styles = ['組織者型', '護框中鋒型', '3D 球員型']
        for style in essential_styles:
            if style not in style_counts:
                weaknesses.append(f"缺乏 {style}")
        
        if '多元得分手型' in style_counts:
            strengths.append("擁有多元得分手")
        if '地板指揮官型' in style_counts:
            strengths.append("擁有頂級組織者")
        
        # 薪資結構檢查
        if total_salary > 170:
            weaknesses.append("超過豪華稅線，操作空間有限")
        elif total_salary < 120:
            strengths.append("薪資空間充裕")
        
        # 年齡結構檢查
        if avg_age > 30:
            weaknesses.append("陣容老化，需考慮重建")
        elif avg_age < 26:
            strengths.append("年輕有潛力")
        
        return TeamProfile(
            team_code=team,
            total_salary=total_salary,
            avg_age=avg_age,
            total_trade_value=total_trade_value,
            position_counts=position_counts,
            style_counts=style_counts,
            top_players=top_players,
            weaknesses=weaknesses,
            strengths=strengths
        )
    
    def _profile_to_dict(self, profile: TeamProfile) -> Dict:
        """將 TeamProfile 轉為字典"""
        return {
            "team_code": profile.team_code,
            "total_salary": round(profile.total_salary, 1),
            "avg_age": round(profile.avg_age, 1),
            "total_trade_value": round(profile.total_trade_value, 1),
            "position_counts": profile.position_counts,
            "style_counts": profile.style_counts,
            "top_players": profile.top_players,
            "weaknesses": profile.weaknesses,
            "strengths": profile.strengths,
        }
    
    def _diagnose_roster(self, profile: TeamProfile, 
                         team_df: pd.DataFrame) -> Dict[str, Any]:
        """陣容診斷"""
        
        diagnosis = {
            "overall_grade": self._calculate_roster_grade(profile, team_df),
            "salary_structure": self._analyze_salary_structure(team_df),
            "age_structure": self._analyze_age_structure(team_df),
            "position_balance": self._analyze_position_balance(profile),
            "style_diversity": self._analyze_style_diversity(profile),
            "star_power": self._analyze_star_power(team_df),
            "depth_assessment": self._analyze_depth(team_df),
        }
        
        return diagnosis
    
    def _calculate_roster_grade(self, profile: TeamProfile, 
                                team_df: pd.DataFrame) -> str:
        """計算陣容評級"""
        score = 0
        
        # 總交易價值 (最高 40 分)
        score += min(40, profile.total_trade_value / 15)
        
        # 明星球員數量 (最高 20 分)
        stars = len(team_df[team_df['TRADE_VALUE_TIER'].isin(['UNTOUCHABLE', 'FRANCHISE', 'ALL_STAR'])])
        score += min(20, stars * 5)
        
        # 陣容深度 (最高 20 分)
        rotation_players = len(team_df[team_df['TRADE_VALUE'] >= 30])
        score += min(20, rotation_players * 2)
        
        # 弱點扣分
        score -= len(profile.weaknesses) * 3
        
        # 優勢加分
        score += len(profile.strengths) * 2
        
        if score >= 80:
            return "A+"
        elif score >= 70:
            return "A"
        elif score >= 60:
            return "B+"
        elif score >= 50:
            return "B"
        elif score >= 40:
            return "C+"
        elif score >= 30:
            return "C"
        else:
            return "D"
    
    def _analyze_salary_structure(self, team_df: pd.DataFrame) -> Dict:
        """分析薪資結構"""
        total = team_df['SALARY_M'].sum()
        
        # 薪資分層
        tiers = {
            'max_contracts': len(team_df[team_df['SALARY_M'] >= 35]),
            'mid_level': len(team_df[(team_df['SALARY_M'] >= 10) & (team_df['SALARY_M'] < 35)]),
            'role_players': len(team_df[(team_df['SALARY_M'] >= 3) & (team_df['SALARY_M'] < 10)]),
            'minimum': len(team_df[team_df['SALARY_M'] < 3]),
        }
        
        # 薪資集中度
        top_3_salary = team_df.nlargest(3, 'SALARY_M')['SALARY_M'].sum()
        concentration = top_3_salary / total if total > 0 else 0
        
        return {
            "total_salary_m": round(total, 1),
            "cap_status": "超過豪華稅" if total > 170 else "接近稅線" if total > 140 else "有空間",
            "salary_tiers": tiers,
            "top_3_concentration": round(concentration * 100, 1),
            "assessment": "薪資結構健康" if concentration < 0.5 else "薪資過於集中"
        }
    
    def _analyze_age_structure(self, team_df: pd.DataFrame) -> Dict:
        """分析年齡結構"""
        avg_age = team_df['AGE'].mean()
        
        age_groups = {
            'young_core': len(team_df[team_df['AGE'] <= 24]),
            'prime': len(team_df[(team_df['AGE'] > 24) & (team_df['AGE'] <= 30)]),
            'veteran': len(team_df[team_df['AGE'] > 30]),
        }
        
        # 判斷球隊階段
        if age_groups['young_core'] >= 5:
            phase = "重建期"
        elif age_groups['prime'] >= 5:
            phase = "爭冠期"
        elif age_groups['veteran'] >= 4:
            phase = "老化期"
        else:
            phase = "過渡期"
        
        return {
            "avg_age": round(avg_age, 1),
            "age_groups": age_groups,
            "team_phase": phase,
            "championship_window": "開放" if avg_age < 29 and age_groups['prime'] >= 3 else "有限"
        }
    
    def _analyze_position_balance(self, profile: TeamProfile) -> Dict:
        """分析位置平衡"""
        ideal = {'PG': 3, 'SG': 3, 'SF': 3, 'PF': 3, 'C': 2}
        
        balance_score = 0
        gaps = []
        surpluses = []
        
        for pos, ideal_count in ideal.items():
            actual = profile.position_counts.get(pos, 0)
            diff = actual - ideal_count
            
            if diff < -1:
                gaps.append(f"{pos} (差 {abs(diff)} 人)")
                balance_score -= 10
            elif diff > 1:
                surpluses.append(f"{pos} (多 {diff} 人)")
                balance_score -= 5
            else:
                balance_score += 10
        
        return {
            "balance_score": balance_score,
            "position_gaps": gaps,
            "position_surpluses": surpluses,
            "assessment": "位置均衡" if balance_score >= 30 else "需要調整"
        }
    
    def _analyze_style_diversity(self, profile: TeamProfile) -> Dict:
        """分析打法多樣性"""
        essential = ['組織者型', '護框中鋒型', '3D 球員型']
        valuable = ['多元得分手型', '雙向側翼型', '空間型大個子']
        
        has_essential = [s for s in essential if s in profile.style_counts]
        has_valuable = [s for s in valuable if s in profile.style_counts]
        
        missing_essential = [s for s in essential if s not in profile.style_counts]
        
        return {
            "diversity_score": len(profile.style_counts),
            "essential_styles": has_essential,
            "missing_essential": missing_essential,
            "valuable_styles": has_valuable,
            "assessment": "陣容完整" if len(missing_essential) == 0 else "需要補強"
        }
    
    def _analyze_star_power(self, team_df: pd.DataFrame) -> Dict:
        """分析明星戰力"""
        untouchables = team_df[team_df['TRADE_VALUE_TIER'] == 'UNTOUCHABLE']
        franchise = team_df[team_df['TRADE_VALUE_TIER'] == 'FRANCHISE']
        all_stars = team_df[team_df['TRADE_VALUE_TIER'] == 'ALL_STAR']
        
        top_player = team_df.nlargest(1, 'TRADE_VALUE').iloc[0] if len(team_df) > 0 else None
        
        return {
            "untouchable_count": len(untouchables),
            "franchise_count": len(franchise),
            "all_star_count": len(all_stars),
            "best_player": top_player['PLAYER_NAME'] if top_player is not None else None,
            "best_player_value": round(top_player['TRADE_VALUE'], 1) if top_player is not None else None,
            "star_power_rating": "頂級" if len(untouchables) > 0 else "強勁" if len(franchise) > 0 else "中等"
        }
    
    def _analyze_depth(self, team_df: pd.DataFrame) -> Dict:
        """分析板凳深度"""
        starters = team_df.nlargest(5, 'TRADE_VALUE')
        bench = team_df[~team_df['PLAYER_NAME'].isin(starters['PLAYER_NAME'])]
        
        starter_value = starters['TRADE_VALUE'].mean()
        bench_value = bench['TRADE_VALUE'].mean() if len(bench) > 0 else 0
        
        depth_gap = starter_value - bench_value
        
        return {
            "starter_avg_value": round(starter_value, 1),
            "bench_avg_value": round(bench_value, 1),
            "depth_gap": round(depth_gap, 1),
            "bench_players": len(bench),
            "assessment": "深度充足" if depth_gap < 25 and len(bench) >= 5 else "深度不足"
        }
    
    def _generate_trade_suggestions(self, full_df: pd.DataFrame,
                                    team_df: pd.DataFrame,
                                    profile: TeamProfile) -> Dict:
        """生成交易建議"""
        
        suggestions = {
            "trade_away": [],
            "trade_targets": [],
            "salary_dump_candidates": [],
        }
        
        # 找出負資產 (應該交易出去的)
        bad_contracts = team_df[team_df['SURPLUS_VALUE_M'] < -10].sort_values('SURPLUS_VALUE_M')
        for _, row in bad_contracts.iterrows():
            suggestions['trade_away'].append({
                "player": row['PLAYER_NAME'],
                "salary_m": round(row['SALARY_M'], 1),
                "surplus_m": round(row['SURPLUS_VALUE_M'], 1),
                "reason": "負資產合約"
            })
        
        # 找出適合追求的目標
        # 基於缺口找目標
        for weakness in profile.weaknesses:
            if '組織者' in weakness:
                targets = full_df[
                    (full_df['TEAM_ABBREVIATION'] != profile.team_code) &
                    (full_df['PLAY_STYLE_CN'].str.contains('組織')) &
                    (full_df['SURPLUS_VALUE_M'] > 0)
                ].nlargest(3, 'TRADE_VALUE')
            elif '護框' in weakness:
                targets = full_df[
                    (full_df['TEAM_ABBREVIATION'] != profile.team_code) &
                    (full_df['PLAY_STYLE_CN'].str.contains('護框|中鋒')) &
                    (full_df['SURPLUS_VALUE_M'] > 0)
                ].nlargest(3, 'TRADE_VALUE')
            elif '3D' in weakness:
                targets = full_df[
                    (full_df['TEAM_ABBREVIATION'] != profile.team_code) &
                    (full_df['PLAY_STYLE_CN'].str.contains('3D')) &
                    (full_df['SURPLUS_VALUE_M'] > 0)
                ].nlargest(3, 'TRADE_VALUE')
            else:
                continue
            
            for _, row in targets.iterrows():
                suggestions['trade_targets'].append({
                    "player": row['PLAYER_NAME'],
                    "team": row['TEAM_ABBREVIATION'],
                    "salary_m": round(row['SALARY_M'], 1),
                    "trade_value": round(row['TRADE_VALUE'], 1),
                    "fills_need": weakness,
                    "style": row['PLAY_STYLE_CN']
                })
        
        return suggestions
    
    def _generate_draft_strategy(self, profile: TeamProfile,
                                 team_df: pd.DataFrame) -> Dict:
        """生成選秀策略"""
        
        young_players = len(team_df[team_df['AGE'] <= 24])
        
        # 判斷策略類型
        if young_players >= 4:
            strategy_type = "即戰力優先"
            description = "已有足夠年輕核心，應選擇能立即貢獻的球員"
        elif profile.avg_age > 30:
            strategy_type = "重建導向"
            description = "陣容老化，應選擇高潛力新秀進行重建"
        else:
            strategy_type = "BPA (最佳球員優先)"
            description = "保持彈性，選擇最佳可得球員"
        
        # 位置優先順序
        position_priority = []
        for pos in ['PG', 'SG', 'SF', 'PF', 'C']:
            count = profile.position_counts.get(pos, 0)
            if count < 2:
                position_priority.append({"position": pos, "priority": "高"})
            elif count < 3:
                position_priority.append({"position": pos, "priority": "中"})
        
        return {
            "strategy_type": strategy_type,
            "description": description,
            "position_priority": position_priority,
            "recommended_archetypes": self._get_recommended_archetypes(profile)
        }
    
    def _get_recommended_archetypes(self, profile: TeamProfile) -> List[str]:
        """推薦應該選擇的球員類型"""
        archetypes = []
        
        if '組織者型' not in profile.style_counts:
            archetypes.append("控球後衛 - 組織能力強")
        if '護框中鋒型' not in profile.style_counts:
            archetypes.append("中鋒 - 護框能力強")
        if '3D 球員型' not in profile.style_counts:
            archetypes.append("側翼 - 三分與防守兼具")
        if '多元得分手型' not in profile.style_counts:
            archetypes.append("得分手 - 多樣化得分能力")
        
        return archetypes[:3] if archetypes else ["最佳可得球員"]
    
    def _assess_championship_window(self, profile: TeamProfile,
                                    team_df: pd.DataFrame) -> Dict:
        """評估爭冠窗口"""
        
        # 計算爭冠指數
        score = 0
        
        # 明星球員
        stars = len(team_df[team_df['TRADE_VALUE'] >= 70])
        score += stars * 20
        
        # 深度
        rotation = len(team_df[team_df['TRADE_VALUE'] >= 40])
        score += rotation * 5
        
        # 年齡適中
        if 26 <= profile.avg_age <= 30:
            score += 20
        elif profile.avg_age < 26:
            score += 10
        
        # 陣容完整度
        score -= len(profile.weaknesses) * 10
        score += len(profile.strengths) * 5
        
        # 判斷窗口狀態
        if score >= 80:
            window_status = "黃金窗口"
            years_remaining = "1-3 年"
            recommendation = "全力衝擊總冠軍"
        elif score >= 60:
            window_status = "競爭窗口"
            years_remaining = "2-4 年"
            recommendation = "可做適度補強"
        elif score >= 40:
            window_status = "發展窗口"
            years_remaining = "3-5 年"
            recommendation = "培養年輕核心"
        else:
            window_status = "重建期"
            years_remaining = "5+ 年"
            recommendation = "累積資產，為未來做準備"
        
        return {
            "championship_score": score,
            "window_status": window_status,
            "estimated_window": years_remaining,
            "recommendation": recommendation,
            "key_factors": {
                "star_power": stars,
                "roster_depth": rotation,
                "age_profile": round(profile.avg_age, 1)
            }
        }
    
    def generate_natural_language_report(self, analysis: Dict) -> str:
        """
        將分析結果轉換為自然語言報告
        
        可以用 Claude API 增強此功能
        """
        team = analysis['team']
        profile = analysis['profile']
        diagnosis = analysis['roster_diagnosis']
        trades = analysis['trade_suggestions']
        draft = analysis['draft_strategy']
        window = analysis['championship_window']
        
        report = []
        
        # 標題
        report.append(f"# {team} 球隊分析報告\n")
        
        # 總覽
        report.append("## 📊 球隊總覽\n")
        report.append(f"- **陣容評級**: {diagnosis['overall_grade']}")
        report.append(f"- **總薪資**: ${profile['total_salary']}M")
        report.append(f"- **平均年齡**: {profile['avg_age']} 歲")
        report.append(f"- **爭冠窗口**: {window['window_status']}\n")
        
        # 優勢
        if profile['strengths']:
            report.append("### ✅ 優勢")
            for s in profile['strengths']:
                report.append(f"- {s}")
            report.append("")
        
        # 劣勢
        if profile['weaknesses']:
            report.append("### ⚠️ 需要改善")
            for w in profile['weaknesses']:
                report.append(f"- {w}")
            report.append("")
        
        # 交易建議
        report.append("## 🔄 交易建議\n")
        
        if trades['trade_away']:
            report.append("### 建議交易出去")
            for p in trades['trade_away'][:3]:
                report.append(f"- **{p['player']}**: 薪資 ${p['salary_m']}M, 剩餘價值 ${p['surplus_m']}M")
            report.append("")
        
        if trades['trade_targets']:
            report.append("### 建議追求目標")
            for p in trades['trade_targets'][:5]:
                report.append(
                    f"- **{p['player']}** ({p['team']}): "
                    f"價值 {p['trade_value']}, 薪資 ${p['salary_m']}M - {p['fills_need']}"
                )
            report.append("")
        
        # 選秀策略
        report.append("## 🎯 選秀策略\n")
        report.append(f"**策略類型**: {draft['strategy_type']}")
        report.append(f"\n{draft['description']}\n")
        
        if draft['position_priority']:
            report.append("### 位置優先順序")
            for pos in draft['position_priority']:
                report.append(f"- {pos['position']}: {pos['priority']}優先")
        
        # 結論
        report.append("\n## 📝 結論\n")
        report.append(f"**{window['recommendation']}**\n")
        report.append(f"預估競爭窗口: {window['estimated_window']}")
        
        return '\n'.join(report)
    
    def query(self, df: pd.DataFrame, question: str, use_ai: bool = True) -> str:
        """
        自然語言查詢

        參數：
        - df: 球員數據
        - question: 用戶問題
        - use_ai: 是否使用 Claude API（若可用）

        範例問題：
        - "誰是性價比最高的控球後衛？"
        - "哪支球隊最需要補強中鋒？"
        - "30 歲以下最佳的交易目標是誰？"
        - "OKC 應該追求哪些球員？"
        - "分析一下湖人隊的陣容"
        """
        # 嘗試使用 Claude API
        if use_ai and self.api_key:
            claude = ClaudeAnalysisEngine(self.api_key)
            if claude.is_available():
                return claude.answer_trade_question(df, question)

        # 本地規則式查詢（備用）
        question_lower = question.lower()

        # 簡單的關鍵字匹配
        if '性價比' in question or '剩餘價值' in question:
            if '控球' in question or 'PG' in question.upper():
                result = df[df['POSITIONS'].str.contains('PG', na=False)].nlargest(10, 'SURPLUS_VALUE_M')
                return self._format_player_list(result, "性價比最高的控球後衛")
            elif '中鋒' in question or 'C' in question.upper():
                result = df[df['POSITIONS'].str.contains('C', na=False)].nlargest(10, 'SURPLUS_VALUE_M')
                return self._format_player_list(result, "性價比最高的中鋒")
            elif '側翼' in question or 'SF' in question.upper():
                result = df[df['POSITIONS'].str.contains('SF', na=False)].nlargest(10, 'SURPLUS_VALUE_M')
                return self._format_player_list(result, "性價比最高的側翼")
            else:
                result = df.nlargest(10, 'SURPLUS_VALUE_M')
                return self._format_player_list(result, "性價比最高的球員")

        if '交易價值' in question and '最高' in question:
            result = df.nlargest(10, 'TRADE_VALUE')
            return self._format_player_list(result, "交易價值最高的球員")

        if '年輕' in question or '25歲以下' in question:
            result = df[df['AGE'] <= 25].nlargest(10, 'TRADE_VALUE')
            return self._format_player_list(result, "25歲以下最佳球員")

        if '老將' in question or '30歲以上' in question:
            result = df[df['AGE'] >= 30].nlargest(10, 'TRADE_VALUE')
            return self._format_player_list(result, "30歲以上最佳老將")

        if '低薪' in question or '便宜' in question:
            result = df[df['SALARY_M'] < 10].nlargest(10, 'TRADE_VALUE')
            return self._format_player_list(result, "低薪高價值球員（薪資 < $10M）")

        if '新秀' in question:
            result = df[df['AGE'] <= 23].nlargest(10, 'TRADE_VALUE')
            return self._format_player_list(result, "最佳年輕新秀（23歲以下）")

        # 球隊相關查詢
        teams = df['TEAM_ABBREVIATION'].unique()
        for team in teams:
            if team.lower() in question_lower:
                team_df = df[df['TEAM_ABBREVIATION'] == team]
                return self._format_team_summary(team_df, team)

        return "💡 提示：我可以回答關於球員性價比、交易價值、特定球隊分析等問題。\n\n" + \
               "範例：\n" + \
               "• 誰是性價比最高的控球後衛？\n" + \
               "• 25歲以下交易價值最高的球員？\n" + \
               "• OKC 的陣容分析\n\n" + \
               "如需更智能的分析，請設置 ANTHROPIC_API_KEY 環境變數。"

    def _format_team_summary(self, team_df: pd.DataFrame, team: str) -> str:
        """格式化球隊摘要"""
        lines = [f"## {team} 球隊摘要\n"]

        total_salary = team_df['SALARY_M'].sum()
        avg_age = team_df['AGE'].mean()
        total_value = team_df['TRADE_VALUE'].sum()

        lines.append(f"**總薪資**: ${total_salary:.1f}M")
        lines.append(f"**平均年齡**: {avg_age:.1f} 歲")
        lines.append(f"**總交易價值**: {total_value:.1f}\n")

        lines.append("### 陣容（按交易價值排序）")
        for _, row in team_df.nlargest(10, 'TRADE_VALUE').iterrows():
            lines.append(
                f"• **{row['PLAYER_NAME']}** - "
                f"年齡 {row['AGE']:.0f}, "
                f"薪資 ${row['SALARY_M']:.1f}M, "
                f"交易價值 {row['TRADE_VALUE']:.1f}"
            )

        return '\n'.join(lines)
    
    def _format_player_list(self, df: pd.DataFrame, title: str) -> str:
        """格式化球員列表"""
        lines = [f"## {title}\n"]
        
        for i, (_, row) in enumerate(df.iterrows(), 1):
            lines.append(
                f"{i}. **{row['PLAYER_NAME']}** ({row['TEAM_ABBREVIATION']})\n"
                f"   - 年齡: {row['AGE']:.0f}, 交易價值: {row['TRADE_VALUE']:.1f}\n"
                f"   - 薪資: ${row['SALARY_M']:.1f}M, 剩餘價值: ${row['SURPLUS_VALUE_M']:+.1f}M\n"
            )
        
        return '\n'.join(lines)


# Ollama 本地 LLM 整合 (免費)
class OllamaAnalysisEngine:
    """
    Ollama 本地 LLM 引擎（完全免費）

    適合 8GB RAM 的輕量模型：
    - qwen2.5:3b (~2GB) - 中文佳，推薦
    - llama3.2:3b (~2GB)
    - phi3:mini (~2GB)
    - gemma2:2b (~1.5GB)

    使用步驟：
    1. 安裝: https://ollama.com/download
    2. 下載模型: ollama pull qwen2.5:3b
    3. 啟動服務: ollama serve
    """

    def __init__(self, model: str = "qwen2.5:3b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def is_available(self) -> bool:
        """檢查 Ollama 服務是否運行"""
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except:
            return False

    def has_model(self, model: str = None) -> bool:
        """檢查是否已安裝指定模型"""
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get('models', [])
                target = model or self.model
                return any(target in m.get('name', '') for m in models)
            return False
        except:
            return False

    def chat(self, prompt: str, system: str = None) -> str:
        """與 Ollama 對話"""
        import requests

        if not self.is_available():
            return "❌ Ollama 未啟動。請先執行 `ollama serve`"

        if not self.has_model():
            return f"❌ 模型 {self.model} 未安裝。請執行 `ollama pull {self.model}`"

        try:
            full_prompt = prompt
            if system:
                full_prompt = f"{system}\n\n{prompt}"

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False
                },
                timeout=120
            )

            if response.status_code == 200:
                return response.json().get("response", "無回應")
            else:
                return f"❌ Ollama 錯誤: {response.status_code}"
        except Exception as e:
            return f"❌ 錯誤: {str(e)}"

    def analyze_team(self, df: pd.DataFrame, team: str, question: str = None) -> str:
        """使用 Ollama 分析球隊"""
        team_df = df[df['TEAM_ABBREVIATION'] == team]
        context = self._prepare_context(team_df)

        system = "你是一位專業的 NBA 數據分析師，精通球員交易、薪資帽規則、球隊建構策略。請用繁體中文回答，提供具體、可執行的建議。"

        if question:
            prompt = f"以下是 {team} 隊的球員數據：\n\n{context}\n\n問題：{question}"
        else:
            prompt = f"""以下是 {team} 隊的球員數據：

{context}

請提供完整的球隊分析報告，包含：
1. 陣容優劣勢評估
2. 具體的交易建議
3. 補強優先順序
4. 爭冠窗口評估"""

        return self.chat(prompt, system)

    def answer_question(self, df: pd.DataFrame, question: str) -> str:
        """回答關於 NBA 的問題"""
        top_players = df.nlargest(30, 'TRADE_VALUE')[
            ['PLAYER_NAME', 'TEAM_ABBREVIATION', 'AGE', 'PTS', 'REB', 'AST',
             'TRADE_VALUE', 'SALARY_M', 'SURPLUS_VALUE_M']
        ].to_string(index=False)

        system = "你是一位專業的 NBA 數據分析師。請用繁體中文回答，根據提供的數據給出具體分析。"

        prompt = f"""以下是 NBA 交易價值前 30 名球員的數據：

{top_players}

用戶問題：{question}

請根據數據提供專業分析。"""

        return self.chat(prompt, system)

    def _prepare_context(self, team_df: pd.DataFrame) -> str:
        """準備上下文數據"""
        context_cols = ['PLAYER_NAME', 'AGE', 'PTS', 'REB', 'AST',
                       'TRADE_VALUE', 'SALARY_M', 'SURPLUS_VALUE_M']
        available_cols = [c for c in context_cols if c in team_df.columns]
        return team_df[available_cols].to_string(index=False)


# Claude API 整合 (進階功能)
class ClaudeAnalysisEngine:
    """
    Claude API 整合引擎

    用於更複雜的自然語言分析
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = "claude-sonnet-4-20250514"
        self._client = None

    @property
    def client(self):
        """延遲初始化 Anthropic 客戶端"""
        if self._client is None and self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                print("請安裝 anthropic: pip install anthropic")
                return None
        return self._client

    def is_available(self) -> bool:
        """檢查 API 是否可用"""
        return self.api_key is not None and self.client is not None

    def chat(self, messages: List[Dict], system: str = None) -> str:
        """
        與 Claude 對話

        參數：
        - messages: [{"role": "user", "content": "..."}]
        - system: 系統提示詞
        """
        if not self.is_available():
            return "❌ Claude API 未設置。請設置 ANTHROPIC_API_KEY 環境變數。"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system or "你是一位專業的 NBA 數據分析師，精通球員交易、薪資帽規則、球隊建構策略。請用繁體中文回答。",
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            return f"❌ API 錯誤: {str(e)}"

    def analyze_with_claude(self, df: pd.DataFrame, team: str,
                            question: str = None) -> str:
        """
        使用 Claude API 進行深度分析
        """
        if not self.is_available():
            return "❌ 未設置 API 金鑰。請設置 ANTHROPIC_API_KEY 環境變數。"

        # 準備上下文數據
        team_df = df[df['TEAM_ABBREVIATION'] == team]
        context = self._prepare_context(team_df)
        full_league_summary = self._prepare_league_summary(df)

        # 建構 prompt
        if question:
            user_message = f"""以下是 {team} 隊的球員數據：

{context}

聯盟概況：
{full_league_summary}

問題：{question}

請提供專業、具體、可執行的建議。"""
        else:
            user_message = f"""以下是 {team} 隊的球員數據：

{context}

聯盟概況：
{full_league_summary}

請提供完整的球隊分析報告，包含：
1. 陣容優劣勢評估
2. 具體的交易建議（含潛在交易對象）
3. 補強優先順序
4. 爭冠窗口評估與建議策略"""

        return self.chat([{"role": "user", "content": user_message}])

    def answer_trade_question(self, df: pd.DataFrame, question: str) -> str:
        """
        回答關於交易的自然語言問題
        """
        if not self.is_available():
            return "❌ 未設置 API 金鑰。請設置 ANTHROPIC_API_KEY 環境變數。"

        # 準備精簡的聯盟數據
        summary = self._prepare_league_summary(df)
        top_players = df.nlargest(50, 'TRADE_VALUE')[
            ['PLAYER_NAME', 'TEAM_ABBREVIATION', 'AGE', 'PTS', 'REB', 'AST',
             'TRADE_VALUE', 'SALARY_M', 'SURPLUS_VALUE_M', 'PLAY_STYLE_CN']
        ].to_string(index=False)

        user_message = f"""以下是 NBA 聯盟的數據摘要：

{summary}

交易價值前 50 名球員：
{top_players}

用戶問題：{question}

請根據數據提供專業分析和具體建議。如果問題涉及特定球員或球隊，請引用相關數據。"""

        return self.chat([{"role": "user", "content": user_message}])

    def simulate_trade_analysis(self, df: pd.DataFrame,
                                 team_a: str, team_a_gives: List[str],
                                 team_b: str, team_b_gives: List[str]) -> str:
        """
        AI 輔助交易分析
        """
        if not self.is_available():
            return "❌ 未設置 API 金鑰。"

        # 取得交易涉及的球員數據
        all_players = team_a_gives + team_b_gives
        trade_players = df[df['PLAYER_NAME'].isin(all_players)]

        if len(trade_players) == 0:
            return "❌ 找不到指定的球員"

        players_data = trade_players[
            ['PLAYER_NAME', 'TEAM_ABBREVIATION', 'AGE', 'PTS', 'REB', 'AST',
             'TRADE_VALUE', 'SALARY_M', 'SURPLUS_VALUE_M', 'PLAY_STYLE_CN',
             'CONTRACT_TYPE_CN', 'YEARS_REMAINING']
        ].to_string(index=False)

        # 取得雙方球隊陣容
        team_a_roster = df[df['TEAM_ABBREVIATION'] == team_a][
            ['PLAYER_NAME', 'AGE', 'TRADE_VALUE', 'SALARY_M', 'PLAY_STYLE_CN']
        ].to_string(index=False)

        team_b_roster = df[df['TEAM_ABBREVIATION'] == team_b][
            ['PLAYER_NAME', 'AGE', 'TRADE_VALUE', 'SALARY_M', 'PLAY_STYLE_CN']
        ].to_string(index=False)

        user_message = f"""分析以下交易提案：

{team_a} 送出：{', '.join(team_a_gives)}
{team_b} 送出：{', '.join(team_b_gives)}

交易涉及的球員數據：
{players_data}

{team_a} 目前陣容：
{team_a_roster}

{team_b} 目前陣容：
{team_b_roster}

請分析：
1. 交易是否公平？雙方價值差異
2. 對 {team_a} 的影響（優缺點）
3. 對 {team_b} 的影響（優缺點）
4. 薪資匹配是否可行？
5. 你的最終建議（這交易應該發生嗎？）"""

        return self.chat([{"role": "user", "content": user_message}])

    def _prepare_context(self, team_df: pd.DataFrame) -> str:
        """準備上下文數據"""
        context_cols = ['PLAYER_NAME', 'AGE', 'PTS', 'REB', 'AST', 'STL', 'BLK',
                       'TRADE_VALUE', 'SALARY_M', 'SURPLUS_VALUE_M',
                       'PLAY_STYLE_CN', 'CONTRACT_TYPE_CN']
        available_cols = [c for c in context_cols if c in team_df.columns]
        return team_df[available_cols].to_string(index=False)

    def _prepare_league_summary(self, df: pd.DataFrame) -> str:
        """準備聯盟概況"""
        total_players = len(df)
        avg_salary = df['SALARY_M'].mean()
        avg_age = df['AGE'].mean()

        # 各等級人數
        tier_counts = df['TRADE_VALUE_TIER'].value_counts().to_dict()

        # 各隊數量
        team_counts = df['TEAM_ABBREVIATION'].value_counts()

        summary = f"""
球員總數：{total_players}
平均薪資：${avg_salary:.1f}M
平均年齡：{avg_age:.1f}
交易等級分布：{tier_counts}
資料涵蓋球隊：{len(team_counts)} 隊
"""
        return summary


if __name__ == "__main__":
    # 測試
    import os
    
    # 載入數據
    data_path = "data/processed/trade_value_full.csv"
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        
        # 測試 AI 分析
        ai = AIAnalysisModule()
        
        # 分析雷霆隊
        result = ai.analyze_team(df, 'OKC')
        
        # 生成報告
        report = ai.generate_natural_language_report(result)
        print(report)
