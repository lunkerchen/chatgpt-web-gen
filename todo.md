# ChatGPT Web Gen — 優化建議報告

> 只讀不跑，基於 `gen.py` (338 行) 與專案結構的靜態分析。

---

## 🔴 高優先 (可靠性 / 安全性)

### 1. 錯誤處理過於寬鬆
- `_load_cookies`、`_save_cookies`、`_logged_in` 都用裸 `except Exception` 吞掉所有錯誤 (L96, L117, L124)
- 建議：區分 `json.JSONDecodeError`、`cryptography.fernet.InvalidToken`、`keyring.errors.KeyringError`、`PlaywrightError` 等，各給明確訊息

### 2. 缺乏重試機制
- `_fetch()` 沒有重試，遇到網路抖動就直接失敗 (L128-136)
- `page.goto()` 沒有 retry，ChatGPT 偶發的 429/503 會直接報錯
- 建議：對 HTTP 請求加上 exponential backoff retry（3 次）

### 3. 沒有處理 ChatGPT 限流 (Rate Limiting)
- 短時間內多次呼叫可能觸發 `429 Too Many Requests`
- 現有程式碼完全沒有偵測限流並等待的邏輯
- 建議：監測 assistant 回覆文字中是否包含 "rate limit" / "too many"，自動 backoff

### 4. `_fetch()` 跨來源問題
- L130 的 `page.evaluate` 用 `fetch(url, {credentials:'include'})` 拿 blob/image URL
- 部分 `blob:` URL 或跨域圖片可能因 CORS 失敗，但只回 `None`
- 建議：fallback 到 `page.goto(url)` + screenshot 或其他下載方式

### 5. Keyring fallback 機制
- macOS Keychain / Windows Credential Manager / Linux Secret Service 行為不同
- Linux 上若沒裝 `gnome-keyring` 或 `kwallet`，`keyring.get_password` 會拋例外
- 建議：加上 `keyring.backends` 偵測，不支援時提示安裝或改用環境變數 fallback

---

## 🟡 中優先 (架構 / 可用性)

### 6. 單一巨石檔案
- `gen.py` 338 行混雜 CLI、瀏覽器、加密、圖片下載、選擇器維護
- 建議拆成：
  - `gen.py` — CLI entry
  - `src/cookies.py` — cookie 加解密
  - `src/browser.py` — browser launch / login flow
  - `src/selectors.py` — 集中管理選擇器
  - `src/download.py` — 圖片下載邏輯

### 7. 選擇器字典 `S` 結構不統一
- L47-55 的 `S` dict 混合了 `, ` 分隔的多選擇器字串，使用時用 `query_selector()` 只會取第一個
- 建議：改用 list 結構，`query_selector` 時逐一嘗試 fallback，或用 `:is()` CSS pseudo-class

### 8. 缺少設定檔 / 環境變數支援
- 所有參數都 hardcode：timeout、poll interval、URL、viewport 尺寸
- 建議：支援 `~/.config/chatgpt-web-gen/config.toml` 或環境變數覆蓋

### 9. 圖片生成失敗的 debug 資訊不完整
- L253-259 只存 screenshot + HTML，沒存 console log、network error
- 建議：加入 `page.on("console", ...)` 和 `page.on("pageerror", ...)` 的 log 收集

### 10. 沒有 headless 模式以外的選項
- `generate()` 硬寫 `headless=True` (L145)，debug 要改 code
- 建議：加 `--headed` / `--debug` flag

### 11. 登入流程的使用者體驗
- `cmd_login()` 用 polling 偵測登入 (5 分鐘 timeout)，但沒有提示目前狀態
- 建議：顯示倒數計時或 "登入已偵測" 的即時回饋、支援 `--timeout` 參數

### 12. 沒有批次處理支援
- 一次只能生一張圖，連續多個 prompt 要反覆 cold start (~8s × N)
- 建議：加 `--file prompts.txt` 模式，或在同一個 browser session 內處理多個 prompt

---

## 🟢 低優先 (工程品質 / 體驗)

### 13. 沒有測試
- 整個專案零測試，只能靠手動驗證
- 建議：至少加上 `pytest` 單元測試（cookie 加解密、選擇器解析）和 smoke test（mock Playwright）

### 14. 中英文混雜的註解
- L66-71 cookie 註解用中文、L82-86 也用中文，但 README 是英文
- 建議：統一英文或至少雙語一致

### 15. 沒有進度回饋
- 生圖期間 (最多 150s) 終端完全沉默，使用者不知道是卡住還是在跑
- 建議：用 spinner / 倒數 / 文字進度顯示（如 `tqdm` 或手刻 dots）

### 16. 無依賴鎖定
- `requirements.txt` 只有寬鬆版本 (`cloakbrowser>=0.3`)
- 建議：加入 `requirements.lock` (pip freeze) 或改用 `pip-tools`/`poetry`

### 17. 無 lint / format 設定
- 沒有 `.flake8`、`pyproject.toml`、`ruff.toml` 等
- 建議：加入 `ruff` 設定與 pre-commit hook

### 18. 無 CI/CD
- 沒有 GitHub Actions 或其他 CI 設定
- 建議：至少加 lint + type check 的 CI

### 19. `import os` 位置怪異
- L276 的 `import os` 放在 CLI 段落中間而非檔案頂部
- 應移到頂部 import 區塊

### 20. 輸出格式可擴充性
- `IMAGE:path` / `ERROR:msg` 是自訂格式，不易被其他工具解析
- 建議：加 `--json` flag 輸出 `{"status": "ok", "path": "..."}` / `{"status": "error", "message": "..."}`

### 21. `_logged_in()` 選擇器可能不穩定
- `data-testid="earth-icon"` 或 `data-testid="user-menu"` 依賴 OpenAI 前端內部標記
- 建議：加更多 fallback，例如檢查 cookie 中是否有 `__Secure-next-auth.session-token`

### 22. 沒有 `--version` flag
- 缺乏版本號追蹤，不易判斷使用者跑的是哪個版本

---

## 📊 總結

| 優先級 | 數量 | 類型 |
|--------|------|------|
| 🔴 高 | 5 | 錯誤處理、重試、限流、CORS、keyring fallback |
| 🟡 中 | 7 | 模組化、設定檔、debug、批次、headless 選項 |
| 🟢 低 | 10 | 測試、CI、lint、註解、UX、格式 |
| **合計** | **22** | |

建議優先處理 🔴 高優先的項目，它們直接影響工具在真實場景下的可靠性和安全性。
