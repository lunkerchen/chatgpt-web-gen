# ChatGPT Web Gen

**生成圖片無需 API Key — 只用 ChatGPT Plus/Pro 帳號 + CloakBrowser**
**Generate images via ChatGPT Web — no API key needed, just a paid account**

```bash
pip install -r requirements.txt
python gen.py --login
python gen.py "a cinematic cyberpunk city at night"
python gen.py "把這張產品照放到沙灘上" --ref product.png
```

---

## 📦 關聯專案 / Related

| 專案 | 說明 |
|------|------|
| **[chatgpt-image-bot](https://github.com/lunkerchen/chatgpt-image-bot)** 🤖 | **Telegram Bot 版本** — 排隊佇列、管理員面板、圖片修改模式、訪客認證、管理員通知。這是 CLI 版的 Bot 包裝，適合多人使用 |
| `chatgpt-web-gen` ← 你正在看這裡 | CLI 版本 — 單機單人，一行指令生圖 |

想讓朋友、客戶或團隊也透過 Telegram 生圖？直接走 Bot 版，功能更完整。

---

## 如何運作 / How it works

```
gen.py
  │
  ├── 1. Launch headless Chromium (CloakBrowser)
  ├── 2. Restore saved ChatGPT session cookies
  ├── 3. Open fresh conversation
  ├── 4. Upload reference image (optional)
  ├── 5. Type prompt + send
  ├── 6. Wait for generation (poll streaming indicator)
  ├── 7. Download the generated image
  └── 8. Print IMAGE:path or ERROR:reason
```

All in one command — no servers, no daemons, no API setup.

---

## 安裝 / Setup

### 環境需求 / Requirements

- **Python 3.10+**
- **ChatGPT Plus, Pro, or Team account** — 生圖需要付費方案
- ~500MB 硬碟空間給 Chromium 引擎（一次性下載）

### 安裝步驟 / Install

```bash
git clone https://github.com/lunkerchen/chatgpt-web-gen.git
cd chatgpt-web-gen

# 建立虛擬環境（建議）
python3 -m venv .venv
source .venv/bin/activate

# 安裝相依套件
pip install -r requirements.txt

# 下載 Chromium 瀏覽器引擎
playwright install chromium
```

### 一次性登入 / One-time login

```bash
python gen.py --login
```

這會打開一個 **可見的** Chrome 視窗到 `chat.openai.com`。
用你的帳號登入後，**在終端機按 Enter**。

Session cookie 會儲存到 `cookies.json`，之後就可以 headless 模式使用。

> **Cookie 有效期限：** 約 1-2 個月（OpenAI 政策）。
> 過期時重新執行 `python gen.py --login` 即可，舊的 `cookies.json` 會自動覆蓋。

---

## 使用方式 / Usage

### 文生圖 / Text-to-image

```bash
python gen.py "a cute orange cat sitting on a desk, digital art style"
python gen.py "大稻埕碼頭黃昏，夕陽染紅天空，寫實攝影"
python gen.py "cinematic shot of a cyberpunk city, neon rain, 8k"
```

### 以圖生圖 / Image-to-image (with reference)

```bash
python gen.py "用極簡風格重新設計這個 logo" --ref logo.png
python gen.py "把這個產品放到熱帶沙灘上" --ref product.jpg
python gen.py "把這個素描變成寫實油畫" --ref sketch.png
```

### 輸出格式 / Output format

| 狀態 | 輸出 |
|------|------|
| 成功 | `IMAGE:/absolute/path/to/gen_1234567890.png` |
| 失敗 | `ERROR:<錯誤說明>`（exit code 1） |

生成的圖片存放在 `./temp/` 目錄下。

---

## 實際範例 / Examples

### 產品照變體

```bash
python gen.py "show this mug on a wooden table with morning sunlight" --ref mug_photo.jpg
```

### 風格轉換

```bash
python gen.py "この写真をジブリ風にしてください" --ref photo.jpg
```

### 批次生成（shell loop）

```bash
for prompt in "cat" "dog" "bird"; do
    python gen.py "cute $prompt, watercolor style"
done
```

---

## 專案結構 / Project structure

```
chatgpt-web-gen/
├── gen.py              # 單檔 CLI 入口（263 行）
├── cookies.json        # ChatGPT session（--login 自動產生，已 gitignore）
├── temp/               # 生成圖片（已 gitignore）
├── requirements.txt    # cloakbrowser + playwright
├── README.md
└── LICENSE
```

---

## 疑難排解 / Troubleshooting

### `ModuleNotFoundError: No module named 'cloakbrowser'`

套件未安裝：

```bash
pip install -r requirements.txt
playwright install chromium
```

### `ERROR:No session`

找不到 `cookies.json`，請執行：

```bash
python gen.py --login
```

### `ERROR:Session expired`

Cookie 已過期，重新登入：

```bash
python gen.py --login
```

### 瀏覽器打開但登入頁面沒載入

檢查網路連線，需要能訪問 `chat.openai.com`。

### 圖片生成卡住或逾時

可能原因：

- ChatGPT 正在生成（可能需要 60-90 秒）
- UI 有變更 — selector 可能過期（見下方 Selector 維護章節）
- ChatGPT 伺服器負載過高

腳本會等待最多 150 秒後放棄。

### 生成圖片品質不佳

ChatGPT Web 會根據你的帳號等級和使用的模型決定輸出解析度，此工具只下載 ChatGPT 產生的結果。

---

## Selector 維護（UI 改版時必讀）

ChatGPT 的前端時常更新。當生成失效時，`gen.py` 頂端的 `S` dictionary 很可能需要更新：

| Key | 用途 | 常見 DOM selector |
|-----|------|-------------------|
| `chat_input` | 提示詞輸入框 | `#prompt-textarea`, `div[contenteditable="true"]` |
| `send` | 送出按鈕 | `button[data-testid="send-button"]` |
| `generated` | 圖片生成完成的檢測 | `img[alt*="已產生"]` |
| `streaming` | 生成中的指示器 | `button[data-testid="stop-button"]` |
| `file_input` | 檔案上傳 input | `input[type="file"]` |
| `assistant` | 助理回覆（失敗文字） | `[data-message-author-role="assistant"]` |
| `logged_in` | 登入狀態確認 | `[data-testid="earth-icon"]`, `#prompt-textarea` |

Selector 除錯技巧：

```bash
# 取消 gen.py 中的 debug 註解來儲存螢幕截圖
# 或者暫時把 headless 設為 False
```

---

## 架構說明 / Architecture notes

```
                   ┌──────────────────────┐
                   │    gen.py (CLI)      │
                   │                      │
  prompt ─────────>│  Playwright browser  │──> chat.openai.com
  --ref ──────────>│  (headless Chromium) │
                   │                      │<── generated image
                   └──────────────────────┘
                              │
                              ├── cookies.json ── session persistence
                              └── temp/ ──────── output images
```

每次執行都會**啟動全新瀏覽器實例**，沒有常駐背景程序。每次呼叫都是自包含的：

1. 啟動 Chromium（~8s 冷啟動）
2. 還原 cookie
3. 生成圖片（~30-60s）
4. 儲存 cookie（供下次使用）
5. 關閉瀏覽器
6. 輸出圖片路徑

這個設計的取捨：犧牲啟動速度，換來零狀態管理的簡單性。

---

## 限制 / Limitations

- **需要付費 ChatGPT 帳號**（Plus/Pro/Team）
- **僅 CLI** — 無伺服器、無 API、無佇列
- **單執行緒** — 每次只能生成一張（ChatGPT Web 限制）
- **Cookie 依賴** — session 每 1-2 個月過期
- **UI 脆弱** — ChatGPT 前端改版可能導致 selector 失效
- **冷啟動** — 每次啟動新瀏覽器（~8s 開銷）

---

## License

MIT
