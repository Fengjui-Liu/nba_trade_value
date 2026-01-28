"""
NBA 交易價值儀表板
==================
使用 Streamlit 建立互動式分析介面

功能：
• 球員搜尋與比較
• 交易模擬器
• 球隊分析
• AI 智能建議
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys

# 加入專案路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.trade_value_engine import TradeValueEngine
from modules.contract_module import ContractModule

# 頁面配置
st.set_page_config(
    page_title="NBA 交易價值分析系統",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
        text-align: center;
        padding: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .player-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
    .trade-tier-untouchable { color: #FFD700; font-weight: bold; }
    .trade-tier-franchise { color: #C0C0C0; font-weight: bold; }
    .trade-tier-allstar { color: #CD7F32; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    """載入數據"""
    data_path = "data/processed/trade_value_full.csv"
    if os.path.exists(data_path):
        return pd.read_csv(data_path)
    
    # 備用路徑
    alt_path = "../data/processed/trade_value_full.csv"
    if os.path.exists(alt_path):
        return pd.read_csv(alt_path)
    
    st.error("找不到數據檔案！請先執行 main.py 產生數據。")
    return None


def render_header():
    """渲染標題"""
    st.markdown('<p class="main-header">🏀 NBA 交易價值分析系統</p>', unsafe_allow_html=True)
    st.markdown("---")


def render_sidebar(df: pd.DataFrame):
    """渲染側邊欄"""
    st.sidebar.header("🔧 篩選條件")
    
    # 球隊篩選
    teams = ['全部'] + sorted(df['TEAM_ABBREVIATION'].unique().tolist())
    selected_team = st.sidebar.selectbox("球隊", teams)
    
    # 位置篩選
    positions = ['全部', 'PG', 'SG', 'SF', 'PF', 'C']
    selected_position = st.sidebar.selectbox("位置", positions)
    
    # 年齡範圍
    age_range = st.sidebar.slider("年齡範圍", 19, 42, (19, 35))
    
    # 薪資範圍
    salary_range = st.sidebar.slider("薪資範圍 ($M)", 0, 60, (0, 60))
    
    # 交易等級
    tiers = ['全部'] + df['TRADE_VALUE_TIER'].unique().tolist()
    selected_tier = st.sidebar.selectbox("交易等級", tiers)
    
    # 套用篩選
    filtered = df.copy()
    
    if selected_team != '全部':
        filtered = filtered[filtered['TEAM_ABBREVIATION'] == selected_team]
    
    if selected_position != '全部':
        filtered = filtered[filtered['POSITIONS'].str.contains(selected_position, na=False)]
    
    filtered = filtered[
        (filtered['AGE'] >= age_range[0]) & 
        (filtered['AGE'] <= age_range[1])
    ]
    
    filtered = filtered[
        (filtered['SALARY_M'] >= salary_range[0]) & 
        (filtered['SALARY_M'] <= salary_range[1])
    ]
    
    if selected_tier != '全部':
        filtered = filtered[filtered['TRADE_VALUE_TIER'] == selected_tier]
    
    st.sidebar.markdown("---")
    st.sidebar.metric("篩選結果", f"{len(filtered)} 名球員")
    
    return filtered


def render_overview(df: pd.DataFrame):
    """渲染總覽頁面"""
    st.header("📊 總覽")
    
    # 關鍵指標
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("總球員數", len(df))
    with col2:
        avg_value = df['TRADE_VALUE'].mean()
        st.metric("平均交易價值", f"{avg_value:.1f}")
    with col3:
        total_salary = df['SALARY_M'].sum()
        st.metric("總薪資", f"${total_salary:.1f}M")
    with col4:
        avg_surplus = df['SURPLUS_VALUE_M'].mean()
        st.metric("平均剩餘價值", f"${avg_surplus:+.1f}M")
    
    st.markdown("---")
    
    # 圖表區
    col1, col2 = st.columns(2)
    
    with col1:
        # 交易等級分布
        tier_order = ['UNTOUCHABLE', 'FRANCHISE', 'ALL_STAR', 
                      'QUALITY_STARTER', 'ROTATION', 'TRADEABLE']
        tier_counts = df['TRADE_VALUE_TIER'].value_counts().reindex(tier_order).fillna(0)
        
        fig = px.bar(
            x=tier_counts.index,
            y=tier_counts.values,
            color=tier_counts.index,
            color_discrete_sequence=px.colors.qualitative.Set2,
            title="交易等級分布"
        )
        fig.update_layout(showlegend=False, xaxis_title="等級", yaxis_title="人數")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # 打法風格分布
        style_counts = df['PLAY_STYLE_CN'].value_counts().head(10)
        
        fig = px.pie(
            values=style_counts.values,
            names=style_counts.index,
            title="打法風格分布",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 交易價值 vs 薪資散點圖
    st.subheader("交易價值 vs 薪資分析")
    
    fig = px.scatter(
        df,
        x='SALARY_M',
        y='TRADE_VALUE',
        color='TRADE_VALUE_TIER',
        size='PTS',
        hover_name='PLAYER_NAME',
        hover_data=['AGE', 'TEAM_ABBREVIATION', 'SURPLUS_VALUE_M'],
        title="交易價值 vs 薪資 (氣泡大小 = 得分)",
        color_discrete_sequence=px.colors.qualitative.Set1
    )
    fig.update_layout(
        xaxis_title="薪資 ($M)",
        yaxis_title="交易價值",
        height=500
    )
    
    # 加入對角線 (價值 = 薪資的參考線)
    fig.add_trace(go.Scatter(
        x=[0, 60],
        y=[0, 100],
        mode='lines',
        line=dict(dash='dash', color='gray'),
        name='參考線'
    ))
    
    st.plotly_chart(fig, use_container_width=True)


def render_player_search(df: pd.DataFrame):
    """渲染球員搜尋頁面"""
    st.header("🔍 球員搜尋與比較")
    
    # 搜尋框
    search_term = st.text_input("搜尋球員名稱")
    
    if search_term:
        matches = df[df['PLAYER_NAME'].str.contains(search_term, case=False, na=False)]
        
        if len(matches) > 0:
            st.write(f"找到 {len(matches)} 名球員")
            
            # 顯示搜尋結果
            display_cols = ['PLAYER_NAME', 'TEAM_ABBREVIATION', 'AGE', 
                           'PTS', 'REB', 'AST', 'TRADE_VALUE', 
                           'SALARY_M', 'SURPLUS_VALUE_M', 'TRADE_VALUE_TIER']
            st.dataframe(matches[display_cols].sort_values('TRADE_VALUE', ascending=False))
        else:
            st.warning("找不到符合的球員")
    
    st.markdown("---")
    
    # 球員比較
    st.subheader("📊 球員比較")
    
    player_names = df['PLAYER_NAME'].tolist()
    selected_players = st.multiselect(
        "選擇要比較的球員 (最多 5 名)",
        player_names,
        max_selections=5
    )
    
    if len(selected_players) >= 2:
        compare_df = df[df['PLAYER_NAME'].isin(selected_players)]
        
        # 雷達圖
        categories = ['PTS', 'REB', 'AST', 'STL', 'BLK']
        
        fig = go.Figure()
        
        for _, row in compare_df.iterrows():
            values = [row[cat] for cat in categories]
            # 標準化到 0-100
            max_vals = df[categories].max()
            normalized = [v / max_vals[cat] * 100 for v, cat in zip(values, categories)]
            normalized.append(normalized[0])  # 閉合
            
            fig.add_trace(go.Scatterpolar(
                r=normalized,
                theta=categories + [categories[0]],
                fill='toself',
                name=row['PLAYER_NAME']
            ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            title="球員能力雷達圖"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 詳細比較表
        compare_cols = ['PLAYER_NAME', 'AGE', 'PTS', 'REB', 'AST', 
                       'PIE', 'TS_PCT', 'NET_RATING',
                       'TRADE_VALUE', 'SALARY_M', 'SURPLUS_VALUE_M',
                       'PLAY_STYLE_CN']
        st.dataframe(compare_df[compare_cols])


def render_trade_simulator(df: pd.DataFrame):
    """渲染交易模擬器"""
    st.header("🔄 交易模擬器")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🅰️ A 隊送出")
        team_a_players = st.multiselect(
            "選擇 A 隊送出的球員",
            df['PLAYER_NAME'].tolist(),
            key="team_a"
        )
    
    with col2:
        st.subheader("🅱️ B 隊送出")
        team_b_players = st.multiselect(
            "選擇 B 隊送出的球員",
            df['PLAYER_NAME'].tolist(),
            key="team_b"
        )
    
    if team_a_players and team_b_players:
        engine = TradeValueEngine()
        result = engine.simulate_trade(df, team_a_players, team_b_players)
        
        st.markdown("---")
        st.subheader("📋 交易分析結果")
        
        # 薪資匹配檢查
        if result['salary_match']:
            st.success("✅ 薪資匹配成功！")
        else:
            st.error(f"❌ 薪資匹配失敗！差距: ${result['salary_diff_m']:.1f}M")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "A 隊送出總價值",
                f"{result['team_a_package']['total_trade_value']:.1f}",
                f"${result['team_a_package']['total_salary_m']:.1f}M"
            )
        
        with col2:
            st.metric(
                "B 隊送出總價值",
                f"{result['team_b_package']['total_trade_value']:.1f}",
                f"${result['team_b_package']['total_salary_m']:.1f}M"
            )
        
        with col3:
            diff = result['value_difference']
            st.metric(
                "價值差異",
                f"{abs(diff):.1f}",
                result['verdict']
            )
        
        # 詳細球員資訊
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**A 隊送出球員：**")
            for p in result['team_a_package']['details']:
                st.write(f"• {p['PLAYER_NAME']}: 價值 {p['TRADE_VALUE']:.1f}, ${p['SALARY_M']:.1f}M")
        
        with col2:
            st.write("**B 隊送出球員：**")
            for p in result['team_b_package']['details']:
                st.write(f"• {p['PLAYER_NAME']}: 價值 {p['TRADE_VALUE']:.1f}, ${p['SALARY_M']:.1f}M")


def render_team_analysis(df: pd.DataFrame):
    """渲染球隊分析頁面"""
    st.header("🏟️ 球隊分析")
    
    teams = sorted(df['TEAM_ABBREVIATION'].unique().tolist())
    selected_team = st.selectbox("選擇球隊", teams)
    
    team_df = df[df['TEAM_ABBREVIATION'] == selected_team]
    
    if len(team_df) > 0:
        # 球隊總覽
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("球員數", len(team_df))
        with col2:
            total_salary = team_df['SALARY_M'].sum()
            st.metric("總薪資", f"${total_salary:.1f}M")
        with col3:
            avg_age = team_df['AGE'].mean()
            st.metric("平均年齡", f"{avg_age:.1f}")
        with col4:
            total_value = team_df['TRADE_VALUE'].sum()
            st.metric("總交易價值", f"{total_value:.1f}")
        
        st.markdown("---")
        
        # 陣容列表
        st.subheader("📋 陣容")
        roster_cols = ['PLAYER_NAME', 'AGE', 'POSITIONS', 'PTS', 'REB', 'AST',
                      'TRADE_VALUE', 'SALARY_M', 'SURPLUS_VALUE_M', 'PLAY_STYLE_CN']
        st.dataframe(
            team_df[roster_cols].sort_values('SALARY_M', ascending=False),
            use_container_width=True
        )
        
        # 打法風格分布
        col1, col2 = st.columns(2)
        
        with col1:
            style_counts = team_df['PLAY_STYLE_CN'].value_counts()
            fig = px.pie(
                values=style_counts.values,
                names=style_counts.index,
                title="打法風格分布"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 位置分布
            positions = team_df['POSITIONS'].str.split('/').explode()
            pos_counts = positions.value_counts()
            fig = px.bar(
                x=pos_counts.index,
                y=pos_counts.values,
                title="位置分布"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 薪資結構
        st.subheader("💰 薪資結構")
        fig = px.bar(
            team_df.sort_values('SALARY_M', ascending=True),
            x='SALARY_M',
            y='PLAYER_NAME',
            orientation='h',
            color='TRADE_VALUE_TIER',
            title="球員薪資分布"
        )
        fig.update_layout(height=max(400, len(team_df) * 30))
        st.plotly_chart(fig, use_container_width=True)


def render_ai_analysis(df: pd.DataFrame):
    """渲染 AI 分析頁面"""
    st.header("🤖 AI 智能分析")
    
    st.info("此功能整合 Claude API 提供深度分析建議")
    
    teams = sorted(df['TEAM_ABBREVIATION'].unique().tolist())
    selected_team = st.selectbox("選擇要分析的球隊", teams, key="ai_team")
    
    analysis_type = st.radio(
        "分析類型",
        ["陣容診斷", "交易建議", "補強方向", "選秀策略"]
    )
    
    if st.button("🚀 開始 AI 分析", type="primary"):
        team_df = df[df['TEAM_ABBREVIATION'] == selected_team]
        
        with st.spinner("AI 分析中..."):
            # 這裡會呼叫 AI 分析模組
            analysis_result = generate_ai_analysis(
                df, team_df, selected_team, analysis_type
            )
            
            st.markdown("---")
            st.subheader("📋 分析報告")
            st.markdown(analysis_result)


def generate_ai_analysis(full_df: pd.DataFrame, team_df: pd.DataFrame, 
                         team: str, analysis_type: str) -> str:
    """
    產生 AI 分析報告 (本地版本，不需 API)
    
    實際部署時可替換為 Claude API 呼叫
    """
    # 基於規則的分析
    report = []
    
    # 球隊基本資訊
    total_salary = team_df['SALARY_M'].sum()
    avg_age = team_df['AGE'].mean()
    total_value = team_df['TRADE_VALUE'].sum()
    avg_surplus = team_df['SURPLUS_VALUE_M'].mean()
    
    if analysis_type == "陣容診斷":
        report.append(f"## {team} 陣容診斷報告\n")
        
        # 薪資結構分析
        report.append("### 💰 薪資結構")
        if total_salary > 170:
            report.append(f"- ⚠️ 總薪資 ${total_salary:.1f}M，已超過豪華稅線")
        elif total_salary > 140:
            report.append(f"- ⚠️ 總薪資 ${total_salary:.1f}M，接近薪資帽")
        else:
            report.append(f"- ✅ 總薪資 ${total_salary:.1f}M，有操作空間")
        
        # 年齡結構
        report.append("\n### 👥 年齡結構")
        if avg_age > 30:
            report.append(f"- ⚠️ 平均年齡 {avg_age:.1f} 歲，陣容偏老，需考慮重建")
        elif avg_age < 25:
            report.append(f"- 🌟 平均年齡 {avg_age:.1f} 歲，年輕有潛力")
        else:
            report.append(f"- ✅ 平均年齡 {avg_age:.1f} 歲，正值巔峰期")
        
        # 位置分析
        report.append("\n### 🏀 位置分析")
        positions = team_df['POSITIONS'].str.split('/').explode()
        pos_counts = positions.value_counts()
        
        for pos in ['PG', 'SG', 'SF', 'PF', 'C']:
            count = pos_counts.get(pos, 0)
            if count < 2:
                report.append(f"- ⚠️ {pos} 位置深度不足 ({count} 人)")
            elif count >= 4:
                report.append(f"- 📈 {pos} 位置充足 ({count} 人)")
        
        # 打法風格
        report.append("\n### 🎯 打法風格")
        style_counts = team_df['PLAY_STYLE_CN'].value_counts()
        
        has_playmaker = '組織者型' in style_counts.index or '地板指揮官型' in style_counts.index
        has_rim_protector = '護框中鋒型' in style_counts.index
        has_three_d = '3D 球員型' in style_counts.index
        
        if not has_playmaker:
            report.append("- ⚠️ 缺乏組織者，進攻發起點不足")
        if not has_rim_protector:
            report.append("- ⚠️ 缺乏護框中鋒，禁區防守有漏洞")
        if not has_three_d:
            report.append("- ⚠️ 缺乏 3D 球員，側翼深度不足")
    
    elif analysis_type == "交易建議":
        report.append(f"## {team} 交易建議報告\n")
        
        # 找出可交易的負資產
        bad_contracts = team_df[team_df['SURPLUS_VALUE_M'] < -10].sort_values('SURPLUS_VALUE_M')
        if len(bad_contracts) > 0:
            report.append("### 🔴 建議交易出的負資產合約")
            for _, row in bad_contracts.iterrows():
                report.append(
                    f"- **{row['PLAYER_NAME']}**: 薪資 ${row['SALARY_M']:.1f}M, "
                    f"剩餘價值 ${row['SURPLUS_VALUE_M']:.1f}M"
                )
        
        # 找出高價值交易目標
        report.append("\n### 🟢 適合追求的交易目標")
        
        # 找出全聯盟性價比高且符合需求的球員
        positions = team_df['POSITIONS'].str.split('/').explode()
        pos_counts = positions.value_counts()
        weak_positions = [pos for pos in ['PG', 'SG', 'SF', 'PF', 'C'] 
                         if pos_counts.get(pos, 0) < 2]
        
        if weak_positions:
            targets = full_df[
                (full_df['TEAM_ABBREVIATION'] != team) &
                (full_df['SURPLUS_VALUE_M'] > 5) &
                (full_df['POSITIONS'].str.contains('|'.join(weak_positions), na=False))
            ].nlargest(5, 'TRADE_VALUE')
            
            if len(targets) > 0:
                for _, row in targets.iterrows():
                    report.append(
                        f"- **{row['PLAYER_NAME']}** ({row['TEAM_ABBREVIATION']}): "
                        f"價值 {row['TRADE_VALUE']:.1f}, 薪資 ${row['SALARY_M']:.1f}M, "
                        f"風格: {row['PLAY_STYLE_CN']}"
                    )
    
    elif analysis_type == "補強方向":
        report.append(f"## {team} 補強方向分析\n")
        
        # 分析缺口
        style_counts = team_df['PLAY_STYLE_CN'].value_counts()
        all_styles = ['組織者型', '得分後衛型', '3D 球員型', '雙向側翼型', 
                     '護框中鋒型', '空間型大個子', '禁區猛獸型', '地板指揮官型',
                     '多元得分手型']
        
        missing_styles = [s for s in all_styles if s not in style_counts.index]
        
        report.append("### 🎯 需要補強的角色類型")
        for style in missing_styles[:3]:
            report.append(f"- {style}")
            
            # 推薦球員
            targets = full_df[
                (full_df['TEAM_ABBREVIATION'] != team) &
                (full_df['PLAY_STYLE_CN'] == style) &
                (full_df['SURPLUS_VALUE_M'] > 0)
            ].nlargest(3, 'TRADE_VALUE')
            
            if len(targets) > 0:
                for _, row in targets.iterrows():
                    report.append(
                        f"  - {row['PLAYER_NAME']} ({row['TEAM_ABBREVIATION']}): "
                        f"${row['SALARY_M']:.1f}M"
                    )
    
    elif analysis_type == "選秀策略":
        report.append(f"## {team} 選秀策略建議\n")
        
        # 根據陣容年齡和缺口建議
        young_players = len(team_df[team_df['AGE'] <= 24])
        
        if young_players < 3:
            report.append("### 📊 策略：發展導向")
            report.append("- 年輕球員不足，建議選擇高潛力新秀")
            report.append("- 優先考慮 BPA (Best Player Available)")
        else:
            report.append("### 📊 策略：即戰力導向")
            report.append("- 已有足夠年輕核心，可選擇即戰力")
            report.append("- 優先填補位置需求")
        
        # 位置需求
        positions = team_df['POSITIONS'].str.split('/').explode()
        pos_counts = positions.value_counts()
        
        report.append("\n### 🏀 選秀位置優先順序")
        priority = []
        for pos in ['PG', 'SG', 'SF', 'PF', 'C']:
            count = pos_counts.get(pos, 0)
            if count < 2:
                priority.append((pos, "高優先"))
            elif count < 3:
                priority.append((pos, "中優先"))
        
        for pos, pri in priority:
            report.append(f"- {pos}: {pri}")
    
    return '\n'.join(report)


def main():
    """主程式"""
    render_header()
    
    # 載入數據
    df = load_data()
    
    if df is None:
        st.stop()
    
    # 側邊欄篩選
    filtered_df = render_sidebar(df)
    
    # 頁面選擇
    page = st.sidebar.radio(
        "📑 頁面",
        ["總覽", "球員搜尋", "交易模擬", "球隊分析", "AI 分析"]
    )
    
    # 渲染對應頁面
    if page == "總覽":
        render_overview(filtered_df)
    elif page == "球員搜尋":
        render_player_search(filtered_df)
    elif page == "交易模擬":
        render_trade_simulator(df)  # 交易模擬使用完整數據
    elif page == "球隊分析":
        render_team_analysis(df)
    elif page == "AI 分析":
        render_ai_analysis(df)
    
    # 頁腳
    st.sidebar.markdown("---")
    st.sidebar.markdown("🏀 NBA Trade Value System v1.0")
    st.sidebar.markdown("📊 數據更新: 2024-25 賽季")


if __name__ == "__main__":
    main()