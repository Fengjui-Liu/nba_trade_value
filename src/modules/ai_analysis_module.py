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
    
    def __init__(self, api_key: str = None):
        """
        初始化 AI 模組
        
        參數：
        - api_key: Anthropic API 金鑰 (可從環境變數讀取)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = "claude-sonnet-4-20250514"
        
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
    
    def query(self, df: pd.DataFrame, question: str) -> str:
        """
        自然語言查詢 (可整合 Claude API)
        
        範例問題：
        - "誰是性價比最高的控球後衛？"
        - "哪支球隊最需要補強中鋒？"
        - "30 歲以下最佳的交易目標是誰？"
        """
        question_lower = question.lower()
        
        # 簡單的關鍵字匹配 (可用 Claude API 增強)
        if '性價比' in question or '剩餘價值' in question:
            if '控球' in question or 'PG' in question.upper():
                result = df[df['POSITIONS'].str.contains('PG', na=False)].nlargest(10, 'SURPLUS_VALUE_M')
                return self._format_player_list(result, "性價比最高的控球後衛")
            else:
                result = df.nlargest(10, 'SURPLUS_VALUE_M')
                return self._format_player_list(result, "性價比最高的球員")
        
        if '交易價值' in question and '最高' in question:
            result = df.nlargest(10, 'TRADE_VALUE')
            return self._format_player_list(result, "交易價值最高的球員")
        
        if '年輕' in question or '25歲以下' in question:
            result = df[df['AGE'] <= 25].nlargest(10, 'TRADE_VALUE')
            return self._format_player_list(result, "25歲以下最佳球員")
        
        return "抱歉，我無法理解您的問題。請嘗試更具體的查詢。"
    
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


# Claude API 整合 (進階功能)
class ClaudeAnalysisEngine:
    """
    Claude API 整合引擎
    
    用於更複雜的自然語言分析
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.base_url = "https://api.anthropic.com/v1/messages"
        
    def analyze_with_claude(self, df: pd.DataFrame, team: str, 
                            question: str = None) -> str:
        """
        使用 Claude API 進行深度分析
        
        需要設置 ANTHROPIC_API_KEY 環境變數
        """
        if not self.api_key:
            return "未設置 API 金鑰，使用本地分析模式"
        
        # 準備上下文數據
        team_df = df[df['TEAM_ABBREVIATION'] == team]
        context = self._prepare_context(team_df)
        
        # 建構 prompt
        if question:
            prompt = f"""你是一位 NBA 專業分析師。根據以下球隊數據，回答問題。

球隊數據：
{context}

問題：{question}

請提供專業、具體的分析。"""
        else:
            prompt = f"""你是一位 NBA 專業分析師。根據以下球隊數據，提供完整的球隊分析報告。

球隊數據：
{context}

請分析：
1. 陣容優劣勢
2. 交易建議
3. 補強方向
4. 爭冠窗口評估"""
        
        # 呼叫 Claude API (需要實際實作)
        # response = self._call_claude_api(prompt)
        
        # 暫時返回提示訊息
        return "Claude API 整合功能開發中。請設置 ANTHROPIC_API_KEY 環境變數。"
    
    def _prepare_context(self, team_df: pd.DataFrame) -> str:
        """準備上下文數據"""
        context_cols = ['PLAYER_NAME', 'AGE', 'PTS', 'REB', 'AST', 
                       'TRADE_VALUE', 'SALARY_M', 'PLAY_STYLE_CN']
        
        return team_df[context_cols].to_string(index=False)


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