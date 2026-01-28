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
```

### 執行分析

```bash
# 基本執行
python src/main_v2.py

# 執行 AI 分析（指定球隊）
python src/main_v2.py --ai-team OKC

# 示範模式
python src/main_v2.py --demo

# 啟動互動儀表板
python src/main_v2.py --dashboard
# 或
streamlit run src/dashboard/app.py
```

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
│   ├── main_v2.py              # 主程式
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