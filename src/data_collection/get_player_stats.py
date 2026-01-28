"""
NBA 球員進階數據收集
抓取 2024-25 賽季所有球員的效率與進階指標
"""

from nba_api.stats.endpoints import leaguedashplayerstats
from nba_api.stats.endpoints import leaguedashplayerbiostats
import pandas as pd
import time

def get_player_advanced_stats(season="2024-25"):
    """抓取球員進階數據"""
    
    print(f"正在抓取 {season} 賽季球員數據...")
    
    # 基本數據
    print("  抓取基本數據...")
    player_base = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base"
    )
    time.sleep(1)
    df_base = player_base.get_data_frames()[0]
    
    # 進階數據
    print("  抓取進階數據...")
    player_advanced = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Advanced"
    )
    time.sleep(1)
    df_advanced = player_advanced.get_data_frames()[0]
    
    # 球員基本資料
    print("  抓取球員資料...")
    player_bio = leaguedashplayerbiostats.LeagueDashPlayerBioStats(
        season=season
    )
    time.sleep(1)
    df_bio = player_bio.get_data_frames()[0]
    
    print(f"  基本數據：{len(df_base)} 筆")
    print(f"  進階數據：{len(df_advanced)} 筆")
    print(f"  球員資料：{len(df_bio)} 筆")
    
    # 看看進階數據有哪些欄位
    print("\n進階數據可用欄位：")
    print(df_advanced.columns.tolist())
    
    return df_advanced, df_base, df_bio


def merge_player_data(df_advanced, df_base, df_bio):
    """合併數據，選取需要的欄位"""
    
    # 計算 eFG% 和 TS%
    df_base['EFG_PCT'] = (df_base['FGM'] + 0.5 * df_base['FG3M']) / df_base['FGA']
    df_base['TS_PCT'] = df_base['PTS'] / (2 * (df_base['FGA'] + 0.44 * df_base['FTA']))
    
    # 從基本數據選取欄位
    base_cols = [
        'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION',
        'GP', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK',
        'FG_PCT', 'FG3_PCT', 'FT_PCT', 'EFG_PCT', 'TS_PCT'
    ]
    df_base_selected = df_base[base_cols].copy()
    
    # 從進階數據選取欄位（加入 PIE）
    advanced_cols = [
        'PLAYER_ID', 'USG_PCT', 'NET_RATING', 'OFF_RATING', 'DEF_RATING', 'PIE'
    ]
    available_advanced = [col for col in advanced_cols if col in df_advanced.columns]
    df_advanced_selected = df_advanced[available_advanced].copy()
    
    # 從球員資料選取欄位
    bio_cols = ['PLAYER_ID', 'PLAYER_HEIGHT', 'PLAYER_WEIGHT', 'AGE']
    df_bio_selected = df_bio[bio_cols].copy()
    
    # 合併
    df_merged = df_base_selected.merge(df_advanced_selected, on='PLAYER_ID', how='left')
    df_merged = df_merged.merge(df_bio_selected, on='PLAYER_ID', how='left')
    
    # 排序
    df_merged = df_merged.sort_values('PTS', ascending=False).reset_index(drop=True)
    
    return df_merged


def main():
    # 抓取數據
    df_advanced, df_base, df_bio = get_player_advanced_stats("2024-25")
    
    # 合併數據
    df_players = merge_player_data(df_advanced, df_base, df_bio)
    
    # 儲存
    output_path = "data/raw/player_stats_2024-25.csv"
    df_players.to_csv(output_path, index=False)
    print(f"\n數據已儲存至 {output_path}")
    print(f"共 {len(df_players)} 名球員，{len(df_players.columns)} 個欄位")
    
    # 預覽
    print("\n前 10 名球員預覽：")
    preview_cols = ['PLAYER_NAME', 'PTS', 'NET_RATING', 'PIE', 'TS_PCT']
    print(df_players[preview_cols].head(10).to_string())
    
    return df_players


if __name__ == "__main__":
    main()