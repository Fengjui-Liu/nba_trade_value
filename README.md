# NBA 球員交易價值評估系統

## 系統架構

```
┌─────────────────────────────────────────────────────────┐
│                 球員交易價值評估系統                      │
├─────────────────┬─────────────────┬─────────────────────┤
│   💰 薪資模組    │  📊 進階數據模組  │   🧩 適配度模組     │
├─────────────────┼─────────────────┼─────────────────────┤
│ • 當前薪資      │ • PER 近似值     │ • 打法風格分類      │
│ • 薪資帽佔比    │ • BPM / VORP    │ • 與現有陣容互補性   │
│ • 薪資等級分類  │ • Win Shares    │ • 位置彈性         │
│ • 市場價值估算  │ • 年齡曲線預測   │ • 進攻/防守角色適配  │
│ • 合約性價比    │ • 綜合價值評分   │ • 適配彈性分數      │
└─────────────────┴─────────────────┴─────────────────────┘
                           ↓
              ┌─────────────────────────┐
              │   Trade Value Engine    │
              │  Surplus Value 計算     │
              │  (表現價值 - 實際薪資)   │
              └─────────────────────────┘
```

## 專案結構

```
nba_trade_value/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py                          # 主程式入口
│   ├── data_collection/                 # 數據收集模組
│   │   ├── __init__.py
│   │   ├── get_contracts.py             # Spotrac 合約爬蟲
│   │   ├── get_salary_espn.py           # ESPN 薪資爬蟲
│   │   ├── get_player_stats.py          # NBA API 進階數據
│   │   ├── check_names.py              # 名稱匹配診斷
│   │   ├── fix_names_and_merge.py      # 名稱標準化與合併
│   │   └── value_model.py              # 舊版價值模型 (legacy)
│   └── modules/                         # 核心分析模組
│       ├── __init__.py
│       ├── salary_module.py             # 薪資模組
│       ├── advanced_stats_module.py     # 進階數據模組
│       ├── fit_module.py                # 適配度模組
│       └── trade_value_engine.py        # 交易價值引擎
└── data/
    ├── raw/                             # 原始數據
    │   ├── player_salaries_2024-25.csv
    │   └── player_stats_2024-25.csv
    └── processed/                       # 處理後數據
        ├── players_with_salary.csv
        ├── trade_value_full.csv
        └── trade_value_ranking.csv
```

## 模組說明

### 薪資模組 (`SalaryModule`)
- 計算薪資帽佔比 (CAP_PCT)
- 薪資等級分類 (SUPERMAX / MAX / NEAR_MAX / MID_LEVEL / ROLE_PLAYER / MINIMUM)
- 基於表現的市場價值估算
- 合約性價比 (CONTRACT_VALUE_RATIO)

### 進階數據模組 (`AdvancedStatsModule`)
- PER 近似計算 (Player Efficiency Rating)
- BPM 近似計算 (Box Plus/Minus)
- VORP 近似計算 (Value Over Replacement Player)
- Win Shares 近似計算
- 年齡曲線因子與預測
- 綜合價值評分 (VALUE_SCORE)

### 適配度模組 (`FitModule`)
- 10 種打法風格分類 (得分後衛型、組織者型、3D 球員型等)
- 進攻角色分類 (第一得分手、主要組織者、空間拉開者等)
- 防守角色分類 (護框者、外線防守者、全能防守者等)
- 位置彈性評估
- 球隊適配度分析

### 交易價值引擎 (`TradeValueEngine`)
- 整合三大模組的加權綜合評分
- 交易價值等級 (UNTOUCHABLE → TRADEABLE)
- 交易目標搜尋 (依預算、位置、風格、年齡)
- 球員比較
- 交易模擬 (含薪資匹配檢查)

## 使用方式

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行完整評估流水線
python -m src.main
```

## 數據流水線

```
ESPN 薪資爬蟲 ──→ player_salaries_2024-25.csv ─┐
                                               ├─→ 名稱標準化合併 ──→ players_with_salary.csv
NBA API 數據  ──→ player_stats_2024-25.csv  ───┘
                                                          ↓
                                              ┌──── 進階數據模組 ────┐
                                              │   PER, BPM, VORP,   │
                                              │   WS, VALUE_SCORE   │
                                              └──────────┬──────────┘
                                                         ↓
                                              ┌────── 薪資模組 ──────┐
                                              │  CAP_PCT, TIER,     │
                                              │  MARKET_VALUE       │
                                              └──────────┬──────────┘
                                                         ↓
                                              ┌───── 適配度模組 ─────┐
                                              │  PLAY_STYLE, ROLE,  │
                                              │  FIT_VERSATILITY    │
                                              └──────────┬──────────┘
                                                         ↓
                                              ┌──── 交易價值引擎 ────┐
                                              │  TRADE_VALUE,       │
                                              │  SURPLUS_VALUE      │
                                              └──────────┬──────────┘
                                                         ↓
                                              trade_value_ranking.csv
```
