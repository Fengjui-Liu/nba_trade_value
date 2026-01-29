"""
批次抓取所有球員合約數據
==========================

從 Spotrac 抓取真實的合約資訊：
• 合約年份明細
• Trade Kicker
• 球員/球隊選項
• 簽約日期
"""

import os
import re
import time
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from pathlib import Path

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# Spotrac player ID 映射 (部分常見球員)
# 完整映射需要從 Spotrac 網站抓取
SPOTRAC_PLAYER_MAP = {
    "Stephen Curry": (6287, "stephen-curry"),
    "LeBron James": (6163, "lebron-james"),
    "Kevin Durant": (6167, "kevin-durant"),
    "Giannis Antetokounmpo": (15559, "giannis-antetokounmpo"),
    "Luka Doncic": (25748, "luka-doncic"),
    "Jayson Tatum": (25750, "jayson-tatum"),
    "Joel Embiid": (15555, "joel-embiid"),
    "Nikola Jokic": (15642, "nikola-jokic"),
    "Shai Gilgeous-Alexander": (28036, "shai-gilgeous-alexander"),
    "Anthony Edwards": (32665, "anthony-edwards"),
    "Damian Lillard": (12444, "damian-lillard"),
    "Jimmy Butler": (9999, "jimmy-butler"),
    "Kawhi Leonard": (12453, "kawhi-leonard"),
    "Paul George": (6174, "paul-george"),
    "Devin Booker": (19194, "devin-booker"),
    "Donovan Mitchell": (25751, "donovan-mitchell"),
    "Trae Young": (28035, "trae-young"),
    "Ja Morant": (32666, "ja-morant"),
    "Zion Williamson": (32667, "zion-williamson"),
    "Jaylen Brown": (18841, "jaylen-brown"),
    "Bam Adebayo": (25752, "bam-adebayo"),
    "De'Aaron Fox": (25753, "deaaron-fox"),
    "Domantas Sabonis": (18842, "domantas-sabonis"),
    "Karl-Anthony Towns": (18843, "karl-anthony-towns"),
    "Bradley Beal": (13251, "bradley-beal"),
    "Kyrie Irving": (9998, "kyrie-irving"),
    "Jalen Williams": (37999, "jalen-williams"),
    "Jalen Brunson": (28037, "jalen-brunson"),
    "Victor Wembanyama": (41000, "victor-wembanyama"),
    "Tyrese Haliburton": (32668, "tyrese-haliburton"),
    "Tyrese Maxey": (35000, "tyrese-maxey"),
    "Evan Mobley": (37998, "evan-mobley"),
    "Cade Cunningham": (38001, "cade-cunningham"),
    "Scottie Barnes": (38002, "scottie-barnes"),
    "Paolo Banchero": (40001, "paolo-banchero"),
    "Anthony Davis": (9997, "anthony-davis"),
    "Rudy Gobert": (13250, "rudy-gobert"),
    "Jrue Holiday": (9996, "jrue-holiday"),
    "Khris Middleton": (9995, "khris-middleton"),
    "Chris Paul": (6166, "chris-paul"),
    "Russell Westbrook": (6165, "russell-westbrook"),
    "James Harden": (9994, "james-harden"),
    "Pascal Siakam": (22000, "pascal-siakam"),
    "Julius Randle": (18844, "julius-randle"),
    "Fred VanVleet": (22001, "fred-vanvleet"),
    "OG Anunoby": (25754, "og-anunoby"),
    "Mikal Bridges": (28038, "mikal-bridges"),
    "Franz Wagner": (38003, "franz-wagner"),
    "Alperen Sengun": (38004, "alperen-sengun"),
}


def money_to_float(x: str) -> Optional[float]:
    """將金額字串轉為浮點數 (以百萬為單位)"""
    if x is None:
        return None
    x = x.strip()
    if not x or x in {"-", "—", "N/A"}:
        return None
    m = re.sub(r"[^0-9.]", "", x.replace(",", ""))
    try:
        return round(float(m) / 1_000_000, 2) if m else None
    except:
        return None


def parse_contract_details(soup: BeautifulSoup) -> Dict:
    """解析合約詳細資訊"""
    result = {
        "contract_terms": None,
        "years": None,
        "total_value_m": None,
        "avg_salary_m": None,
        "guaranteed_m": None,
        "signing_bonus_m": None,
        "trade_bonus_pct": None,
        "player_option_years": [],
        "team_option_years": [],
        "yearly_breakdown": [],
    }

    # 找到主合約區塊
    contract_wrapper = soup.select_one("div.contract-wrapper")
    if not contract_wrapper:
        return result

    # 合約年份
    years_span = contract_wrapper.select_one("h2 span.years")
    if years_span:
        result["years"] = years_span.get_text(strip=True)

    # 合約細節
    for cell in contract_wrapper.select("div.contract-details div.cell"):
        label_el = cell.select_one("div.label")
        value_el = cell.select_one("div.value")
        if not label_el:
            continue

        label = label_el.get_text(strip=True).lower()
        value = value_el.get_text(strip=True) if value_el else ""

        if "contract terms" in label:
            result["contract_terms"] = value
        elif "total value" in label:
            result["total_value_m"] = money_to_float(value)
        elif "average" in label or "aav" in label:
            result["avg_salary_m"] = money_to_float(value)
        elif "guaranteed" in label:
            result["guaranteed_m"] = money_to_float(value)
        elif "signing bonus" in label:
            result["signing_bonus_m"] = money_to_float(value)
        elif "trade bonus" in label or "trade kicker" in label:
            # 解析百分比
            pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
            if pct_match:
                result["trade_bonus_pct"] = float(pct_match.group(1))

    # 年度明細表
    table = contract_wrapper.select_one("table.contract-breakdown")
    if table:
        headers = []
        for th in table.select("thead th"):
            headers.append(th.get_text(strip=True))

        for tr in table.select("tbody tr"):
            tds = [td.get_text(strip=True) for td in tr.select("td")]
            if tds and len(tds) >= 2:
                row_data = {}
                for i, val in enumerate(tds):
                    if i < len(headers):
                        header = headers[i].lower()
                        if "year" in header or "season" in header:
                            row_data["season"] = val
                        elif "salary" in header or "base" in header:
                            row_data["salary_m"] = money_to_float(val)
                        elif "cap" in header and "%" in header:
                            pct = re.sub(r"[^0-9.]", "", val)
                            row_data["cap_pct"] = float(pct) if pct else None
                        elif "option" in header.lower():
                            if "PO" in val or "Player" in val:
                                result["player_option_years"].append(row_data.get("season", ""))
                            elif "TO" in val or "Team" in val:
                                result["team_option_years"].append(row_data.get("season", ""))

                if row_data:
                    result["yearly_breakdown"].append(row_data)

    return result


def fetch_player_contract(player_id: int, slug: str) -> Optional[Dict]:
    """抓取單一球員的合約資訊"""
    url = f"https://www.spotrac.com/nba/player/_/id/{player_id}/{slug}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  ⚠ HTTP {resp.status_code} for {slug}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        contract = parse_contract_details(soup)
        contract["spotrac_url"] = url
        contract["spotrac_id"] = player_id

        return contract

    except Exception as e:
        print(f"  ⚠ Error fetching {slug}: {e}")
        return None


def fetch_all_contracts(players_df: pd.DataFrame,
                        delay: float = 1.5,
                        output_path: str = "data/raw/player_contracts.json") -> pd.DataFrame:
    """
    批次抓取所有球員的合約資訊

    參數：
    - players_df: 包含 PLAYER_NAME 欄位的 DataFrame
    - delay: 請求間隔（秒），避免被封鎖
    - output_path: 輸出 JSON 路徑
    """
    contracts = {}
    total = len(players_df)
    matched = 0

    print(f"開始抓取 {total} 名球員的合約資訊...")
    print("=" * 60)

    for idx, row in players_df.iterrows():
        player_name = row['PLAYER_NAME']

        # 查找 Spotrac 映射
        if player_name in SPOTRAC_PLAYER_MAP:
            player_id, slug = SPOTRAC_PLAYER_MAP[player_name]
            print(f"[{idx+1}/{total}] 抓取 {player_name}...", end=" ")

            contract = fetch_player_contract(player_id, slug)
            if contract:
                contracts[player_name] = contract
                matched += 1
                print("✓")
            else:
                print("✗")

            time.sleep(delay)
        else:
            # 未在映射中的球員，跳過或嘗試自動生成 slug
            pass

    print("=" * 60)
    print(f"完成！成功抓取 {matched}/{total} 名球員的合約資訊")

    # 儲存 JSON
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(contracts, f, ensure_ascii=False, indent=2)
    print(f"已儲存至 {output_path}")

    return pd.DataFrame.from_dict(contracts, orient='index')


def merge_contracts_to_players(players_df: pd.DataFrame,
                                contracts_path: str = "data/raw/player_contracts.json") -> pd.DataFrame:
    """
    將合約資訊合併到球員 DataFrame

    新增欄位：
    - CONTRACT_YEARS_REAL: 真實合約年份
    - TOTAL_CONTRACT_VALUE_REAL: 真實合約總值
    - TRADE_KICKER_PCT: Trade Kicker 百分比
    - HAS_PLAYER_OPTION: 是否有球員選項
    - HAS_TEAM_OPTION: 是否有球隊選項
    - YEARS_BREAKDOWN: 年度薪資明細
    """
    df = players_df.copy()

    if not os.path.exists(contracts_path):
        print(f"合約數據不存在: {contracts_path}")
        print("請先執行 fetch_all_contracts() 抓取數據")
        return df

    with open(contracts_path, 'r', encoding='utf-8') as f:
        contracts = json.load(f)

    # 初始化新欄位
    df['CONTRACT_YEARS_REAL'] = None
    df['TOTAL_CONTRACT_VALUE_REAL'] = None
    df['TRADE_KICKER_PCT'] = None
    df['HAS_PLAYER_OPTION'] = False
    df['HAS_TEAM_OPTION'] = False
    df['YEARS_BREAKDOWN'] = None

    matched = 0
    for idx, row in df.iterrows():
        player_name = row['PLAYER_NAME']
        if player_name in contracts:
            c = contracts[player_name]
            df.at[idx, 'CONTRACT_YEARS_REAL'] = c.get('years')
            df.at[idx, 'TOTAL_CONTRACT_VALUE_REAL'] = c.get('total_value_m')
            df.at[idx, 'TRADE_KICKER_PCT'] = c.get('trade_bonus_pct')
            df.at[idx, 'HAS_PLAYER_OPTION'] = len(c.get('player_option_years', [])) > 0
            df.at[idx, 'HAS_TEAM_OPTION'] = len(c.get('team_option_years', [])) > 0
            df.at[idx, 'YEARS_BREAKDOWN'] = json.dumps(c.get('yearly_breakdown', []))
            matched += 1

    print(f"已合併 {matched}/{len(df)} 名球員的真實合約資訊")
    return df


def update_contract_module_with_real_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    用真實數據更新 ContractModule 的推估值

    優先使用真實數據，缺失時使用推估值
    """
    # 如果有真實的合約年份，更新 YEARS_REMAINING
    if 'CONTRACT_YEARS_REAL' in df.columns:
        # 解析真實年份 (例如 "4 yrs" -> 4)
        def parse_years(val):
            if pd.isna(val):
                return None
            match = re.search(r'(\d+)', str(val))
            return int(match.group(1)) if match else None

        real_years = df['CONTRACT_YEARS_REAL'].apply(parse_years)
        # 只在有真實數據時更新
        mask = real_years.notna()
        if 'YEARS_REMAINING' in df.columns:
            df.loc[mask, 'YEARS_REMAINING'] = real_years[mask]

    # 如果有真實的 Trade Kicker，更新標記
    if 'TRADE_KICKER_PCT' in df.columns:
        df['TRADE_KICKER_LIKELY'] = df['TRADE_KICKER_PCT'].notna() & (df['TRADE_KICKER_PCT'] > 0)

    return df


if __name__ == "__main__":
    # 測試：抓取部分球員的合約
    print("測試模式：抓取 5 名球員的合約資訊\n")

    test_players = [
        "Stephen Curry",
        "LeBron James",
        "Giannis Antetokounmpo",
        "Luka Doncic",
        "Victor Wembanyama"
    ]

    test_df = pd.DataFrame({"PLAYER_NAME": test_players})
    contracts_df = fetch_all_contracts(test_df, delay=1.0,
                                       output_path="data/raw/player_contracts_test.json")

    print("\n抓取結果：")
    print(contracts_df[['years', 'total_value_m', 'trade_bonus_pct']].to_string())
