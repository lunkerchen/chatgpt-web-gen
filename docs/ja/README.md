# ChatGPT Web Gen

**API キー不要 — ChatGPT Plus/Pro/Team アカウントだけで画像生成。**

```bash
pip install -r requirements.txt
playwright install chromium
python gen.py --login
python gen.py "シネマティックなサイバーパンクシティ、夜"
python gen.py "この商品をビーチに配置" --ref product.png
```

---

🌐 **言語** — [English](../../README.md) · [繁體中文](../zh-Hant/README.md)

---

## これは何？

ヘッドレスブラウザで ChatGPT Web (chat.openai.com) を操作し、画像を生成する単一ファイルの CLI ツールです。API キー、サーバー、デーモンは一切不要 — ChatGPT のサブスクリプションとターミナルだけで動作します。

## 動作の流れ

```
gen.py
  │
  ├── 1. ヘッドレス Chromium 起動（CloakBrowser ステルス）
  ├── 2. ChatGPT セッションクッキーを復号・復元
  ├── 3. 新しい会話を開始
  ├── 4. 参照画像をアップロード（オプション）
  ├── 5. プロンプトを入力して送信
  ├── 6. 生成完了を待機（画像をポーリング）
  ├── 7. 生成画像をダウンロード
  └── 8. IMAGE:パス または ERROR:理由 を出力
```

毎回クリーンな状態で起動 — バックグラウンドデーモンも状態管理も不要です。

## 特徴

- **API キー不要** — ChatGPT Plus/Pro/Team のサブスクリプションで動作
- **テキスト→画像 & 画像→画像** — `--ref` パラメータで参照画像を使用
- **ステルスヘッドレスブラウザ** — CloakBrowser + channel オーバーライドでボット検出を回避
- **暗号化セッション保存** — クッキーを Fernet（AES-128-CBC + HMAC）で暗号化、鍵は OS キーリングに保管
- **インフラ不要** — 単一 Python ファイル、サーバーもデータベースも不要

## セットアップ

### 必要なもの

- **Python 3.10+**
- **ChatGPT Plus、Pro、または Team** サブスクリプション
- Chromium 用に約 500 MB のディスク容量（初回のみ）

### インストール

```bash
git clone https://github.com/lunkerchen/chatgpt-web-gen.git
cd chatgpt-web-gen

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 初回ログイン

```bash
python gen.py --login
```

**表示可能な** Chrome ウィンドウが開き、`chat.openai.com` にアクセスします。アカウントでログインしたら、**ターミナルで Enter キーを押します**。セッションクッキーは暗号化され、OS キーリング（macOS Keychain / Windows Credential Manager）に保存されます。

> **セッション有効期限：** 約 1-2 ヶ月（OpenAI のポリシー）。期限切れ時は `python gen.py --login` を再実行してください。

## 使い方

### テキストから画像生成

```bash
python gen.py "可愛いオレンジ猫、デスクに座る、デジタルアート"
python gen.py "台湾・大稻埕の夕暮れ、夕日で空が赤く染まる、写実写真"
python gen.py "cinematic shot of a cyberpunk city, neon rain, 8k"
```

### 参照画像から生成

```bash
python gen.py "このロゴをミニマルスタイルでリデザイン" --ref logo.png
python gen.py "この商品を熱帯のビーチに配置" --ref product.jpg
python gen.py "このスケッチを写実的な油絵に変換" --ref sketch.png
```

### 出力形式

| ステータス | 出力 |
|-----------|------|
| 成功 | `IMAGE:/絶対パス/gen_1234567890.png` |
| 失敗 | `ERROR:<エラー説明>`（exit code 1） |

生成された画像は `./temp/` に保存されます。

## セキュリティモデル

| レイヤー | 仕組み |
|----------|--------|
| クッキー暗号化 | Fernet（AES-128-CBC + HMAC SHA256）、`cryptography` ライブラリ使用 |
| 鍵の保管 | OS キーリング（macOS Keychain / Windows Credential Manager / Linux Secret Service） |
| ログインブラウザ | システム Chrome、`channel="chrome"` で Google ボット検出を回避 |
| .gitignore | 全セッションデータ（`cookies.enc`、`playwright_user_data/`）を Git から除外 |

攻撃者がセッションを奪取するには、暗号化ファイル **と** OS キーリングへのアクセスの **両方** が必要です。

## プロジェクト構成

```
chatgpt-web-gen/
├── gen.py                  # CLI エントリーポイント（約 240 行）
├── requirements.txt        # cloakbrowser + playwright + keyring + cryptography
├── docs/
│   ├── zh-Hant/README.md   # 繁体中国語ドキュメント
│   └── ja/README.md        # 日本語ドキュメント（ここ）
├── README.md               # 英語ハブ
├── LICENSE
└── .gitignore
```

**実行時に生成されるファイル**（Git から除外済み）：

| パス | 内容 |
|------|------|
| `cookies.enc` | 暗号化されたセッションクッキー |
| `playwright_user_data/` | Chrome プロファイルキャッシュ（ログイン時） |
| `temp/` | 生成された画像 |

## セレクタメンテナンス（ChatGPT UI 変更時）

ChatGPT のフロントエンドは頻繁に更新されます。画像生成が機能しなくなったら、`gen.py` 先頭の `S` ディクショナリを更新してください：

| キー | 用途 | 一般的なセレクタ |
|------|------|------------------|
| `chat_input` | プロンプト入力欄 | `#prompt-textarea`, `div[contenteditable="true"]` |
| `send` | 送信ボタン | `button[data-testid="send-button"]` |
| `generated` | 生成画像の検出 | `img[alt*="Generated"]` |
| `streaming` | 生成中インジケータ | `button[data-testid="stop-button"]` |
| `file_input` | ファイルアップロード | `input[type="file"]` |
| `assistant` | アシスタント返信（エラー時） | `[data-message-author-role="assistant"]` |
| `logged_in` | ログイン状態確認 | `[data-testid="earth-icon"]`, `#prompt-textarea` |

**デバッグのヒント：** `headless` を一時的に `False` に設定すると、ブラウザの動作を確認できます。

## アーキテクチャ

```
                   ┌──────────────────────┐
                   │    gen.py (CLI)      │
                   │                      │
  prompt ─────────>│  Playwright browser  │──> chat.openai.com
  --ref ──────────>│  (headless Chromium) │
                   │                      │<── generated image
                   └──────────────────────┘
                              │
                              ├── cookies.enc ── 暗号化セッション
                              └── temp/ ──────── 出力画像
```

設計上のトレードオフ：起動速度を犠牲に（毎回 ~8s のコールドスタート）、**状態管理ゼロ**のシンプルさを実現。

## 制限事項

- **有料 ChatGPT アカウント必須**（Plus/Pro/Team）
- **CLI のみ** — サーバー、API、キューなし
- **シングルスレッド** — 一度に 1 枚のみ生成（ChatGPT Web の制約）
- **クッキー依存** — セッションは 1-2 ヶ月で期限切れ
- **UI 脆弱性** — ChatGPT のフロントエンド変更でセレクタが機能しなくなる可能性
- **コールドスタート** — 毎回 ~8s の起動オーバーヘッド

## 関連プロジェクト

| プロジェクト | 説明 |
|-------------|------|
| [chatgpt-image-bot](https://github.com/lunkerchen/chatgpt-image-bot) 🤖 | Telegram Bot 版 — キュー、管理パネル、画像編集、訪問者認証。複数ユーザー向け |

## ライセンス

MIT
