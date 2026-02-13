# 🏀 NBA 交易價值評估系統 v2.0

一個基於運動科學數據的 NBA 球員交易價值分析工具，整合進階數據、薪資分析、適配度評估和 AI 智能建議。

## ✨ 功能特點

### 核心模組
| 模組 | 功能 | 輸出欄位 |
|------|------|----------|
| **進階數據模組** | PER/BPM/VORP/WS 計算 | `PER_APPROX`, `BPM_APPROX`, `VORP_APPROX`, `WIN_SHARES_APPROX` |
| **薪資模組** | 市場價值估算、性價比分析 | `MARKET_VALUE_M`, `SURPLUS_VALUE_M`, `CAP_PCT` |
| **適配度模組** | 10 種打法風格分類 | `PLAY_STYLE_CN`, `OFFENSIVE_ROLE`, `DEFENSIVE_ROLE` |
| **合約模組** | 剩餘年限、交易限制分析 | `CONTRACT_TYPE`, `YEARS_REMAINING`, `CONTRACT_FLEXIBILITY` |
| **AI 分析模組** | 智能球隊診斷與建議 | 自然語言報告 |

### 交易價值等級
- 🏆 **UNTOUCHABLE** - 不可交易級別
- ⭐ **FRANCHISE** - 基石球員
- 🌟 **ALL_STAR** - 全明星級別
- ✅ **QUALITY_STARTER** - 優質先發
- 📊 **ROTATION** - 輪替球員
- 🔄 **TRADEABLE** - 可交易

## 🚀 快速開始

### 安裝

```bash
# 克隆專案
git clone https://github.com/your-repo/nba-trade-value.git
cd nba-trade-value

# 安裝依賴
pip install -r requirements.txt

# 安裝開發/測試依賴（pytest / coverage / ruff）
pip install -r requirements-dev.txt
```

### 開發環境（Dev Setup）

```bash
# 建議建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 安裝執行與開發依賴
pip install -r requirements-dev.txt
```

### 執行分析

```bash
# 基本執行
python src/main.py

# 執行 AI 分析（指定球隊）
python src/main.py --ai-team OKC

# 示範模式
python src/main.py --demo

# 啟動互動儀表板
python src/main.py --dashboard
# 或
streamlit run src/dashboard/app.py

# 一鍵資料更新流程
python3 src/pipeline/run_full_refresh.py --season 2025-26 --year 2026
```

### 資料收集（可選）

```bash
# 一鍵更新整個資料與輸出流程（推薦）
python3 src/pipeline/run_full_refresh.py --season 2025-26 --year 2026

# 如需忽略快取強制重跑
python3 src/pipeline/run_full_refresh.py --season 2025-26 --year 2026 --force

# 抓取球員統計（可指定賽季）
python src/data_collection/get_player_stats.py --season 2025-26

# 抓取 ESPN 薪資（可指定年份 / 頁數）
python src/data_collection/get_salary_espn.py --year 2026 --max-pages 30

# 合併統計與薪資
python src/data_collection/fix_names_and_merge.py
```

### 測試

```bash
# 執行全部測試
python3 -m pytest -q

# 顯示更詳細結果
python3 -m pytest -v

# Phase 0 fixture regression 測試
python3 -m pytest tests/test_phase0_regression_fixtures.py -q

# 顯示 coverage（終端缺失行）
python3 -m pytest \
  --cov=src.modules.advanced_stats_module \
  --cov=src.modules.salary_module \
  --cov=src.modules.fit_module \
  --cov=src.modules.contract_module \
  --cov=src.modules.trade_value_engine \
  --cov=src.data_collection.fix_names_and_merge \
  --cov=src.data_collection.get_salary_espn \
  --cov-report=term-missing \
  --cov-fail-under=65

# 產生 HTML coverage 報告（輸出到 htmlcov/）
python3 -m pytest \
  --cov=src.modules.advanced_stats_module \
  --cov=src.modules.salary_module \
  --cov=src.modules.fit_module \
  --cov=src.modules.contract_module \
  --cov=src.modules.trade_value_engine \
  --cov=src.data_collection.fix_names_and_merge \
  --cov=src.data_collection.get_salary_espn \
  --cov-report=html

# Lint (Ruff)
ruff check .
```

### Backtest

```bash
python3 src/models/backtest.py \
  --player-data data/processed/trade_value_full.csv \
  --trades data/historical_trades/canonical_trades.csv
```

目前測試涵蓋：
- 核心分析模組（advanced stats / salary / fit / contract / trade value）
- 資料清理邏輯（名稱正規化）
- 資料收集解析邏輯（以 mock session 測試，無實際網路請求）

Coverage 設定：
- 建議門檻為 `65%`（命令中 `--cov-fail-under=65`）
- 如需調整門檻，修改命令中的 `--cov-fail-under` 數值即可

## 📊 輸出文件

```
data/processed/
├── trade_value_full.csv      # 完整數據 (52+ 欄位)
├── trade_value_ranking.csv   # 精簡排名
└── ai_report_{TEAM}.md       # AI 分析報告
```

## 🎯 使用範例

### 1. 找出最佳交易目標
```python
from src.modules.trade_value_engine import TradeValueEngine

engine = TradeValueEngine()
# 預算 $15M 以下，25 歲以下
targets = engine.get_trade_targets(df, budget_m=15, max_age=25, top_n=10)
```

### 2. 模擬交易
```python
result = engine.simulate_trade(
    df,
    team_a_gives=['Player A', 'Player B'],
    team_b_gives=['Player C']
)
print(f"薪資匹配: {result['salary_match']}")
print(f"價值差異: {result['value_difference']}")
```

### 3. AI 球隊分析
```python
from src.modules.ai_analysis_module import AIAnalysisModule

ai = AIAnalysisModule()
analysis = ai.analyze_team(df, 'OKC')
report = ai.generate_natural_language_report(analysis)
print(report)
```

### 4. 選秀權價值計算
```python
from src.modules.contract_module import ContractModule

# 第 5 順位，Top-5 保護，2 年後
value = ContractModule.get_draft_pick_value(5, "TOP_5", years_out=2)
```

## 📈 分析指標說明

### 交易價值計算公式
```
TRADE_VALUE = 
    PERF_SCORE_NORM × 0.50 (進階數據) +
    CONTRACT_SCORE_NORM × 0.25 (合約性價比) +
    FIT_SCORE_NORM × 0.25 (適配彈性)
```

### 年齡調整
| 年齡區間 | 調整分數 | 說明 |
|----------|----------|------|
| < 23 | +5 | 高潛力新秀 |
| 23-24 | +3 | 成長期 |
| 25-28 | 0 | 巔峰期 |
| 29-32 | -2 | 穩定期 |
| > 32 | -5 | 衰退風險 |

## 🏗️ 專案結構

```
nba_trade_value/
├── src/
│   ├── main.py                 # 主程式
│   ├── data_collection/        # 數據收集腳本
│   │   ├── get_player_stats.py
│   │   ├── get_salary_espn.py
│   │   └── fix_names_and_merge.py
│   ├── modules/                # 核心分析模組
│   │   ├── advanced_stats_module.py
│   │   ├── salary_module.py
│   │   ├── fit_module.py
│   │   ├── contract_module.py
│   │   ├── trade_value_engine.py
│   │   └── ai_analysis_module.py
│   └── dashboard/              # Streamlit 儀表板
│       └── app.py
├── data/
│   ├── raw/                    # 原始數據
│   └── processed/              # 處理後數據
├── requirements.txt
└── README.md
```

## 🔧 設定 AI 功能

如需使用 Claude API 進行深度分析：

```bash
# 設定環境變數
export ANTHROPIC_API_KEY="your-api-key"
```

或在 `.env` 文件中設定：
```
ANTHROPIC_API_KEY=your-api-key
```

## 📝 授權

MIT License

## 🙏 致謝

- [NBA API](https://github.com/swar/nba_api) - NBA 數據來源
- [ESPN](https://www.espn.com/nba/salaries) - 薪資數據
- [Anthropic Claude](https://www.anthropic.com) - AI 分析引擎
