# 🎨 ChatGPT Web Gen

**無需 API Key — 只用 ChatGPT Plus/Pro/Team 帳號，透過瀏覽器自動化生圖。**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](../../gen.py)
[![Playwright](https://img.shields.io/badge/Playwright-Headless-45ba4b?logo=playwright)](https://playwright.dev)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![English](https://img.shields.io/badge/README-English-green.svg)](../../README.md)
[![中文首頁](https://img.shields.io/badge/README-首頁-red.svg)](../../README.zh-TW.md)
[![日本語](https://img.shields.io/badge/README-日本語-blue.svg)](../ja/README.md)

## 這是什麼？

一個單檔 CLI 工具，透過無頭瀏覽器操控 ChatGPT Web (chat.openai.com) 來生成圖片。不需要 API Key、不需要伺服器、不需要背景程序——只要你有 ChatGPT 付費帳號和一個終端機。

## 運作流程

```
gen.py
  │
  ├── 1. 啟動無頭 Chromium（CloakBrowser 反偵測）
  ├── 2. 解密並還原 ChatGPT session cookie
  ├── 3. 開啟新的對話
  ├── 4. 上傳參考圖片（選擇性）
  ├── 5. 輸入提示詞並送出
  ├── 6. 等待生成（輪詢圖片出現）
  ├── 7. 下載生成的圖片
  └── 8. 輸出 IMAGE:路徑 或 ERROR:原因
```

每次執行都是全新開始——沒有常駐背景程序，不需要管理狀態。

## 功能特色

- **不需要 API Key** — 用你的 ChatGPT Plus/Pro/Team 訂閱即可
- **文生圖 + 以圖生圖** — `--ref` 參數支援參考圖片
- **隱匿無頭瀏覽器** — CloakBrowser + channel 覆蓋繞過機器人偵測
- **加密 Session 儲存** — Cookie 透過 Fernet（AES-128-CBC + HMAC）加密，金鑰存放於 OS Keyring
- **零基礎設施** — 單一 Python 檔案，不需要伺服器或資料庫

## 安裝

### 環境需求

- **Python 3.10+**
- **ChatGPT Plus、Pro 或 Team** 付費方案
- 約 500 MB 硬碟空間給 Chromium 引擎（一次性下載）

### 安裝步驟

```bash
git clone https://github.com/lunkerchen/chatgpt-web-gen.git
cd chatgpt-web-gen

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 一次性登入

```bash
python gen.py --login
```

這會打開一個**可見的** Chrome 視窗到 `chat.openai.com`。用你的帳號登入後，**在終端機按 Enter**。

Session cookie 會經過加密後儲存，加密金鑰存放於你的作業系統 Keyring（macOS Keychain / Windows Credential Manager）。

> **Cookie 有效期限：** 約 1-2 個月（OpenAI 政策）。過期時重新執行 `python gen.py --login` 即可。

## 使用方式

### 文生圖

```bash
python gen.py "可愛的橘貓坐在書桌上，數位藝術風格"
python gen.py "大稻埕碼頭黃昏，夕陽染紅天空，寫實攝影"
python gen.py "cinematic shot of a cyberpunk city, neon rain, 8k"
```

### 以圖生圖（附參考圖片）

```bash
python gen.py "用極簡風格重新設計這個 logo" --ref logo.png
python gen.py "把這個產品放到熱帶沙灘上" --ref product.jpg
python gen.py "把這個素描變成寫實油畫" --ref sketch.png
```

### 輸出格式

| 狀態 | 輸出 |
|------|------|
| 成功 | `IMAGE:/絕對路徑/gen_1234567890.png` |
| 失敗 | `ERROR:<錯誤說明>`（exit code 1） |

生成的圖片存放在 `./temp/` 目錄下。

## 安全架構

| 層級 | 機制 |
|------|------|
| Cookie 加密 | Fernet（AES-128-CBC + HMAC SHA256），使用 `cryptography` 套件 |
| 金鑰儲存 | OS Keyring（macOS Keychain / Windows Credential Manager / Linux Secret Service） |
| 登入瀏覽器 | 系統 Chrome，使用 `channel="chrome"` 繞過 Google 機器人偵測 |
| .gitignore | 所有 Session 資料（`cookies.enc`、`playwright_user_data/`）已排除 |

攻擊者需要**同時取得**加密檔案和 OS Keyring 存取權才能竊取 Session。

## 專案結構

```
chatgpt-web-gen/
├── gen.py                  # 單檔 CLI 入口（約 240 行）
├── requirements.txt        # cloakbrowser + playwright + keyring + cryptography
├── docs/
│   ├── zh-Hant/README.md   # 繁體中文文件（你正在看這裡）
│   └── ja/README.md        # 日文文件
├── README.md               # 英文主文件（Hub）
├── LICENSE
└── .gitignore
```

**執行時產生的檔案**（已排除在 Git 之外）：

| 路徑 | 內容 |
|------|------|
| `cookies.enc` | 加密的 Session cookie |
| `playwright_user_data/` | Chrome 瀏覽器快取（登入流程） |
| `temp/` | 生成的圖片 |

## Selector 維護（ChatGPT UI 改版時必讀）

ChatGPT 的前端時常更新。當生成失效時，更新 `gen.py` 頂端的 `S` dictionary：

| Key | 用途 | 常見 DOM selector |
|-----|------|-------------------|
| `chat_input` | 提示詞輸入框 | `#prompt-textarea`, `div[contenteditable="true"]` |
| `send` | 送出按鈕 | `button[data-testid="send-button"]` |
| `generated` | 圖片生成完成的檢測 | `img[alt*="已產生"]` |
| `streaming` | 生成中的指示器 | `button[data-testid="stop-button"]` |
| `file_input` | 檔案上傳 input | `input[type="file"]` |
| `assistant` | 助理回覆（失敗文字） | `[data-message-author-role="assistant"]` |
| `logged_in` | 登入狀態確認 | `[data-testid="earth-icon"]`, `#prompt-textarea` |

**除錯技巧：** 暫時把 `headless` 設為 `False` 就能看到瀏覽器視窗的實際操作。

## 架構說明

```
                   ┌──────────────────────┐
                   │    gen.py (CLI)      │
                   │                      │
  prompt ─────────>│  Playwright browser  │──> chat.openai.com
  --ref ──────────>│  (headless Chromium) │
                   │                      │<── generated image
                   └──────────────────────┘
                              │
                              ├── cookies.enc ── 加密 session
                              └── temp/ ──────── 輸出圖片
```

設計取捨：犧牲啟動速度（每次 ~8s 冷啟動），換來**零狀態管理的簡單性**。

## 限制

- **需要付費 ChatGPT 帳號**（Plus/Pro/Team）
- **僅 CLI** — 無伺服器、無 API、無佇列
- **單執行緒** — 每次只能生成一張（ChatGPT Web 限制）
- **Cookie 依賴** — Session 每 1-2 個月過期
- **UI 脆弱** — ChatGPT 前端改版可能導致 selector 失效
- **冷啟動** — 每次啟動新瀏覽器（~8s 開銷）

## 關聯專案

| 專案 | 說明 |
|------|------|
| [chatgpt-image-bot](https://github.com/lunkerchen/chatgpt-image-bot) 🤖 | Telegram Bot 版本 — 排隊佇列、管理員面板、圖片修改模式、訪客認證。適合多人使用 |

## License

MIT
