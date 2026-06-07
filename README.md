# ChatGPT Web Gen

**Generate images via ChatGPT Web — no API key, just a Plus/Pro/Team account.**

```bash
pip install -r requirements.txt
playwright install chromium
python gen.py --login
python gen.py "a cinematic cyberpunk city at night"
python gen.py "put this product on a beach" --ref product.png
```

---

🌐 **Languages** — [繁體中文](docs/zh-Hant/README.md) · [日本語](docs/ja/README.md)

---

## What is this?

A single-file CLI tool that drives ChatGPT Web (chat.openai.com) through a headless browser to generate images. No API key, no server, no daemon — just your ChatGPT subscription and a terminal.

## How it works

```
gen.py
  │
  ├── 1. Launch headless Chromium (CloakBrowser)
  ├── 2. Decrypt & restore ChatGPT session cookies
  ├── 3. Open a fresh conversation
  ├── 4. Upload reference image (optional)
  ├── 5. Type prompt + send
  ├── 6. Wait for generation (poll for image)
  ├── 7. Download the generated image
  └── 8. Print IMAGE:path or ERROR:reason
```

Every invocation starts fresh — no background daemon, no state management.

## Features

- **No API key required** — works with your ChatGPT Plus/Pro/Team subscription
- **Text-to-image & image-to-image** — with `--ref` for reference-based generation
- **Stealth headless browser** — CloakBrowser + channel-override bypass bot detection
- **Encrypted session storage** — cookies encrypted via Fernet (AES-128-CBC + HMAC) with key in OS keyring
- **Zero infrastructure** — single Python file, no servers, no databases

## Setup

### Prerequisites

- **Python 3.10+**
- **ChatGPT Plus, Pro, or Team** subscription
- ~500 MB disk for Chromium (one-time download)

### Install

```bash
git clone https://github.com/lunkerchen/chatgpt-web-gen.git
cd chatgpt-web-gen

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### One-time login

```bash
python gen.py --login
```

This opens a **visible** Chrome window to `chat.openai.com`. Log in with your account, then **press Enter in the terminal**. Your session cookies are encrypted and stored via your OS keyring (macOS Keychain / Windows Credential Manager).

> **Session expiry:** ~1-2 months (OpenAI policy). Re-run `python gen.py --login` when it expires.

## Usage

### Text-to-image

```bash
python gen.py "a cute orange cat sitting on a desk, digital art style"
python gen.py "大稻埕碼頭黃昏，夕陽染紅天空，寫實攝影"
python gen.py "cinematic shot of a cyberpunk city, neon rain, 8k"
```

### Image-to-image (with reference)

```bash
python gen.py "redesign this logo in minimal style" --ref logo.png
python gen.py "put this product on a tropical beach" --ref product.jpg
python gen.py "turn this sketch into a realistic oil painting" --ref sketch.png
```

### Output format

| Status | Output |
|--------|--------|
| Success | `IMAGE:/absolute/path/to/gen_1234567890.png` |
| Failure | `ERROR:<error description>` (exit code 1) |

Generated images are saved in `./temp/`.

## Security model

| Layer | Mechanism |
|-------|-----------|
| Cookie encryption | Fernet (AES-128-CBC + HMAC SHA256) via `cryptography` |
| Key storage | OS keyring (macOS Keychain / Windows Credential Manager / Linux Secret Service) |
| Login browser | System Chrome with `channel="chrome"` to bypass Google bot detection |
| .gitignore | All session data (`cookies.enc`, `playwright_user_data/`) excluded from Git |

Attackers need **both** the encrypted file **and** OS keyring access to steal a session.

## Project structure

```
chatgpt-web-gen/
├── gen.py                  # Single-file CLI entry point (~240 lines)
├── requirements.txt        # cloakbrowser + playwright + keyring + cryptography
├── docs/
│   ├── zh-Hant/README.md   # Traditional Chinese docs
│   └── ja/README.md        # Japanese docs
├── README.md
├── LICENSE
└── .gitignore
```

**Runtime-only** (created by the tool, excluded from Git):

| Path | Contents |
|------|----------|
| `cookies.enc` | Encrypted session cookies |
| `playwright_user_data/` | Chrome profile cache (login flow) |
| `temp/` | Generated images |

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

**Debug tip:** Temporarily set `headless=False` in `gen.py` to watch the browser in action.

## Architecture

```
                   ┌──────────────────────┐
                   │    gen.py (CLI)      │
                   │                      │
  prompt ─────────>│  Playwright browser  │──> chat.openai.com
  --ref ──────────>│  (headless Chromium) │
                   │                      │<── generated image
                   └──────────────────────┘
                              │
                              ├── cookies.enc ── encrypted session
                              └── temp/ ──────── output images
```

Design trade-off: cold start (~8s per invocation) in exchange for **zero state management**.

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

MIT
