"""
修正球員名稱匹配問題
移除特殊字符，統一名稱格式
"""

import pandas as pd
import unicodedata

def normalize_name(name):
    """將特殊字符轉換為基本英文字母"""
    # 將 ć -> c, ņ -> n, ģ -> g 等
    normalized = unicodedata.normalize('NFD', name)
    ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
    return ascii_name

def fix_and_merge():
    """修正名稱後重新合併"""
    
    df_stats = pd.read_csv("data/raw/player_stats_2024-25.csv")
    df_salary = pd.read_csv("data/raw/player_salaries_2024-25.csv")
    
    print(f"進階數據：{len(df_stats)} 名球員")
    print(f"薪資數據：{len(df_salary)} 名球員")
    
    # 建立標準化名稱欄位
    df_stats['NAME_KEY'] = df_stats['PLAYER_NAME'].apply(normalize_name)
    df_salary['NAME_KEY'] = df_salary['PLAYER_NAME'].apply(normalize_name)
    
    # 用標準化名稱合併
    df_merged = df_stats.merge(
        df_salary[['NAME_KEY', 'SALARY', 'SALARY_M']], 
        on='NAME_KEY', 
        how='left'
    )
    
    # 移除輔助欄位
    df_merged = df_merged.drop(columns=['NAME_KEY'])
    
    # 檢查合併結果
    matched = df_merged['SALARY'].notna().sum()
    print(f"\n成功匹配薪資：{matched} 名球員")
    print(f"未匹配薪資：{len(df_merged) - matched} 名球員")
    
    # 篩選有薪資的球員
    df_final = df_merged[df_merged['SALARY'].notna()].copy()
    
    # 儲存
    output_path = "data/processed/players_with_salary.csv"
    df_final.to_csv(output_path, index=False)
    print(f"\n合併數據已儲存至 {output_path}")
    print(f"共 {len(df_final)} 名球員")
    
    # 確認頂薪球員是否匹配成功
    print("\n確認頂薪球員匹配：")
    top_players = ['Nikola Jokić', 'Luka Dončić', 'Stephen Curry', 'LeBron James', 'Giannis Antetokounmpo']
    for name in top_players:
        row = df_final[df_final['PLAYER_NAME'] == name]
        if len(row) > 0:
            salary = row['SALARY_M'].values[0]
            print(f"  ✓ {name}: ${salary}M")
        else:
            print(f"  ✗ {name}: 未匹配")
    
    # 預覽前 10 名（按得分排序）
    print("\n前 10 名球員預覽：")
    cols = ['PLAYER_NAME', 'TEAM_ABBREVIATION', 'PTS', 'EFG_PCT', 'TS_PCT', 'SALARY_M']
    print(df_final[cols].head(10).to_string())
    
    return df_final


if __name__ == "__main__":
    fix_and_merge()