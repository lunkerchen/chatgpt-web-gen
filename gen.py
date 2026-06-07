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
import os
import sys
import time
from pathlib import Path

from cryptography.fernet import Fernet
import keyring

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

TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────
logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("gen")
logger.setLevel(logging.INFO)

# ── Selectors (update when ChatGPT UI changes) ─
S = {
    "chat_input": '#prompt-textarea, div[contenteditable="true"][role="textbox"], textarea[placeholder*="Message"]',
    "send": 'button[data-testid="send-button"], button:has(svg[data-icon="send"])',
    "file_input": '#upload-photos, input[type="file"]',
    "generated": 'img[alt*="已產生"], img[alt*="Generated"]',
    "streaming": 'button[data-testid="stop-button"], div[class*="streaming"], div[class*="typing"]',
    "assistant": '[data-message-author-role="assistant"]',
}


# ── Helpers ───────────────────────────────────

# Encrypted cookie file — paths relative to script directory
COOKIE_ENC = HERE / "cookies.enc"

def _get_or_create_key():
    """Retrieve encryption key from keyring, or generate a new one if not exists."""
    
    # 從系統金鑰庫拿取「加密鑰匙」（這把鑰匙很小，絕對不會超過 Windows 上限）
    key_str = keyring.get_password("chatgpt_web_gen", "encryption_key")
    if not key_str:
        # 如果是第一次，生成一把標準的 Fernet 鑰匙並鎖進系統
        new_key = Fernet.generate_key()
        keyring.set_password("chatgpt_web_gen", "encryption_key", new_key.decode('utf-8'))
        return new_key
    return key_str.encode('utf-8')

def _load_cookies(ctx):
    """Load encrypted session state and apply to browser context."""
    if not COOKIE_ENC.exists():
        return False
        
    try:
        
        # 1. 取得儲存在系統 Keyring 的專屬金鑰
        key = _get_or_create_key()
        f = Fernet(key)
        
        # 2. 讀取本地加密檔案並解密
        with open(COOKIE_ENC, "rb") as file:
            encrypted_data = file.read()
            
        json_str = f.decrypt(encrypted_data).decode('utf-8')
        state = json.loads(json_str)
        
        # Apply cookies from storage_state format
        cookies = state.get("cookies", [])
        if cookies:
            ctx.add_cookies(cookies)
            logger.info(f"Restored {len(cookies)} cookies.")
            return True
        
        # Fallback: try as plain cookie array (legacy format)
        ctx.add_cookies(state)
        logger.info(f"Restored session (legacy format).")
        return True
    except Exception as e:
        logger.error(f"Failed to decrypt cookies: {e}")
    return False

def _save_cookies(ctx):
    """Encrypt session data (cookies + localStorage) and save to local file."""
    try:
        # Use storage_state to capture all cookies + localStorage + sessionStorage
        state = ctx.storage_state()
        json_str = json.dumps(state)
        
        # 1. 取得（或建立）系統 Keyring 的專屬金鑰
        key = _get_or_create_key()
        f = Fernet(key)
        
        # 2. 將 Cookie 加密並寫入本地檔案
        encrypted_data = f.encrypt(json_str.encode('utf-8'))
        with open(COOKIE_ENC, "wb") as file:
            file.write(encrypted_data)
            
        logger.info(f"Session data encrypted and saved ({len(state['cookies'])} cookies).")
    except Exception as e:
        logger.error(f"Failed to save encrypted cookies: {e}")


def _logged_in(page: Page) -> bool:
    """Check if user is logged in by verifying login button is absent."""
    try:
        # ChatGPT shows login-button when logged out, hides it when logged in
        return page.evaluate("!document.querySelector('[data-testid=\"login-button\"]')")
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
        # Debug: save page state when generation fails
        dbg_dir = TEMP_DIR / "debug"
        dbg_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(dbg_dir / "fail_screenshot.png"))
        html = page.content()
        (dbg_dir / "fail_page.html").write_text(html[:50000])
        logger.info(f"Debug files saved to {dbg_dir}/")
        
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
import os

def cmd_login():
    """Interactive login helper — opens visible browser via CloakBrowser for manual login."""
    logger.info("Opening Visible Chrome via CloakBrowser. Log in manually.")
    logger.info("Auto-detecting login within 5 minutes...")
    
    from cloakbrowser import launch
    
    # Launch visible CloakBrowser
    browser = launch(headless=False)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto(CHATGPT_URL, wait_until="domcontentloaded")
    
    # Poll for login status — no manual input needed
    deadline = time.time() + 300  # 5 min timeout
    logged_in = False
    while time.time() < deadline:
        if _logged_in(page):
            logged_in = True
            break
        time.sleep(2)
    
    if logged_in:
        time.sleep(3)
        # Navigate to chatgpt.com again to ensure session token is fully established
        page.goto(CHATGPT_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        _save_cookies(ctx)
        logger.info("Login successful! Cookies saved.")
    else:
        logger.error("Login not detected within 5 minutes.")
    
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
