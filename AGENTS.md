# AGENTS.md - chatgpt-web-gen

## What
單檔 CLI 工具，用 headless browser 操作 ChatGPT Web 生成圖片。不需要 API key，靠 ChatGPT Plus/Pro/Team 訂閱。

## Tech
- Python (單檔 `gen.py`)
- playwright + cloakbrowser (stealth browser automation)
- cookies 用 Fernet 加密存 OS keyring

## Commands
```bash
python gen.py "prompt"                    # text-to-image
python gen.py "prompt" --ref path.jpg     # image-to-image
python gen.py --headless                  # 無頭模式
python gen.py --model dalle-3             # 選模型
```

## Convention
- 保持單檔架構，不要拆多檔案
- cookies 加密處理，不要明文存
- 登入邏輯和生成邏輯分開
- 錯誤處理要優雅（登入過期提示重登，不要直接 crash）
- todo.md 的優先級：P0 修登入 > P1 修生成 > P2 優化
