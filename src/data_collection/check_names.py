"""
檢查並修復球員名稱匹配問題
"""

import pandas as pd

def check_missing_players():
    """找出未匹配的重要球員"""
    
    df_stats = pd.read_csv("data/raw/player_stats_2025-26.csv")
    df_salary = pd.read_csv("data/raw/player_salaries_2025-26.csv")
    
    # 找出高薪但未匹配的球員
    salary_names = set(df_salary['PLAYER_NAME'])
    stats_names = set(df_stats['PLAYER_NAME'])
    
    # 薪資表有但數據表沒有的
    in_salary_not_stats = salary_names - stats_names
    
    # 數據表有但薪資表沒有的
    in_stats_not_salary = stats_names - salary_names
    
    print("="*60)
    print("薪資表有，但數據表沒匹配到的前 20 名高薪球員：")
    print("="*60)
    
    top_salary = df_salary[df_salary['PLAYER_NAME'].isin(in_salary_not_stats)].head(20)
    print(top_salary[['PLAYER_NAME', 'SALARY_M']].to_string())
    
    print("\n" + "="*60)
    print("數據表有，但薪資表沒匹配到的前 20 名得分球員：")
    print("="*60)
    
    top_stats = df_stats[df_stats['PLAYER_NAME'].isin(in_stats_not_salary)].sort_values('PTS', ascending=False).head(20)
    print(top_stats[['PLAYER_NAME', 'PTS']].to_string())


if __name__ == "__main__":
    check_missing_players()