#!/usr/bin/env python3
"""
ChatGPT Web Image Generator — CLI tool.

Launches a stealth headless Chromium (CloakBrowser), logs into ChatGPT via
saved cookies, sends your prompt, and downloads the generated image.

Usage:
    ./gen.py "a cute orange cat, digital art"
    ./gen.py "put this product on a beach" --ref photo.jpg
"""
import argparse
import base64
import json
import logging
import sys
import time
from pathlib import Path

from cloakbrowser import launch
from playwright.sync_api import Browser, BrowserContext, Page

# ── Config ────────────────────────────────────
CHATGPT_URL = "https://chat.openai.com"
BROWSER_TIMEOUT = 180_000        # 180s per-page timeout
GEN_TIMEOUT = 150                # 150s max wait for image generation
POLL_INTERVAL = 1.5              # seconds between checks
SEND_DELAY = 0.5

# Paths (relative to script)
HERE = Path(__file__).parent
TEMP_DIR = HERE / "temp"
# TODO: 漏洞
COOKIE_FILE = HERE / "cookies.json"

TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────
logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("gen")
logger.setLevel(logging.INFO)

# ── Selectors (update when ChatGPT UI changes) ─
S = {
    "logged_in": '[data-testid="earth-icon"], [data-testid="user-menu"], #prompt-textarea, div[role="textbox"]',
    "chat_input": '#prompt-textarea, div[contenteditable="true"][role="textbox"], textarea[placeholder*="Message"]',
    "send": 'button[data-testid="send-button"], button:has(svg[data-icon="send"])',
    "file_input": '#upload-photos, input[type="file"]',
    "generated": 'img[alt*="已產生"], img[alt*="Generated"]',
    "streaming": 'button[data-testid="stop-button"], div[class*="streaming"], div[class*="typing"]',
    "assistant": '[data-message-author-role="assistant"]',
}


# ── Helpers ───────────────────────────────────

def _save_cookies(ctx: BrowserContext):
    """Persist cookies for next run."""
    c = ctx.cookies()
    # TODO: 漏洞
    # 問題點：當使用者執行 python gen.py --login 登入成功後，
    # 腳本會把包含 __Secure-next-auth.session-token 的極敏感 ChatGPT 登入憑證，用完全明文（Plaintext JSON）的方式直接寫入專案目錄下的
    # 風險：如果使用者不小心把這個 cookies.json 一起 git commit 推送到公開的 GitHub 倉庫，
    # 或者電腦被惡意軟體掃描，攻擊者就能直接拿走這個檔案，完全繞過 2FA 密碼驗證，直接劫持該用戶的 OpenAI 帳號！
    COOKIE_FILE.write_text(json.dumps(c, indent=2))
    logger.info(f"Saved {len(c)} cookies")


def _load_cookies(ctx: BrowserContext) -> bool:
    """Restore saved cookies. Returns True if any loaded."""
    if not COOKIE_FILE.exists():
        return False
    c = json.loads(COOKIE_FILE.read_text())
    if c:
        ctx.add_cookies(c)
        logger.info(f"Restored {len(c)} cookies")
        return True
    return False


def _logged_in(page: Page) -> bool:
    try:
        return page.wait_for_selector(S["logged_in"], timeout=10_000) is not None
    except Exception:
        return False


def _fetch(page: Page, url: str) -> bytes | None:
    """Fetch binary data via page context (has auth cookies)."""
    raw = page.evaluate("""async (url) => {
        const r = await fetch(url, {credentials:'include'});
        if (!r.ok) return null;
        const b = await r.blob();
        return Array.from(new Uint8Array(await b.arrayBuffer()));
    }""", url)
    return bytes(raw) if raw else None


def generate(prompt: str, ref: str | None = None) -> tuple:
    """
    Run the full flow: launch browser → login → upload → prompt → download.

    Returns (image_path | None, error_text | None).
    """
    browser = launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    )
    page = ctx.new_page()
    page.set_default_timeout(BROWSER_TIMEOUT)

    # ── Restore session ──────────────────────
    ok = _load_cookies(ctx)
    if ok:
        page.goto(CHATGPT_URL, wait_until="domcontentloaded")
        time.sleep(3)
        if not _logged_in(page):
            browser.close()
            return (None, "Session expired. Re-login: gen.py --login")
    else:
        browser.close()
        return (None, "No session. Run: gen.py --login")

    # ── Fresh conversation ───────────────────
    page.goto(CHATGPT_URL, wait_until="domcontentloaded")
    time.sleep(2)

    try:
        page.wait_for_selector(S["chat_input"], timeout=15_000)
    except Exception:
        browser.close()
        return (None, "ChatGPT input not found — UI may have changed.")

    # ── Upload reference image ───────────────
    if ref:
        p = Path(ref)
        if p.exists():
            fi = page.query_selector(S["file_input"])
            if fi:
                fi.set_input_files(str(p))
                logger.info(f"Uploaded {p}")
                time.sleep(2)

    # ── Type prompt ──────────────────────────
    inp = page.query_selector(S["chat_input"])
    if not inp:
        browser.close()
        return (None, "Chat input disappeared.")
    tag = inp.evaluate("el => el.tagName.toLowerCase()")
    if tag in ("textarea", "input"):
        inp.fill(prompt)
    else:
        inp.click()
        page.keyboard.type(prompt, delay=50)
    time.sleep(SEND_DELAY)

    # ── Send ─────────────────────────────────
    btn = page.query_selector(S["send"])
    if btn and btn.is_visible():
        btn.click()
    else:
        page.keyboard.press("Enter")
    time.sleep(1)
    logger.info(f"Prompt sent: {prompt[:60]}")

    # ── Wait for generation ──────────────────
    try:
        page.wait_for_selector(S["streaming"], timeout=15_000)
        logger.info("Generation started...")
    except Exception:
        logger.info("Fast response (no streaming indicator)")

    deadline = time.time() + GEN_TIMEOUT
    out_path = None
    gpt_text = None

    while time.time() < deadline:
        streaming = page.query_selector(S["streaming"])
        if not streaming:
            time.sleep(2)
            img = page.query_selector(S["generated"])
            if img:
                src = img.evaluate("el => el.getAttribute('src')")
                if src:
                    ts = int(time.time())
                    dst = TEMP_DIR / f"gen_{ts}.png"
                    logger.info(f"Image found: {src[:80]}")

                    if src.startswith("data:"):
                        _, data = src.split(",", 1)
                        dst.write_bytes(base64.b64decode(data))
                        out_path = dst
                        break
                    elif src.startswith("blob:"):
                        raw = _fetch(page, src)
                        if raw:
                            dst.write_bytes(raw)
                            out_path = dst
                            break
                    else:
                        if src.startswith("/"):
                            src = CHATGPT_URL + src
                        raw = _fetch(page, src)
                        if raw:
                            dst.write_bytes(raw)
                            out_path = dst
                            break
        else:
            time.sleep(POLL_INTERVAL)

    if not out_path:
        gpt_text = page.evaluate("""() => {
            const msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
            if (!msgs.length) return null;
            return msgs[msgs.length - 1].textContent?.trim().substring(0, 500) || null;
        }""")

    _save_cookies(ctx)
    browser.close()

    if out_path:
        return (str(out_path), None)
    return (None, gpt_text or "No image generated — unknown error.")


# ── CLI ───────────────────────────────────────

def cmd_login():
    """Interactive login helper — opens visible Chrome for manual login."""
    logger.info("Opening ChatGPT in visible browser. Log in manually, then press Enter.")
    browser = launch(headless=False)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto(CHATGPT_URL, wait_until="domcontentloaded")
    input("Press Enter after login...")
    time.sleep(2)
    if _logged_in(page):
        _save_cookies(ctx)
        logger.info("Login successful! Cookies saved.")
    else:
        logger.error("Login not detected. Try again.")
    browser.close()


def main():
    parser = argparse.ArgumentParser(description="Generate images via ChatGPT Web")
    parser.add_argument("prompt", nargs="?", help="Text prompt for image generation")
    parser.add_argument("--ref", help="Path to reference image")
    parser.add_argument("--login", action="store_true", help="Interactive ChatGPT login")
    args = parser.parse_args()

    if args.login:
        cmd_login()
        return

    while not args.prompt:
        args.prompt = input("Prompt: ").strip()

    path, err = generate(args.prompt, args.ref)
    if path:
        print(f"IMAGE:{path}")
    else:
        print(f"ERROR:{err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
