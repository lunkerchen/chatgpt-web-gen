# 🎨 ChatGPT Web Gen

**Generate images via ChatGPT Web — no API key, just a Plus/Pro/Team account.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](gen.py)
[![Playwright](https://img.shields.io/badge/Playwright-Headless-45ba4b?logo=playwright)](https://playwright.dev)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![中文](https://img.shields.io/badge/README-繁體中文-red.svg)](README.zh-TW.md)
[![日本語](https://img.shields.io/badge/README-日本語-blue.svg)](docs/ja/README.md)

---

## What is this?

A single-file CLI tool that drives **ChatGPT Web** through a headless browser to generate images. No API key, no server, no daemon — just your ChatGPT subscription and a terminal.

## Features

| Capability | Description |
|------------|-------------|
| **No API key** | Uses your ChatGPT Plus/Pro/Team subscription directly |
| **Text → Image** | Generate from any text prompt |
| **Image → Image** | Reference-based generation with `--ref` |
| **Stealth browser** | CloakBrowser + channel override bypasses bot detection |
| **Encrypted session** | Cookies encrypted via Fernet (AES-128-CBC + HMAC), key in OS keyring |
| **Zero infra** | Single Python file, no servers, no databases |

## How it works

```
                    ┌──────────────────────┐
                    │    gen.py (CLI)      │
                    │                      │
  prompt ──────────>│  Playwright browser  │──> chat.openai.com
  --ref ───────────>│  (headless Chromium) │
                    │                      │<── generated image
                    └──────────────────────┘
                               │
                               ├── cookies.enc ── encrypted session
                               └── temp/ ──────── output images
```

Every invocation starts fresh — no background daemon, no state management. Cold start ~8s.

## Quick start

```bash
# Install
pip install -r requirements.txt
playwright install chromium

# One-time login (opens visible Chrome)
python gen.py --login

# Text-to-image
python gen.py "a cinematic cyberpunk city at night"
python gen.py "大稻埕碼頭黃昏，夕陽染紅天空，寫實攝影"

# Image-to-image (with reference)
python gen.py "put this product on a beach" --ref product.png
python gen.py "turn this sketch into a realistic oil painting" --ref sketch.png
```

## Project structure

```
chatgpt-web-gen/
├── gen.py                  # Single-file CLI entry point (~240 lines)
├── requirements.txt        # cloakbrowser + playwright + keyring + cryptography
├── README.md               # English (you are here)
├── README.zh-TW.md         # Traditional Chinese
├── docs/
│   ├── zh-Hant/README.md   # Traditional Chinese (full)
│   └── ja/README.md        # Japanese
├── LICENSE                 # MIT
└── .gitignore
```

**Runtime-only** (excluded from Git):

| Path | Contents |
|------|----------|
| `cookies.enc` | Encrypted session cookies |
| `playwright_user_data/` | Chrome profile cache (login flow) |
| `temp/` | Generated images |

## Security model

| Layer | Mechanism |
|-------|-----------|
| Cookie encryption | Fernet (AES-128-CBC + HMAC SHA256) via `cryptography` |
| Key storage | OS keyring (macOS Keychain / Windows Credential Manager / Linux Secret Service) |
| Login browser | System Chrome with `channel="chrome"` to bypass Google bot detection |
| .gitignore | All session data (`cookies.enc`, `playwright_user_data/`) excluded from Git |

Attackers need **both** the encrypted file **and** OS keyring access to steal a session.

## Selector maintenance (when ChatGPT UI changes)

ChatGPT's frontend updates frequently. If generation breaks, update the `S` dictionary at the top of `gen.py`:

| Key | Purpose | Common selectors |
|-----|---------|------------------|
| `chat_input` | Prompt textarea | `#prompt-textarea`, `div[contenteditable="true"]` |
| `send` | Send button | `button[data-testid="send-button"]` |
| `generated` | Generated image detection | `img[alt*="已產生"]` |
| `streaming` | In-progress indicator | `button[data-testid="stop-button"]` |
| `file_input` | File upload input | `input[type="file"]` |
| `assistant` | Assistant reply (error text) | `[data-message-author-role="assistant"]` |
| `logged_in` | Login status check | `[data-testid="earth-icon"]`, `#prompt-textarea` |

**Debug tip:** Set `headless=False` in `gen.py` to watch the browser in action.

## Limitations

- **Paid ChatGPT account required** (Plus/Pro/Team)
- **CLI only** — no server, no API, no queue
- **Single-threaded** — one image at a time (ChatGPT Web constraint)
- **Cookie-dependent** — session expires every 1-2 months
- **UI-fragile** — ChatGPT frontend changes can break selectors
- **Cold start** — ~8s overhead per invocation

## Related projects

| Project | Description |
|---------|-------------|
| [chatgpt-image-bot](https://github.com/lunkerchen/chatgpt-image-bot) 🤖 | Telegram Bot version — queue, admin panel, image editing, visitor auth. Same engine, multi-user friendly. |

## License

MIT — see [LICENSE](LICENSE).
