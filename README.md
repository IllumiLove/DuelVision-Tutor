# DuelVision Tutor

即時 AI 決鬥教練 — 為 Yu-Gi-Oh! Master Duel（PC / Steam）打造的螢幕疊加輔助工具。

透過 OCR 即時讀取遊戲畫面，分析當前局勢，結合你的卡組資訊與卡片效果，由 AI 給出合法且具體的操作建議。

---

## 功能特色

- **即時螢幕擷取** — 自動偵測 Master Duel 視窗，以 mss + Win32 API 擷取遊戲畫面
- **PaddleOCR 辨識** — 使用 PP-OCRv5 (GPU) 辨識中文卡名、LP、階段等遊戲資訊
- **模糊匹配卡名** — 結合 14,000+ 張卡片資料庫（中/英文），即使 OCR 有誤差也能正確識別
- **AI 戰術建議** — 透過 DeepSeek API（或本地 Ollama）分析局勢，提供完整展開路線
- **操作合法性檢查** — 系統自動標註卡片觸發條件（特召觸發 / 通召限制 / 手坑等），預計算手牌可行操作，確保 AI 不會建議違規操作
- **透明疊加視窗** — PyQt6 置頂視窗，即時顯示 AI 建議，不影響正常遊戲
- **卡組管理** — 匯入自訂卡組，AI 會根據你的牌組內容規劃 combo 路線
- **對戰日誌** — 自動記錄每回合的遊戲狀態與 AI 建議

## 系統架構

```
src/
├── capture/        # 螢幕擷取 & 變化偵測
├── parser/         # OCR 引擎 + 遊戲狀態解析（LP、階段、手牌、場上怪獸）
├── database/       # SQLite 卡片資料庫（YGOProDeck + YGOCDB 中文名）
├── advisor/        # LLM 提示詞建構 & API 呼叫
│   └── prompts/    # 系統提示詞模板
├── deck/           # 卡組載入 & 管理
├── overlay/        # PyQt6 疊加 UI
├── logger/         # 對戰紀錄
└── main.py         # 主程式進入點

tools/              # 開發輔助工具
├── import_deck.py          # 卡組匯入
├── sync_chinese_names.py   # 同步中文卡名
└── debug_capture.py        # OCR 區域除錯截圖

data/
├── cards.db        # SQLite 卡片資料庫
├── decks/          # 卡組 JSON 檔案
└── debug/          # 除錯輸出
```

## 技術棧

| 類別 | 技術 |
|------|------|
| 語言 | Python 3.11 |
| OCR | PaddleOCR 3.x + PaddlePaddle GPU (CUDA) |
| AI | DeepSeek API / Ollama (可切換) |
| UI | PyQt6 |
| 卡片資料 | YGOProDeck API + YGOCDB (中文) |
| 模糊匹配 | rapidfuzz |
| 資料庫 | SQLite |

## 環境需求

- Windows 10/11
- Python 3.11+
- NVIDIA GPU + CUDA（用於 PaddleOCR GPU 加速）
- Master Duel 以 1920×1080 解析度運行

## 快速開始

```bash
# 1. 建立虛擬環境
python -m venv .venv
.venv\Scripts\activate

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 設定 API Key
#    在 .env 中填入 DEEPSEEK_API_KEY=your_key_here

# 4. 同步卡片資料庫（首次執行會自動同步）

# 5. 匯入你的卡組
python tools/import_deck.py

# 6. 啟動
start.bat
# 或手動執行：
set PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
python -m src.main
```

## 設定檔

編輯 `config.yaml` 調整參數：

```yaml
capture:
  target_window: "masterduel"     # 遊戲視窗名稱
  interval: 1.0                   # 掃描間隔（秒）

llm:
  provider: "deepseek"            # deepseek 或 ollama
  deepseek:
    model: "deepseek-chat"
    max_tokens: 2048
    temperature: 0.3

overlay:
  opacity: 0.88                   # 視窗透明度
  width: 420
  height: 500

deck:
  active: "你的卡組名稱"
```

## 運作流程

```
遊戲畫面 → 螢幕擷取 → 變化偵測 → PaddleOCR 辨識
                                        ↓
                               遊戲狀態解析（LP、階段、手牌、場上）
                                        ↓
                               卡片效果查詢 + 觸發條件標註
                                        ↓
                               手牌合法性分析（可通召/不可通召/特召條件）
                                        ↓
                               DeepSeek API → AI 戰術建議
                                        ↓
                               PyQt6 疊加視窗即時顯示
```

## 授權

本專案僅供個人學習與研究使用。
