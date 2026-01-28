"""
Phase 2：球員價值評估模型 v2
加入 PIE 指標，調整權重
"""

import pandas as pd
import numpy as np

def calculate_player_value():
    """計算球員價值與剩餘價值"""
    
    # 讀取合併數據
    df = pd.read_csv("data/processed/players_with_salary.csv")
    
    print(f"載入 {len(df)} 名球員數據")
    
    # ========== 篩選條件 ==========
    df_filtered = df[(df['GP'] >= 20) & (df['MIN'] >= 15)].copy()
    print(f"篩選後：{len(df_filtered)} 名球員（GP>=20, MIN>=15）")
    
    # ========== 計算綜合評分 ==========
    
    # 1. PIE 分數（核心指標，權重最高）
    df_filtered['PIE_SCORE'] = (df_filtered['PIE'].rank(pct=True) * 100).round(1)
    
    # 2. 效率指標
    df_filtered['EFG_SCORE'] = (df_filtered['EFG_PCT'].rank(pct=True) * 100).round(1)
    df_filtered['TS_SCORE'] = (df_filtered['TS_PCT'].rank(pct=True) * 100).round(1)
    
    # 3. 淨效率值（綜合進攻防守）
    df_filtered['NET_SCORE'] = (df_filtered['NET_RATING'].rank(pct=True) * 100).round(1)
    
    # 4. 產量指標
    df_filtered['PRODUCTION_SCORE'] = (
        (df_filtered['PTS'].rank(pct=True) * 0.4 +
         df_filtered['REB'].rank(pct=True) * 0.25 +
         df_filtered['AST'].rank(pct=True) * 0.25 +
         df_filtered['STL'].rank(pct=True) * 0.05 +
         df_filtered['BLK'].rank(pct=True) * 0.05) * 100
    ).round(1)
    
    # ========== 綜合價值分數（調整權重）==========
    # PIE 40% + 產量 25% + 淨效率 20% + 效率 15%
    df_filtered['VALUE_SCORE'] = (
        df_filtered['PIE_SCORE'] * 0.40 +
        df_filtered['PRODUCTION_SCORE'] * 0.25 +
        df_filtered['NET_SCORE'] * 0.20 +
        df_filtered['TS_SCORE'] * 0.15
    ).round(1)
    
    # ========== 年齡調整 ==========
    # 年輕球員（<25）加分，老將（>32）減分
    def age_adjustment(age):
        if pd.isna(age):
            return 0
        if age < 23:
            return 5   # 高潛力新秀
        elif age < 25:
            return 3   # 成長期
        elif age <= 28:
            return 0   # 巔峰期
        elif age <= 32:
            return -2  # 穩定期
        else:
            return -5  # 衰退風險
    
    df_filtered['AGE_ADJ'] = df_filtered['AGE'].apply(age_adjustment)
    df_filtered['VALUE_SCORE_ADJ'] = (df_filtered['VALUE_SCORE'] + df_filtered['AGE_ADJ']).round(1)
    
    # ========== 估算市場價值 ==========
    # VALUE_SCORE_ADJ = 100 → 頂薪 $51M
    # VALUE_SCORE_ADJ = 50 → 中產 $12M
    df_filtered['MARKET_VALUE_M'] = (
        df_filtered['VALUE_SCORE_ADJ'] / 100 * 51
    ).round(2)
    
    # ========== 計算剩餘價值 ==========
    df_filtered['SURPLUS_VALUE_M'] = (
        df_filtered['MARKET_VALUE_M'] - df_filtered['SALARY_M']
    ).round(2)
    
    # ========== 排序與輸出 ==========
    df_result = df_filtered.sort_values('SURPLUS_VALUE_M', ascending=False).reset_index(drop=True)
    
    # 選擇輸出欄位
    output_cols = [
        'PLAYER_NAME', 'TEAM_ABBREVIATION', 'AGE', 'GP', 'MIN',
        'PTS', 'REB', 'AST', 'PIE', 'NET_RATING', 'TS_PCT',
        'VALUE_SCORE', 'AGE_ADJ', 'VALUE_SCORE_ADJ',
        'MARKET_VALUE_M', 'SALARY_M', 'SURPLUS_VALUE_M'
    ]
    
    df_output = df_result[output_cols].copy()
    
    # 儲存
    output_path = "data/processed/player_value_ranking.csv"
    df_output.to_csv(output_path, index=False)
    print(f"\n價值評估已儲存至 {output_path}")
    
    # ========== 結果預覽 ==========
    print("\n" + "="*70)
    print("🏆 最划算的 15 名球員（Surplus Value 最高）")
    print("="*70)
    display_cols = ['PLAYER_NAME', 'AGE', 'PIE', 'VALUE_SCORE_ADJ', 'MARKET_VALUE_M', 'SALARY_M', 'SURPLUS_VALUE_M']
    print(df_output[display_cols].head(15).to_string())
    
    print("\n" + "="*70)
    print("💸 最不划算的 15 名球員（Surplus Value 最低）")
    print("="*70)
    print(df_output[display_cols].tail(15).to_string())
    
    print("\n" + "="*70)
    print("⭐ 頂級球星價值檢視")
    print("="*70)
    stars = ['Stephen Curry', 'LeBron James', 'Kevin Durant', 'Nikola Jokić', 
             'Giannis Antetokounmpo', 'Luka Dončić', 'Shai Gilgeous-Alexander']
    df_stars = df_output[df_output['PLAYER_NAME'].isin(stars)].sort_values('VALUE_SCORE_ADJ', ascending=False)
    print(df_stars[display_cols].to_string())
    
    return df_output


if __name__ == "__main__":
    calculate_player_value()