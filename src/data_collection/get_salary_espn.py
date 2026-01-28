"""
NBA 球員薪資數據收集
從 ESPN 抓取 2024-25 賽季薪資
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

def get_espn_salaries():
    """從 ESPN 抓取所有球員薪資（分頁）"""
    
    all_players = []
    page = 1
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    while True:
        url = f"https://www.espn.com/nba/salaries/_/year/2025/page/{page}"
        print(f"正在抓取第 {page} 頁...")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"抓取失敗: {response.status_code}")
            break
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 找到表格中的所有行
        rows = soup.find_all('tr')
        
        page_players = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                # 排名
                rank = cols[0].get_text(strip=True)
                if not rank.isdigit():
                    continue
                    
                # 球員名稱
                name_cell = cols[1]
                name = name_cell.get_text(strip=True)
                # 移除位置標記 (G, F, C)
                name = re.sub(r',\s*[GFC]+$', '', name)
                
                # 球隊
                team = cols[2].get_text(strip=True)
                
                # 薪資
                salary_text = cols[3].get_text(strip=True)
                salary_clean = re.sub(r'[,$]', '', salary_text)
                try:
                    salary = int(salary_clean)
                except:
                    salary = 0
                
                if name and salary > 0:
                    page_players.append({
                        'PLAYER_NAME': name,
                        'TEAM': team,
                        'SALARY': salary
                    })
        
        if not page_players:
            print(f"第 {page} 頁沒有數據，結束")
            break
            
        all_players.extend(page_players)
        print(f"  抓到 {len(page_players)} 名球員")
        
        # ESPN 有 13 頁
        if page >= 13:
            break
            
        page += 1
        time.sleep(1)  # 避免過快請求
    
    df = pd.DataFrame(all_players)
    print(f"\n總共抓取 {len(df)} 名球員薪資")
    
    return df


def main():
    # 抓取薪資
    df_salary = get_espn_salaries()
    
    if df_salary is None or len(df_salary) == 0:
        print("抓取失敗")
        return
    
    # 新增薪資（百萬）欄位
    df_salary['SALARY_M'] = (df_salary['SALARY'] / 1_000_000).round(2)
    
    # 儲存
    output_path = "data/raw/player_salaries_2024-25.csv"
    df_salary.to_csv(output_path, index=False)
    print(f"\n薪資數據已儲存至 {output_path}")
    
    # 預覽
    print("\n薪資前 15 名球員：")
    print(df_salary.head(15).to_string())
    
    return df_salary


if __name__ == "__main__":
    main()