# DuelVision Tutor — 開發文檔

> **即時遊戲畫面辨識 + AI 決鬥教練建議系統**
> 目標：在 Yu-Gi-Oh! Master Duel (Steam PC) 對戰時，即時擷取畫面、解析遊戲狀態，由 AI 給出世界冠軍級決鬥建議。

---

## 1. 專案概覽

| 項目 | 說明 |
|---|---|
| **名稱** | DuelVision Tutor |
| **類型** | 即時 AI 決鬥教學輔助工具（純建議，不自動操作） |
| **平台** | Windows PC（Steam 版 Master Duel） |
| **開發語言** | Python 3.11+ |
| **AI 後端** | DeepSeek API（主要）；保留本地 Ollama 切換介面 |
| **硬體需求** | i7 12th+ / 16GB+ RAM / RTX 3060+（OCR GPU 加速） |

---

## 2. 系統架構

```
┌─────────────────────────────────────────────────────────┐
│                    DuelVision Tutor                      │
│                                                         │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │ Screen   │──▶│ Game State   │──▶│ LLM Advisor    │  │
│  │ Capture  │   │ Parser       │   │ (DeepSeek API) │  │
│  │ (mss)    │   │ (PaddleOCR + │   │                │  │
│  └──────────┘   │  Template    │   └───────┬────────┘  │
│                 │  Matching)   │           │            │
│                 └──────────────┘           ▼            │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │ Card     │◀─▶│ Battle Log   │   │ Overlay UI     │  │
│  │ Database │   │ Recorder     │   │ (PyQt6 透明    │  │
│  │ (SQLite) │   │              │   │  置頂視窗)     │  │
│  └──────────┘   └──────────────┘   └────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 資料流

```
截圖 (每 1~2 秒)
  │
  ▼
變化偵測（比對前一幀關鍵區域像素差異）
  │ 有變化
  ▼
OCR + 模板匹配 → 結構化遊戲狀態 JSON
  │
  ▼
查詢卡片資料庫 → 補充完整卡片效果文字
  │
  ▼
組裝 Prompt（遊戲狀態 + 卡組資訊 + 歷史紀錄）
  │
  ▼
呼叫 DeepSeek API → 取得建議
  │
  ▼
Overlay 顯示建議（置頂透明視窗）
  │
  ▼
記錄到 Battle Log
```

---

## 3. 模組設計

### 3.1 截圖模組 (`capture/`)

| 項目 | 說明 |
|---|---|
| **功能** | 定位 Master Duel 視窗，快速截圖 |
| **核心庫** | `mss`（高速截圖）+ `win32gui`（視窗定位） |
| **截圖頻率** | 預設 1 秒/次，偵測到變化時加速到 0.5 秒/次 |
| **變化偵測** | 比對關鍵區域（生命值、場地、手牌區）的像素哈希，無變化時跳過後續流程 |

**關鍵邏輯：**
- 用 `win32gui.FindWindow()` 找到 Master Duel 視窗 handle
- 取得視窗 rect，用 `mss` 截取該區域
- 支援不同解析度自動適配（以 1920x1080 為基準，按比例縮放 ROI）

### 3.2 遊戲狀態解析模組 (`parser/`)

| 項目 | 說明 |
|---|---|
| **功能** | 從截圖中提取遊戲狀態 |
| **OCR 引擎** | PaddleOCR（GPU 加速，中文辨識最佳） |
| **模板匹配** | OpenCV `matchTemplate` 用於辨識階段圖示、按鈕狀態等 |
| **輸出** | 結構化 `GameState` 物件 |

**解析目標（ROI 區域）：**

| 區域 | 辨識方式 | 辨識內容 |
|---|---|---|
| 我方手牌 | OCR + 圖像比對 | 卡名列表 |
| 我方場上 | OCR + 模板匹配 | 怪獸名/ATK/DEF/表示形式 |
| 對手場上 | OCR + 模板匹配 | 怪獸名/ATK/DEF/表示形式 |
| 我方 LP | OCR | 數字 |
| 對手 LP | OCR | 數字 |
| 遊戲階段 | 模板匹配 | DP/SP/M1/BP/M2/EP |
| 墓地/除外 | OCR（展開時） | 卡片列表 |
| 鏈結提示 | 模板匹配 | 是否有可觸發效果 |

**`GameState` 資料結構：**

```python
@dataclass
class GameState:
    phase: str                    # "DRAW", "STANDBY", "MAIN1", "BATTLE", "MAIN2", "END"
    turn_player: str              # "self" or "opponent"
    my_lp: int
    opp_lp: int
    my_hand: list[str]            # 卡名列表
    my_field: list[FieldCard]     # 場上卡片
    opp_field: list[FieldCard]    # 對手場上
    my_graveyard: list[str]       # 墓地（展開時才有）
    my_banished: list[str]        # 除外區（展開時才有）
    chain_prompt: bool            # 是否出現鏈結提示
    turn_count: int               # 回合數
    timestamp: float

@dataclass
class FieldCard:
    name: str
    atk: int | None
    def_: int | None
    position: str                 # "ATK", "DEF", "SET"
    zone: str                     # "MONSTER_1"~"MONSTER_5", "SPELL_1"~"SPELL_5"
```

### 3.3 卡片資料庫模組 (`database/`)

| 項目 | 說明 |
|---|---|
| **功能** | 儲存所有遊戲王卡片資料，供 AI 查詢效果文字 |
| **資料來源** | [YGOProDeck API](https://db.ygoprodeck.com/api-guide/) |
| **本地儲存** | SQLite 資料庫 |
| **更新策略** | 首次啟動全量下載，之後每週增量更新 |

**資料表設計：**

```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY,       -- YGOProDeck card ID
    name_en TEXT NOT NULL,
    name_zh TEXT,                  -- 中文卡名
    card_type TEXT,                -- Monster/Spell/Trap
    sub_type TEXT,                 -- Normal/Effect/Fusion/Synchro/Xyz/Link/Ritual
    attribute TEXT,                -- DARK/LIGHT/FIRE/WATER/EARTH/WIND/DIVINE
    race TEXT,                     -- 種族
    level INTEGER,
    atk INTEGER,
    def INTEGER,
    description_en TEXT,           -- 英文效果
    description_zh TEXT,           -- 中文效果
    archetype TEXT,                -- 所屬系列 (e.g. "Snake-Eye")
    updated_at TIMESTAMP
);

CREATE INDEX idx_cards_name_zh ON cards(name_zh);
CREATE INDEX idx_cards_name_en ON cards(name_en);
CREATE INDEX idx_cards_archetype ON cards(archetype);
```

### 3.4 卡組管理模組 (`deck/`)

| 項目 | 說明 |
|---|---|
| **功能** | 管理使用者的卡組列表 |
| **卡組輸入** | 截圖辨識模式：截取卡組編輯畫面 → OCR 讀取所有卡名 |
| **儲存格式** | JSON 檔 |

**卡組結構：**

```json
{
  "name": "蛇眼",
  "created_at": "2026-03-22",
  "main_deck": ["蛇眼灰燼", "效果遮蔽者", "灰流麗", ...],
  "extra_deck": ["蛇眼鳳凰", ...],
  "side_deck": []
}
```

### 3.5 LLM 建議引擎 (`advisor/`)

| 項目 | 說明 |
|---|---|
| **功能** | 根據遊戲狀態生成決鬥建議 |
| **主要 API** | DeepSeek Chat API (`deepseek-chat`) |
| **備選** | 本地 Ollama（Qwen2.5-7B 等小模型） |
| **回應格式** | 固定 JSON schema，方便 Overlay 解析顯示 |

**System Prompt 設計（核心）：**

```
你是「DuelVision Tutor」—— 一位世界冠軍級的遊戲王 Master Duel 教練。
你對每一張卡的效果、每一個系列的 combo 路線、每一個 meta 牌組的弱點都瞭如指掌。

你的任務：根據當前遊戲狀態，給出最佳行動建議。

規則：
1. 永遠以「教學」口吻回答，既告訴玩家「做什麼」也解釋「為什麼」
2. 考慮對手可能的手坑（灰流麗、增殖的G、無限泡影、幽鬼兔等）
3. 預判對手可能的反制，給出應對方案
4. 建議必須具體到卡名和操作順序
5. 風格：自信、專業、偶爾毒舌但有道理

輸出格式（嚴格 JSON）：
{
  "priority_action": "最優先要做的操作（一句話）",
  "action_steps": [
    {"step": 1, "action": "具體操作", "reason": "為什麼"},
    {"step": 2, "action": "具體操作", "reason": "為什麼"}
  ],
  "warnings": ["注意事項1", "注意事項2"],
  "win_assessment": "當前局面評估（優勢/劣勢/均勢）"
}
```

**Prompt 組裝流程：**

```
System Prompt（AI 人設 + 輸出格式規範）
    +
User Prompt = 遊戲狀態 + 我方卡組完整列表 + 相關卡片效果文字 + 最近 N 回合行動紀錄
    ↓
DeepSeek API → JSON 回應 → 解析 → Overlay 顯示
```

**延遲控制：**
- 使用 streaming 模式，先顯示 `priority_action`（通常 0.5 秒內回來）
- 完整回應在 1~2 秒內完成
- 設定 `max_tokens = 500` 控制回應長度，避免過慢

### 3.6 Overlay 顯示模組 (`overlay/`)

| 項目 | 說明 |
|---|---|
| **功能** | 透明置頂視窗顯示 AI 建議 |
| **框架** | PyQt6（輕量、原生 Windows 支援佳） |
| **視窗特性** | 無邊框、半透明背景、Always-on-Top、可拖曳定位 |
| **顯示內容** | 最優先行動 + 步驟列表 + 注意事項 |

**UI 設計草案：**

```
┌────────────────────────────────────┐
│ 🎯 DuelVision Tutor          [≡]  │  ← 可拖曳標題列
├────────────────────────────────────┤
│                                    │
│ ▶ 召喚蛇眼灰燼，觸發效果連鎖      │  ← 最優先行動（大字）
│                                    │
│ ① 通召蛇眼灰燼                     │  ← 步驟
│   → 觸發搜索，對手可能丟灰流       │
│ ② 若被灰流，改用效果遮蔽者保護     │
│ ③ 連鎖成功後融合出蛇眼鳳凰         │
│                                    │
│ ⚠ 對手可能有無限泡影               │  ← 警告
│ ⚠ 留一張手坑防反殺                 │
│                                    │
│ 局面：我方優勢                      │  ← 評估
│                                    │
│ 截圖: 0.8s | AI: 1.2s | 更新 3s前  │  ← 狀態列
└────────────────────────────────────┘
```

**PyQt6 視窗關鍵設定：**
- `Qt.WindowType.WindowStaysOnTopHint` — 置頂
- `Qt.WindowType.FramelessWindowHint` — 無邊框
- `setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)` — 透明
- 背景色：`rgba(20, 20, 30, 220)` — 深色半透明
- 字體：等寬字體，綠色/白色/黃色配色

### 3.7 對戰紀錄模組 (`logger/`)

| 項目 | 說明 |
|---|---|
| **功能** | 記錄每場對戰的完整狀態變化與 AI 建議 |
| **儲存** | JSON Lines 格式（一行一條紀錄） |
| **用途** | 1) 回顧覆盤 2) 作為未來 prompt 的歷史參考 |

**紀錄結構：**

```json
{
  "match_id": "2026-03-22_001",
  "timestamp": 1742616000,
  "turn": 3,
  "phase": "MAIN1",
  "game_state": { ... },
  "ai_suggestion": { ... },
  "user_action": "followed / ignored / unknown"
}
```

**學習機制（Phase 1）：**
- 記錄最近 50 場對戰紀錄
- 每次 prompt 附帶「最近 3 場遇到相同系列牌組」的紀錄摘要
- AI 可以參考過去的模式來改進建議

---

## 4. 技術選型

| 類別 | 技術 | 選擇原因 |
|---|---|---|
| 截圖 | `mss` | 最快的 Python 截圖庫，支援指定區域 |
| 視窗操作 | `pywin32` | Windows 原生 API，精準定位視窗 |
| OCR | `PaddleOCR` | 中文辨識精度最高，GPU 加速 (CUDA) |
| 圖像處理 | `OpenCV` (`cv2`) | 模板匹配、圖像預處理、ROI 裁切 |
| 圖像哈希 | `imagehash` | 快速比對畫面變化 |
| LLM API | `openai` SDK | DeepSeek API 相容 OpenAI 協議 |
| 本地 LLM | `ollama` | 備選本地模型方案 |
| UI | `PyQt6` | 高效能原生 overlay 視窗 |
| 資料庫 | `sqlite3`（內建） | 卡片資料庫，無需額外安裝 |
| HTTP | `httpx` | 非同步 HTTP 請求（YGOProDeck API） |
| 設定管理 | `pydantic-settings` | 型別安全的設定檔管理 |
| 日誌 | `loguru` | 簡潔好用的日誌庫 |

---

## 5. 專案結構

```
DuelVision Tutor/
├── docs/
│   └── DEVELOPMENT.md              # 本文件
├── src/
│   ├── __init__.py
│   ├── main.py                     # 主入口，啟動所有模組
│   ├── config.py                   # 設定檔載入 (pydantic-settings)
│   │
│   ├── capture/                    # 截圖模組
│   │   ├── __init__.py
│   │   ├── screen.py               # mss 截圖 + 視窗定位
│   │   └── change_detect.py        # 畫面變化偵測
│   │
│   ├── parser/                     # 遊戲狀態解析
│   │   ├── __init__.py
│   │   ├── ocr_engine.py           # PaddleOCR 封裝
│   │   ├── template_matcher.py     # OpenCV 模板匹配
│   │   ├── game_state.py           # GameState 資料結構
│   │   └── regions.py              # ROI 區域定義 (各解析度)
│   │
│   ├── database/                   # 卡片資料庫
│   │   ├── __init__.py
│   │   ├── card_db.py              # SQLite CRUD
│   │   ├── ygoprodeck.py           # YGOProDeck API 同步
│   │   └── cards.db                # SQLite 資料庫檔案 (git ignored)
│   │
│   ├── deck/                       # 卡組管理
│   │   ├── __init__.py
│   │   ├── manager.py              # 卡組 CRUD
│   │   └── ocr_import.py           # 截圖辨識導入卡組
│   │
│   ├── advisor/                    # LLM 建議引擎
│   │   ├── __init__.py
│   │   ├── engine.py               # LLM 呼叫封裝
│   │   ├── prompt_builder.py       # Prompt 組裝
│   │   └── prompts/
│   │       └── system.txt          # System prompt 模板
│   │
│   ├── overlay/                    # Overlay UI
│   │   ├── __init__.py
│   │   ├── window.py               # PyQt6 主視窗
│   │   └── styles.py               # QSS 樣式定義
│   │
│   └── logger/                     # 對戰紀錄
│       ├── __init__.py
│       └── battle_log.py           # 紀錄讀寫
│
├── assets/                         # 靜態資源
│   └── templates/                  # 模板匹配用的圖片
│       ├── phase_draw.png
│       ├── phase_main1.png
│       ├── phase_battle.png
│       └── ...
│
├── data/                           # 運行時資料 (git ignored)
│   ├── decks/                      # 卡組 JSON
│   ├── logs/                       # 對戰紀錄
│   └── cards.db                    # 卡片資料庫
│
├── config.yaml                     # 使用者設定檔
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 6. 設定檔 (`config.yaml`)

```yaml
# DuelVision Tutor 設定

# 擷取設定
capture:
  target_window: "masterduel"       # 視窗標題關鍵字
  interval: 1.0                     # 截圖間隔（秒）
  fast_interval: 0.5                # 偵測到變化時的加速間隔
  base_resolution: [1920, 1080]     # 基準解析度

# OCR 設定
ocr:
  engine: "paddleocr"
  language: "chinese_cht"           # 繁體中文
  use_gpu: true

# LLM 設定
llm:
  provider: "deepseek"              # deepseek / ollama
  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"  # 從環境變數讀取
    model: "deepseek-chat"
    base_url: "https://api.deepseek.com"
    max_tokens: 500
    temperature: 0.3
  ollama:
    model: "qwen2.5:7b"
    base_url: "http://localhost:11434"

# Overlay 設定
overlay:
  opacity: 0.88                     # 視窗透明度
  width: 420
  height: 500
  font_size: 14
  position: "right"                 # 預設在右側螢幕

# 紀錄設定
logger:
  enabled: true
  max_matches: 100                  # 最多保留幾場紀錄
  history_context: 3                # prompt 中附帶最近幾場相同牌組紀錄

# 資料庫設定
database:
  auto_update: true
  update_interval_days: 7
```

---

## 7. 開發階段

### Phase 0：環境建置 & 基礎設施
- [x] 建立專案結構
- [ ] 建立虛擬環境 + 安裝依賴
- [ ] 設定檔載入（pydantic-settings）
- [ ] 日誌系統（loguru）

### Phase 1：截圖 & OCR 核心
- [ ] 實作截圖模組（mss + win32gui 視窗定位）
- [ ] 實作變化偵測
- [ ] 建立 ROI 區域定義（1080p 基準）
- [ ] PaddleOCR 引擎封裝
- [ ] 模板匹配（遊戲階段辨識）
- [ ] GameState 解析器整合測試

### Phase 2：卡片資料庫
- [ ] YGOProDeck API 串接
- [ ] SQLite 資料庫建立 + 全量下載
- [ ] 卡名模糊匹配（OCR 結果可能有誤差）
- [ ] 卡組截圖辨識導入

### Phase 3：LLM 建議引擎
- [ ] DeepSeek API 串接
- [ ] System Prompt 設計 & 調優
- [ ] Prompt 組裝邏輯（狀態 + 卡片效果 + 歷史）
- [ ] Streaming 回應處理
- [ ] 回應 JSON 解析 + 錯誤處理

### Phase 4：Overlay UI
- [ ] PyQt6 透明置頂視窗
- [ ] 建議內容渲染
- [ ] 狀態列（延遲、更新時間）
- [ ] 拖曳定位 + 位置記憶
- [ ] 全域熱鍵（可選）

### Phase 5：主程式整合
- [ ] 主迴圈：截圖 → 解析 → 建議 → 顯示
- [ ] 多執行緒 / asyncio 協調各模組
- [ ] 對戰紀錄模組

### Phase 6：學習 & 優化
- [ ] 歷史紀錄 RAG 注入 prompt
- [ ] OCR 精度調優（閾值、預處理）
- [ ] 延遲優化
- [ ] 錯誤恢復 & 穩定性

---

## 8. 關鍵技術細節

### 8.1 Master Duel 視窗截圖

```python
# 核心截圖邏輯概念
import mss
import win32gui

def find_game_window():
    """找到 Master Duel 視窗並返回其座標"""
    def callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "masterduel" in title.lower():
                results.append(hwnd)
    results = []
    win32gui.EnumWindows(callback, results)
    if results:
        rect = win32gui.GetWindowRect(results[0])
        return {"left": rect[0], "top": rect[1],
                "width": rect[2]-rect[0], "height": rect[3]-rect[1]}
    return None

def capture_screen(region):
    with mss.mss() as sct:
        img = sct.grab(region)
        return np.array(img)  # BGR numpy array
```

### 8.2 變化偵測策略

不是每一幀都需要送進 OCR + LLM，只有遊戲狀態真的改變時才需要：

```python
import imagehash
from PIL import Image

class ChangeDetector:
    """比對關鍵區域的感知哈希值"""
    def __init__(self, threshold=5):
        self.prev_hashes = {}
        self.threshold = threshold

    def has_changed(self, frame, regions: dict) -> bool:
        for name, roi in regions.items():
            crop = frame[roi[1]:roi[3], roi[0]:roi[2]]
            h = imagehash.phash(Image.fromarray(crop))
            prev = self.prev_hashes.get(name)
            if prev is not None and abs(h - prev) > self.threshold:
                self.prev_hashes[name] = h
                return True
            self.prev_hashes[name] = h
        return False
```

### 8.3 DeepSeek API 呼叫（相容 OpenAI SDK）

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-deepseek-key",
    base_url="https://api.deepseek.com"
)

def get_advice(system_prompt: str, user_prompt: str) -> dict:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=500,
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)
```

### 8.4 OCR 精度提升策略

Master Duel 的 UI 有一些特殊挑戰：
- **卡名字體**：遊戲使用特殊字體，OCR 可能誤讀
- **背景干擾**：卡圖背景會影響文字辨識

**解決方案：**
1. **預處理**：灰度化 → 二值化 → 降噪，提升文字對比度
2. **模糊匹配**：OCR 結果用 fuzzy match 與卡片資料庫比對，修正誤差
3. **快取**：相同區域如果內容沒變就複用上次辨識結果

```python
from rapidfuzz import process

def match_card_name(ocr_text: str, card_names: list[str]) -> str | None:
    """用模糊匹配修正 OCR 誤差"""
    result = process.extractOne(ocr_text, card_names, score_cutoff=70)
    return result[0] if result else None
```

---

## 9. 依賴清單 (`requirements.txt`)

```
# 截圖 & 圖像處理
mss>=9.0
opencv-python>=4.9
numpy>=1.26
Pillow>=10.0
imagehash>=4.3

# OCR
paddlepaddle-gpu>=2.6        # PaddlePaddle GPU 版
paddleocr>=2.8

# 視窗操作 (Windows)
pywin32>=306

# LLM API
openai>=1.50                  # DeepSeek 相容 OpenAI SDK

# UI
PyQt6>=6.7

# 資料庫 & 資料處理
httpx>=0.27                   # 非同步 HTTP
rapidfuzz>=3.6                # 模糊字串匹配
pydantic>=2.7
pydantic-settings>=2.3

# 日誌
loguru>=0.7

# 開發工具
ruff                          # Linter + Formatter
```

---

## 10. 環境變數

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

---

## 11. 風險 & 注意事項

| 風險 | 影響 | 緩解措施 |
|---|---|---|
| OCR 精度不足 | 無法正確辨識卡名 | 模糊匹配 + 資料庫修正 + 預處理調優 |
| LLM 延遲過高 | 建議來不及 | Streaming + 限制 token 數 + 快取相似局面 |
| Master Duel 更新 UI | ROI 區域偏移 | 設計彈性 ROI 設定，可手動校準 |
| API 費用 | DeepSeek 按 token 計費 | 只在狀態變化時呼叫、限制 prompt 長度 |
| 反作弊偵測 | 理論上純截圖+overlay 不修改記憶體，風險低 | 不注入遊戲程序、不模擬操作 |

---

## 12. 未來擴展（Phase 7+）

- **Vision LLM 模式**：直接把截圖送給支援圖片的 LLM（如 DeepSeek-VL 未來開放 API 時），省略 OCR 步驟
- **對手牌組辨識**：根據對手出的前幾張牌，預測對手牌組並調整策略
- **Fine-tune 模型**：用大量對戰紀錄 fine-tune 小模型，離線也能用
- **對戰回放分析**：戰後逐回合分析，指出每一步的最佳/次佳選擇
- **多語言支援**：英文/日文 UI 辨識

---

*文檔建立日期：2026-03-22*
*版本：v0.1-draft*
