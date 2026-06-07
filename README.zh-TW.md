# 🎨 ChatGPT Web Gen

**無需 API Key — 只用 ChatGPT Plus/Pro/Team 帳號，透過瀏覽器自動化生圖。**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](gen.py)
[![Playwright](https://img.shields.io/badge/Playwright-Headless-45ba4b?logo=playwright)](https://playwright.dev)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![English](https://img.shields.io/badge/README-English-green.svg)](README.md)
[![日本語](https://img.shields.io/badge/README-日本語-blue.svg)](docs/ja/README.md)

---

## 這是什麼？

一個單檔 CLI 工具，透過**無頭瀏覽器**操控 ChatGPT Web 來生成圖片。不需要 API Key、不需要伺服器、不需要背景程序——只要你有 ChatGPT 付費帳號和一個終端機。

## 功能特色

| 功能 | 說明 |
|------|------|
| **不需要 API Key** | 直接用 ChatGPT Plus/Pro/Team 訂閱 |
| **文生圖** | 任何文字提示詞即可生成 |
| **以圖生圖** | 使用 `--ref` 參數搭配參考圖片 |
| **隱匿瀏覽器** | CloakBrowser + channel 覆蓋繞過機器人偵測 |
| **加密 Session** | Cookie 經 Fernet (AES-128-CBC + HMAC) 加密，金鑰存 OS Keyring |
| **零基礎設施** | 單一 Python 檔案，無伺服器無資料庫 |

## 運作流程

```
                    ┌──────────────────────┐
                    │    gen.py (CLI)      │
                    │                      │
  prompt ──────────>│  Playwright browser  │──> chat.openai.com
  --ref ───────────>│  (headless Chromium) │
                    │                      │<── generated image
                    └──────────────────────┘
                               │
                               ├── cookies.enc ── 加密 session
                               └── temp/ ──────── 輸出圖片
```

每次執行都是全新開始，無常駐程序，無需管理狀態。冷啟動 ~8s。

## 快速開始

```bash
# 安裝
pip install -r requirements.txt
playwright install chromium

# 一次性登入（開啟可見 Chrome 視窗）
python gen.py --login

# 文生圖
python gen.py "賽博龐克城市夜景，電影級畫質"
python gen.py "可愛的橘貓坐在書桌上，數位藝術風格"

# 以圖生圖（附參考圖片）
python gen.py "把這個產品放到沙灘上" --ref product.png
python gen.py "把這個素描變成寫實油畫" --ref sketch.png
```

## 專案結構

```
chatgpt-web-gen/
├── gen.py                  # 單檔 CLI 入口（約 240 行）
├── requirements.txt        # cloakbrowser + playwright + keyring + cryptography
├── README.md               # 英文主檔
├── README.zh-TW.md         # 繁體中文（你正在看這裡）
├── docs/
│   ├── zh-Hant/README.md   # 繁體中文（完整版）
│   └── ja/README.md        # 日文
├── LICENSE                 # MIT
└── .gitignore
```

**執行時產生**（已排除在 Git 外）：

| 路徑 | 內容 |
|------|------|
| `cookies.enc` | 加密的 Session cookie |
| `playwright_user_data/` | Chrome 瀏覽器快取（登入流程） |
| `temp/` | 生成的圖片 |

## 安全架構

| 層級 | 機制 |
|------|------|
| Cookie 加密 | Fernet (AES-128-CBC + HMAC SHA256)，使用 `cryptography` |
| 金鑰儲存 | OS Keyring (macOS Keychain / Windows Credential Manager / Linux Secret Service) |
| 登入瀏覽器 | 系統 Chrome，`channel="chrome"` 繞過機器人偵測 |
| .gitignore | 所有 Session 資料已排除在 Git 外 |

攻擊者需要**同時取得**加密檔案和 OS Keyring 存取權才能竊取 Session。

## Selector 維護（ChatGPT UI 改版時）

ChatGPT 前端頻繁更新。生成失效時請更新 `gen.py` 頂端的 `S` dictionary：

| Key | 用途 | 常見 Selector |
|-----|------|---------------|
| `chat_input` | 提示詞輸入框 | `#prompt-textarea`, `div[contenteditable="true"]` |
| `send` | 送出按鈕 | `button[data-testid="send-button"]` |
| `generated` | 圖片生成完成 | `img[alt*="已產生"]` |
| `streaming` | 生成中指示器 | `button[data-testid="stop-button"]` |
| `file_input` | 檔案上傳 | `input[type="file"]` |
| `assistant` | 助理回覆（錯誤文字） | `[data-message-author-role="assistant"]` |
| `logged_in` | 登入狀態確認 | `[data-testid="earth-icon"]`, `#prompt-textarea` |

**除錯技巧：** 暫時把 `headless` 設為 `False` 就能看到瀏覽器實際操作。

## 限制

- **需要付費 ChatGPT 帳號**（Plus/Pro/Team）
- **僅 CLI** — 無伺服器、無 API、無佇列
- **單執行緒** — 每次只能生成一張
- **Cookie 依賴** — Session 每 1-2 個月過期
- **UI 脆弱** — 前端改版可能導致 selector 失效
- **冷啟動** — 每次 ~8s 開銷

## 關聯專案

| 專案 | 說明 |
|------|------|
| [chatgpt-image-bot](https://github.com/lunkerchen/chatgpt-image-bot) 🤖 | Telegram Bot 版本 — 排隊佇列、管理面板、圖片修改、訪客認證。適合多人使用 |

## License

MIT — 詳見 [LICENSE](LICENSE)。
