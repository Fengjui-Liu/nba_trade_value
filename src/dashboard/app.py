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

# 載入環境變數
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

    /* Trade Machine 專用樣式 */
    .team-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px 10px 0 0;
        text-align: center;
        font-size: 1.3rem;
        font-weight: bold;
    }
    .team-roster {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0 0 10px 10px;
        max-height: 400px;
        overflow-y: auto;
    }
    .player-row {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem 1rem;
        border-bottom: 1px solid #dee2e6;
        cursor: pointer;
        transition: background 0.2s;
    }
    .player-row:hover {
        background: #e9ecef;
    }
    .player-in-trade {
        background: #d4edda !important;
        border-left: 3px solid #28a745;
    }
    .trade-package {
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .salary-ok { color: #28a745; font-weight: bold; }
    .salary-fail { color: #dc3545; font-weight: bold; }
    .trade-value-bar {
        height: 30px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .surplus-positive { color: #28a745; }
    .surplus-negative { color: #dc3545; }
    .draft-pick-card {
        background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);
        color: #000;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        font-weight: bold;
    }
    .trade-result-box {
        background: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .trade-fair { border-color: #28a745; }
    .trade-unfair { border-color: #dc3545; }
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
    st.markdown('<p class="main-header">NBA 交易價值分析系統</p>', unsafe_allow_html=True)
    st.markdown("---")


def render_sidebar(df: pd.DataFrame):
    """渲染側邊欄"""
    st.sidebar.header("篩選條件")
    
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
    st.header("總覽")
    
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
    st.header("球員搜尋與比較")
    
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
    st.subheader("球員比較")
    
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
    """渲染專業交易模擬器"""
    st.markdown("## NBA Trade Machine")
    st.markdown("*模擬真實交易，分析價值與薪資匹配*")

    # 初始化交易狀態
    if 'trade_team_a' not in st.session_state:
        st.session_state.trade_team_a = None
    if 'trade_team_b' not in st.session_state:
        st.session_state.trade_team_b = None
    if 'team_a_selected' not in st.session_state:
        st.session_state.team_a_selected = []
    if 'team_b_selected' not in st.session_state:
        st.session_state.team_b_selected = []
    if 'draft_picks_a' not in st.session_state:
        st.session_state.draft_picks_a = []
    if 'draft_picks_b' not in st.session_state:
        st.session_state.draft_picks_b = []

    # 球隊選擇
    teams = sorted(df['TEAM_ABBREVIATION'].unique().tolist())

    col1, col_mid, col2 = st.columns([2, 1, 2])

    with col1:
        team_a = st.selectbox("選擇 A 隊", teams, key="select_team_a",
                              index=teams.index(st.session_state.trade_team_a) if st.session_state.trade_team_a in teams else 0)
        st.session_state.trade_team_a = team_a

    with col_mid:
        st.markdown("<div style='text-align: center; padding-top: 2rem; font-size: 2rem;'>⇄</div>", unsafe_allow_html=True)

    with col2:
        # 預設選擇不同球隊
        default_b = 1 if teams[0] == team_a else 0
        team_b = st.selectbox("選擇 B 隊", teams, key="select_team_b", index=default_b)
        st.session_state.trade_team_b = team_b

    if team_a == team_b:
        st.warning("請選擇兩支不同的球隊")
        return

    st.markdown("---")

    # 取得兩隊陣容
    team_a_roster = df[df['TEAM_ABBREVIATION'] == team_a].sort_values('SALARY_M', ascending=False)
    team_b_roster = df[df['TEAM_ABBREVIATION'] == team_b].sort_values('SALARY_M', ascending=False)

    # 顯示兩隊陣容
    col1, col2 = st.columns(2)

    with col1:
        render_team_trade_panel(team_a, team_a_roster, "a", df)

    with col2:
        render_team_trade_panel(team_b, team_b_roster, "b", df)

    # 選秀籤區域
    st.markdown("---")
    st.markdown("### 加入選秀籤")

    pick_col1, pick_col2 = st.columns(2)

    with pick_col1:
        st.markdown(f"**{team_a} 送出選秀籤**")
        picks_a = st.multiselect(
            "選擇選秀籤",
            get_team_draft_picks(team_a),
            key="picks_a",
            default=st.session_state.draft_picks_a
        )
        st.session_state.draft_picks_a = picks_a

    with pick_col2:
        st.markdown(f"**{team_b} 送出選秀籤**")
        picks_b = st.multiselect(
            "選擇選秀籤",
            get_team_draft_picks(team_b),
            key="picks_b",
            default=st.session_state.draft_picks_b
        )
        st.session_state.draft_picks_b = picks_b

    # 交易分析
    st.markdown("---")

    # 取得選中的球員
    team_a_players = st.session_state.get('team_a_selected', [])
    team_b_players = st.session_state.get('team_b_selected', [])

    if team_a_players or team_b_players:
        render_trade_analysis(df, team_a, team_a_players, picks_a,
                             team_b, team_b_players, picks_b)
    else:
        st.info("從上方選擇要交易的球員開始模擬")

    # 重置按鈕
    if st.button("重置交易", type="secondary"):
        st.session_state.team_a_selected = []
        st.session_state.team_b_selected = []
        st.session_state.draft_picks_a = []
        st.session_state.draft_picks_b = []
        st.rerun()


def get_team_draft_picks(team: str):
    """取得球隊擁有的選秀籤（簡化版 - 實際應從資料庫讀取）"""
    # 基本上每隊有自己的籤，這裡列出已知的交易情況
    # 資料來源應該要定期更新

    # 已送出選秀籤的球隊（2025年1月資料）
    traded_picks = {
        'LAL': ['2025 1輪', '2027 1輪'],  # 送給 NOP (AD交易)
        'BKN': ['2025 1輪', '2026 1輪', '2027 1輪'],  # 送給多隊
        'UTA': [],  # 收到很多籤
        'HOU': [],  # 收到很多籤
        'OKC': [],  # 收到很多籤
        'PHX': ['2025 1輪', '2027 1輪', '2029 1輪'],  # KD交易
    }

    picks = []
    team_traded = traded_picks.get(team, [])

    for year in range(2025, 2029):
        for round_num in [1, 2]:
            pick_name = f"{year} {round_num}輪"
            if pick_name not in team_traded:
                picks.append(f"{team} {year} {round_num}輪")

    return picks


def get_pick_value(pick_str: str) -> float:
    """計算選秀籤的預估價值"""
    # 格式: "TEAM 2025 1輪" 或 "TEAM 2025 2輪"
    parts = pick_str.split()
    if len(parts) < 3:
        return 10

    year = int(parts[1])
    round_type = parts[2]

    # 基礎價值
    base = 25 if "1輪" in round_type else 5

    # 年份折扣（越遠的籤價值越低）
    current_year = 2025
    year_discount = max(0.5, 1 - (year - current_year) * 0.1)

    return base * year_discount


def render_team_trade_panel(team: str, roster: pd.DataFrame, side: str, full_df: pd.DataFrame):
    """渲染球隊交易面板"""
    # 取得球隊顏色
    team_colors = {
        'LAL': '#552583', 'BOS': '#007A33', 'MIA': '#98002E', 'GSW': '#006BB6',
        'PHX': '#1D1160', 'MIL': '#00471B', 'DEN': '#0E2240', 'MEM': '#5D76A9',
        'OKC': '#007AC1', 'CLE': '#6F263D', 'SAC': '#5A2D81', 'NYK': '#006BB6',
        'PHI': '#006BB6', 'DAL': '#00538C', 'MIN': '#0C2340', 'NOP': '#0C2340',
        'ATL': '#E03A3E', 'CHI': '#CE1141', 'CHA': '#1D1160', 'DET': '#C8102E',
        'IND': '#002D62', 'TOR': '#CE1141', 'WAS': '#002B5C', 'ORL': '#0077C0',
        'POR': '#E03A3E', 'SAS': '#C4CED4', 'LAC': '#C8102E', 'HOU': '#CE1141'
    }
    bg_color = team_colors.get(team, '#1a1a2e')

    st.markdown(f"""
    <div style='background: {bg_color}; color: white; padding: 1rem;
                border-radius: 10px 10px 0 0; text-align: center;'>
        <h3 style='margin: 0;'>{team}</h3>
        <small>總薪資: ${roster['SALARY_M'].sum():.1f}M</small>
    </div>
    """, unsafe_allow_html=True)

    # 球員選擇
    selected_key = f"team_{side}_selected"
    current_selected = st.session_state.get(selected_key, [])

    # 建立球員選項（顯示薪資和合約年限）
    player_options = []
    player_map = {}
    for _, row in roster.iterrows():
        years = int(row.get('YEARS_REMAINING', 1)) if pd.notna(row.get('YEARS_REMAINING')) else 1
        contract_type = row.get('CONTRACT_TYPE_CN', '')
        label = f"{row['PLAYER_NAME']} - ${row['SALARY_M']:.1f}M / {years}年"
        player_options.append(label)
        player_map[label] = row['PLAYER_NAME']

    # 反向映射當前選中的球員
    current_labels = []
    for p in current_selected:
        if p in roster['PLAYER_NAME'].values:
            row = roster[roster['PLAYER_NAME']==p].iloc[0]
            years = int(row.get('YEARS_REMAINING', 1)) if pd.notna(row.get('YEARS_REMAINING')) else 1
            label = f"{p} - ${row['SALARY_M']:.1f}M / {years}年"
            current_labels.append(label)

    # 用 multiselect 選擇球員
    selected_labels = st.multiselect(
        f"選擇 {team} 送出的球員",
        player_options,
        default=current_labels,
        key=f"select_{side}",
    )

    # 轉換回球員名稱
    selected = [player_map[label] for label in selected_labels]
    st.session_state[selected_key] = selected

    # 顯示已選球員的薪資總計
    if selected:
        selected_df = roster[roster['PLAYER_NAME'].isin(selected)]
        total_selected_salary = selected_df['SALARY_M'].sum()
        st.success(f"已選 {len(selected)} 人，薪資: ${total_selected_salary:.1f}M")

    # 顯示陣容表格（含合約資訊）
    display_cols = ['PLAYER_NAME', 'AGE', 'SALARY_M', 'YEARS_REMAINING', 'CONTRACT_TYPE_CN', 'TRADE_VALUE']
    available_cols = [c for c in display_cols if c in roster.columns]
    display_roster = roster[available_cols].copy()

    # 重新命名欄位
    col_names = {
        'PLAYER_NAME': '球員',
        'AGE': '年齡',
        'SALARY_M': '薪資(M)',
        'YEARS_REMAINING': '剩餘年',
        'CONTRACT_TYPE_CN': '合約類型',
        'TRADE_VALUE': '價值'
    }
    display_roster = display_roster.rename(columns=col_names)

    # 標記已選擇的球員
    display_roster[''] = display_roster['球員'].apply(lambda x: '*' if x in selected else '')

    # 格式化數字
    display_roster['薪資(M)'] = display_roster['薪資(M)'].apply(lambda x: f"${x:.1f}")
    display_roster['價值'] = display_roster['價值'].apply(lambda x: f"{x:.0f}")
    if '剩餘年' in display_roster.columns:
        display_roster['剩餘年'] = display_roster['剩餘年'].apply(lambda x: f"{int(x)}" if pd.notna(x) else "-")

    # 重新排序欄位
    final_cols = ['', '球員', '年齡', '薪資(M)']
    if '剩餘年' in display_roster.columns:
        final_cols.append('剩餘年')
    if '合約類型' in display_roster.columns:
        final_cols.append('合約類型')
    final_cols.append('價值')
    display_roster = display_roster[final_cols]

    st.dataframe(
        display_roster,
        use_container_width=True,
        hide_index=True,
        height=300
    )


def render_trade_analysis(df: pd.DataFrame,
                          team_a: str, players_a: list, picks_a: list,
                          team_b: str, players_b: list, picks_b: list):
    """渲染交易分析結果"""
    st.markdown("## 交易分析")

    # 計算價值
    team_a_df = df[df['PLAYER_NAME'].isin(players_a)]
    team_b_df = df[df['PLAYER_NAME'].isin(players_b)]

    # 球員價值
    value_a = team_a_df['TRADE_VALUE'].sum() if len(team_a_df) > 0 else 0
    value_b = team_b_df['TRADE_VALUE'].sum() if len(team_b_df) > 0 else 0

    # 選秀籤價值
    picks_value_a = sum(get_pick_value(p) for p in picks_a)
    picks_value_b = sum(get_pick_value(p) for p in picks_b)

    total_a = value_a + picks_value_a
    total_b = value_b + picks_value_b

    # 薪資
    salary_a = team_a_df['SALARY_M'].sum() if len(team_a_df) > 0 else 0
    salary_b = team_b_df['SALARY_M'].sum() if len(team_b_df) > 0 else 0

    # 統計數據
    avg_age_a = team_a_df['AGE'].mean() if len(team_a_df) > 0 else 0
    avg_age_b = team_b_df['AGE'].mean() if len(team_b_df) > 0 else 0
    total_pts_a = team_a_df['PTS'].sum() if len(team_a_df) > 0 else 0
    total_pts_b = team_b_df['PTS'].sum() if len(team_b_df) > 0 else 0

    # 薪資匹配規則：125% + $100K
    def check_salary_match(outgoing, incoming):
        if outgoing == 0:
            return incoming == 0
        threshold = outgoing * 1.25 + 0.1
        return incoming <= threshold

    salary_ok_a = check_salary_match(salary_a, salary_b)
    salary_ok_b = check_salary_match(salary_b, salary_a)
    salary_match = salary_ok_a and salary_ok_b

    # 計算進階數據變化
    # A隊：失去 team_a_df，得到 team_b_df
    # B隊：失去 team_b_df，得到 team_a_df

    def calc_stats(player_df):
        if len(player_df) == 0:
            return {'PTS': 0, 'REB': 0, 'AST': 0, 'OFF_RATING': 0, 'DEF_RATING': 0, 'NET_RATING': 0}
        return {
            'PTS': player_df['PTS'].sum(),
            'REB': player_df['REB'].sum(),
            'AST': player_df['AST'].sum(),
            'OFF_RATING': player_df['OFF_RATING'].mean() if 'OFF_RATING' in player_df.columns else 0,
            'DEF_RATING': player_df['DEF_RATING'].mean() if 'DEF_RATING' in player_df.columns else 0,
            'NET_RATING': player_df['NET_RATING'].mean() if 'NET_RATING' in player_df.columns else 0,
        }

    stats_a_out = calc_stats(team_a_df)
    stats_b_out = calc_stats(team_b_df)

    # 顯示結果
    col1, col_mid, col2 = st.columns([2, 1, 2])

    with col1:
        st.markdown(f"### {team_a} 送出")

        for _, row in team_a_df.iterrows():
            years = int(row.get('YEARS_REMAINING', 1)) if pd.notna(row.get('YEARS_REMAINING')) else 1
            contract = row.get('CONTRACT_TYPE_CN', '-')
            st.markdown(f"""
**{row['PLAYER_NAME']}** ({row['AGE']:.0f}歲)
- 薪資: ${row['SALARY_M']:.1f}M | 合約: {years}年 {contract}
- 數據: {row['PTS']:.1f}分 {row['REB']:.1f}籃板 {row['AST']:.1f}助攻
- 交易價值: {row['TRADE_VALUE']:.0f}
            """)

        if picks_a:
            st.markdown("**選秀籤**")
            for pick in picks_a:
                pick_val = get_pick_value(pick)
                st.markdown(f"- {pick} (價值: {pick_val:.0f})")

        st.markdown(f"""
---
**總價值: {total_a:.0f}**
總薪資: ${salary_a:.1f}M | 平均年齡: {avg_age_a:.1f}
        """)

    with col_mid:
        if salary_match:
            st.success("薪資匹配通過")
        else:
            st.error(f"薪資不匹配 (差距: ${abs(salary_a - salary_b):.1f}M)")

        st.markdown("---")
        st.markdown("**價值比較**")
        st.markdown(f"- {team_a} 送出: {total_a:.0f}")
        st.markdown(f"- {team_b} 送出: {total_b:.0f}")
        st.markdown(f"- 差距: {abs(total_a - total_b):.0f}")

    with col2:
        st.markdown(f"### {team_b} 送出")

        for _, row in team_b_df.iterrows():
            years = int(row.get('YEARS_REMAINING', 1)) if pd.notna(row.get('YEARS_REMAINING')) else 1
            contract = row.get('CONTRACT_TYPE_CN', '-')
            st.markdown(f"""
**{row['PLAYER_NAME']}** ({row['AGE']:.0f}歲)
- 薪資: ${row['SALARY_M']:.1f}M | 合約: {years}年 {contract}
- 數據: {row['PTS']:.1f}分 {row['REB']:.1f}籃板 {row['AST']:.1f}助攻
- 交易價值: {row['TRADE_VALUE']:.0f}
            """)

        if picks_b:
            st.markdown("**選秀籤**")
            for pick in picks_b:
                pick_val = get_pick_value(pick)
                st.markdown(f"- {pick} (價值: {pick_val:.0f})")

        st.markdown(f"""
---
**總價值: {total_b:.0f}**
總薪資: ${salary_b:.1f}M | 平均年齡: {avg_age_b:.1f}
        """)

    # 交易後數據變化
    st.markdown("---")
    st.markdown("### 交易後數據變化")

    change_col1, change_col2 = st.columns(2)

    with change_col1:
        st.markdown(f"**{team_a} 交易後變化**")
        st.markdown("(失去左側球員，得到右側球員)")

        pts_change_a = stats_b_out['PTS'] - stats_a_out['PTS']
        reb_change_a = stats_b_out['REB'] - stats_a_out['REB']
        ast_change_a = stats_b_out['AST'] - stats_a_out['AST']
        ortg_change_a = stats_b_out['OFF_RATING'] - stats_a_out['OFF_RATING']
        drtg_change_a = stats_b_out['DEF_RATING'] - stats_a_out['DEF_RATING']
        net_change_a = stats_b_out['NET_RATING'] - stats_a_out['NET_RATING']

        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("得分", f"{stats_b_out['PTS']:.1f}", f"{pts_change_a:+.1f}")
            st.metric("籃板", f"{stats_b_out['REB']:.1f}", f"{reb_change_a:+.1f}")
            st.metric("助攻", f"{stats_b_out['AST']:.1f}", f"{ast_change_a:+.1f}")
        with col_stat2:
            st.metric("ORTG", f"{stats_b_out['OFF_RATING']:.1f}", f"{ortg_change_a:+.1f}")
            st.metric("DRTG", f"{stats_b_out['DEF_RATING']:.1f}", f"{drtg_change_a:+.1f}" if drtg_change_a <= 0 else f"{drtg_change_a:+.1f}", delta_color="inverse")
            st.metric("NET", f"{stats_b_out['NET_RATING']:.1f}", f"{net_change_a:+.1f}")

    with change_col2:
        st.markdown(f"**{team_b} 交易後變化**")
        st.markdown("(失去右側球員，得到左側球員)")

        pts_change_b = stats_a_out['PTS'] - stats_b_out['PTS']
        reb_change_b = stats_a_out['REB'] - stats_b_out['REB']
        ast_change_b = stats_a_out['AST'] - stats_b_out['AST']
        ortg_change_b = stats_a_out['OFF_RATING'] - stats_b_out['OFF_RATING']
        drtg_change_b = stats_a_out['DEF_RATING'] - stats_b_out['DEF_RATING']
        net_change_b = stats_a_out['NET_RATING'] - stats_b_out['NET_RATING']

        col_stat3, col_stat4 = st.columns(2)
        with col_stat3:
            st.metric("得分", f"{stats_a_out['PTS']:.1f}", f"{pts_change_b:+.1f}")
            st.metric("籃板", f"{stats_a_out['REB']:.1f}", f"{reb_change_b:+.1f}")
            st.metric("助攻", f"{stats_a_out['AST']:.1f}", f"{ast_change_b:+.1f}")
        with col_stat4:
            st.metric("ORTG", f"{stats_a_out['OFF_RATING']:.1f}", f"{ortg_change_b:+.1f}")
            st.metric("DRTG", f"{stats_a_out['DEF_RATING']:.1f}", f"{drtg_change_b:+.1f}" if drtg_change_b <= 0 else f"{drtg_change_b:+.1f}", delta_color="inverse")
            st.metric("NET", f"{stats_a_out['NET_RATING']:.1f}", f"{net_change_b:+.1f}")

    # 視覺化比較
    st.markdown("---")
    st.markdown("### 價值對比")

    # 使用 Plotly 製作對比圖
    fig = go.Figure()

    # A 隊價值條
    fig.add_trace(go.Bar(
        name=f'{team_a} 送出',
        x=['球員價值', '選秀籤價值', '總價值'],
        y=[value_a, picks_value_a, total_a],
        marker_color='#667eea',
        text=[f'{value_a:.0f}', f'{picks_value_a:.0f}', f'{total_a:.0f}'],
        textposition='outside'
    ))

    # B 隊價值條
    fig.add_trace(go.Bar(
        name=f'{team_b} 送出',
        x=['球員價值', '選秀籤價值', '總價值'],
        y=[value_b, picks_value_b, total_b],
        marker_color='#f093fb',
        text=[f'{value_b:.0f}', f'{picks_value_b:.0f}', f'{total_b:.0f}'],
        textposition='outside'
    ))

    fig.update_layout(
        barmode='group',
        height=400,
        title="雙方交易價值比較",
        yaxis_title="交易價值",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 交易後陣容變化
    st.markdown("### 交易後陣容變化")

    change_col1, change_col2 = st.columns(2)

    with change_col1:
        st.markdown(f"**{team_a} 交易後**")
        original_roster_a = df[df['TEAM_ABBREVIATION'] == team_a]

        # 送出的球員
        sent_salary_a = team_a_df['SALARY_M'].sum()
        sent_value_a = team_a_df['TRADE_VALUE'].sum()

        # 收到的球員
        received_salary_a = team_b_df['SALARY_M'].sum()
        received_value_a = team_b_df['TRADE_VALUE'].sum()

        salary_change_a = received_salary_a - sent_salary_a
        value_change_a = received_value_a - sent_value_a

        new_total_salary_a = original_roster_a['SALARY_M'].sum() + salary_change_a

        st.metric("新總薪資", f"${new_total_salary_a:.1f}M", f"{salary_change_a:+.1f}M")
        st.metric("陣容價值變化", f"{value_change_a:+.0f}", "")

    with change_col2:
        st.markdown(f"**{team_b} 交易後**")
        original_roster_b = df[df['TEAM_ABBREVIATION'] == team_b]

        salary_change_b = sent_salary_a - received_salary_a
        value_change_b = sent_value_a - received_value_a

        new_total_salary_b = original_roster_b['SALARY_M'].sum() + salary_change_b

        st.metric("新總薪資", f"${new_total_salary_b:.1f}M", f"{salary_change_b:+.1f}M")
        st.metric("陣容價值變化", f"{value_change_b:+.0f}", "")


def render_team_analysis(df: pd.DataFrame):
    """渲染球隊分析頁面"""
    st.header("球隊分析")
    
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
        st.subheader("陣容")
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
        st.subheader("薪資結構")
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

    # 檢查 AI 可用狀態
    api_key = os.getenv('ANTHROPIC_API_KEY')
    claude_available = api_key is not None

    # 檢查 Ollama
    ollama = OllamaAnalysisEngine()
    ollama_available = ollama.is_available()

    # 決定使用哪個 AI
    ai_backend = "none"
    if claude_available:
        ai_backend = "claude"
        st.success("✅ Claude API 已連接")
    elif ollama_available:
        ai_backend = "ollama"
        st.success("✅ Ollama 本地 AI 已連接（免費）")
    else:
        st.warning("⚠️ 無 AI 連接 - 使用本地規則分析")
        st.info("""
**啟用 AI 的方式：**
1. **Ollama（免費）**: 安裝 [Ollama](https://ollama.com)，執行 `ollama pull llama3.1` 和 `ollama serve`
2. **Claude API（付費）**: 設置 `ANTHROPIC_API_KEY` 環境變數
        """)

    # 分頁選擇
    ai_tab = st.radio(
        "選擇功能",
        ["💬 AI 對話", "📊 球隊分析", "🔄 交易分析"],
        horizontal=True
    )

    if ai_tab == "💬 AI 對話":
        render_ai_chat(df, ai_backend)
    elif ai_tab == "📊 球隊分析":
        render_ai_team_analysis(df, ai_backend)
    elif ai_tab == "🔄 交易分析":
        render_ai_trade_analysis(df, ai_backend)


def render_ai_chat(df: pd.DataFrame, ai_backend: str):
    """渲染 AI 對話介面"""
    st.subheader("💬 與 AI 對話")

    # 初始化對話歷史
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # 範例問題
    st.markdown("**範例問題：**")
    example_cols = st.columns(3)
    examples = [
        "誰是性價比最高的控球後衛？",
        "25歲以下最佳球員是誰？",
        "OKC 應該追求哪些球員？"
    ]

    for col, example in zip(example_cols, examples):
        if col.button(example, key=f"ex_{example[:5]}"):
            st.session_state.pending_question = example

    # 對話輸入
    user_input = st.chat_input("輸入你的問題...")

    # 處理輸入（包括範例點擊）
    question = user_input or st.session_state.get('pending_question', None)
    if 'pending_question' in st.session_state:
        del st.session_state.pending_question

    if question:
        # 加入對話歷史
        st.session_state.chat_history.append({"role": "user", "content": question})

        # 生成回答
        with st.spinner("AI 思考中..."):
            if ai_backend == "ollama":
                ollama = OllamaAnalysisEngine()
                response = ollama.answer_question(df, question)
            elif ai_backend == "claude":
                claude = ClaudeAnalysisEngine()
                response = claude.answer_trade_question(df, question)
            else:
                ai_module = AIAnalysisModule()
                response = ai_module.query(df, question, use_ai=False)

        st.session_state.chat_history.append({"role": "assistant", "content": response})

    # 顯示對話歷史
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 清除對話按鈕
    if st.session_state.chat_history:
        if st.button("🗑️ 清除對話"):
            st.session_state.chat_history = []
            st.rerun()


def render_ai_team_analysis(df: pd.DataFrame, ai_backend: str):
    """渲染 AI 球隊分析"""
    st.subheader("📊 球隊深度分析")

    teams = sorted(df['TEAM_ABBREVIATION'].unique().tolist())
    selected_team = st.selectbox("選擇要分析的球隊", teams, key="ai_team")

    analysis_type = st.radio(
        "分析類型",
        ["陣容診斷", "交易建議", "補強方向", "選秀策略"]
    )

    if st.button("🚀 開始分析", type="primary"):
        team_df = df[df['TEAM_ABBREVIATION'] == selected_team]

        # 設定問題
        if analysis_type == "陣容診斷":
            question = "請對這支球隊進行完整的陣容診斷，包含優劣勢分析"
        elif analysis_type == "交易建議":
            question = "請提供具體的交易建議，包含應該交易出去的球員和適合追求的目標"
        elif analysis_type == "補強方向":
            question = "請分析這支球隊的補強優先順序和推薦的球員類型"
        else:
            question = "請提供選秀策略建議，包含應該優先選擇的位置和球員類型"

        with st.spinner("AI 分析中..."):
            if ai_backend == "ollama":
                ollama = OllamaAnalysisEngine()
                analysis_result = ollama.analyze_team(df, selected_team, question)
            elif ai_backend == "claude":
                claude = ClaudeAnalysisEngine()
                analysis_result = claude.analyze_with_claude(df, selected_team, question)
            else:
                # 使用本地規則分析
                analysis_result = generate_ai_analysis(
                    df, team_df, selected_team, analysis_type
                )

            st.markdown("---")
            st.subheader("📋 分析報告")
            st.markdown(analysis_result)


def render_ai_trade_analysis(df: pd.DataFrame, ai_backend: str):
    """渲染 AI 交易分析"""
    st.subheader("🔄 AI 輔助交易分析")

    col1, col2 = st.columns(2)

    with col1:
        team_a = st.selectbox("A 隊", sorted(df['TEAM_ABBREVIATION'].unique()), key="trade_team_a")
        team_a_players = df[df['TEAM_ABBREVIATION'] == team_a]['PLAYER_NAME'].tolist()
        team_a_gives = st.multiselect("A 隊送出", team_a_players, key="trade_a_gives")

    with col2:
        team_b = st.selectbox("B 隊", sorted(df['TEAM_ABBREVIATION'].unique()), key="trade_team_b")
        team_b_players = df[df['TEAM_ABBREVIATION'] == team_b]['PLAYER_NAME'].tolist()
        team_b_gives = st.multiselect("B 隊送出", team_b_players, key="trade_b_gives")

    if st.button("🔍 AI 分析這筆交易", type="primary"):
        if not team_a_gives or not team_b_gives:
            st.error("請選擇雙方要交易的球員")
        else:
            with st.spinner("AI 分析交易中..."):
                if ai_backend == "claude":
                    claude = ClaudeAnalysisEngine()
                    result = claude.simulate_trade_analysis(
                        df, team_a, team_a_gives, team_b, team_b_gives
                    )
                elif ai_backend == "ollama":
                    # 使用 Ollama 分析交易
                    ollama = OllamaAnalysisEngine()
                    trade_players = ', '.join(team_a_gives + team_b_gives)
                    prompt = f"""分析這筆交易：
{team_a} 送出: {', '.join(team_a_gives)}
{team_b} 送出: {', '.join(team_b_gives)}

請評估：1. 交易是否公平 2. 對雙方的影響 3. 薪資匹配可行性"""
                    result = ollama.chat(prompt, "你是 NBA 交易分析專家，請用繁體中文回答。")
                else:
                    # 本地分析
                    engine = TradeValueEngine()
                    trade_result = engine.simulate_trade(df, team_a_gives, team_b_gives)

                    result = f"""## 交易分析結果

**{team_a} 送出**: {', '.join(team_a_gives)}
**{team_b} 送出**: {', '.join(team_b_gives)}

### 薪資匹配
{'✅ 薪資匹配成功' if trade_result['salary_match'] else f"❌ 薪資匹配失敗，差距 ${trade_result['salary_diff_m']:.1f}M"}

### 價值分析
- A 隊送出總價值: {trade_result['team_a_package']['total_trade_value']:.1f}
- B 隊送出總價值: {trade_result['team_b_package']['total_trade_value']:.1f}
- 價值差異: {abs(trade_result['value_difference']):.1f}

### 結論
{trade_result['verdict']}

💡 **提示**: 安裝 Ollama 或設置 ANTHROPIC_API_KEY 可獲得更詳細的 AI 分析
"""

                st.markdown("---")
                st.markdown(result)


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
    # 載入數據
    df = load_data()

    if df is None:
        st.stop()

    # 簡化的側邊欄
    st.sidebar.markdown("## NBA Trade Machine")
    st.sidebar.markdown("---")

    # 頁面選擇
    page = st.sidebar.radio(
        "功能",
        ["交易模擬", "球員搜尋", "球隊分析"],
        label_visibility="collapsed"
    )

    # 渲染對應頁面
    if page == "交易模擬":
        render_trade_simulator(df)
    elif page == "球員搜尋":
        filtered_df = render_sidebar(df)
        render_player_search(filtered_df)
    elif page == "球隊分析":
        render_team_analysis(df)

    # 頁腳
    st.sidebar.markdown("---")
    st.sidebar.markdown("2025-26 賽季數據")


if __name__ == "__main__":
    main()