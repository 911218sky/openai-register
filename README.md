# OpenAI Register

自動化 OpenAI 帳號註冊與 AI API 代理管理工具。

## 功能特點

### 🤖 OpenAI 自動註冊

- 自動生成隨機郵箱和強密碼
- 支援 Gmail IMAP 自動獲取驗證碼
- 支援代理（HTTP/HTTPS/SOCKS5）
- 批量註冊和循環模式
- 自動保存 Token 和帳號資訊

### 🚀 CLI Proxy API

- 支援多種 AI API（Gemini、Claude、Codex、Vertex 等）
- 統一管理多個 API 金鑰
- 智能路由和自動重試
- Docker 一鍵部署

> 基於 [CLIProxyAPIPlus](https://github.com/router-for-me/CLIProxyAPIPlus) 整合

---

## 快速開始

### 安裝

```bash
# 克隆專案
git clone https://github.com/911218sky/openai-register.git
cd openai-register

# 安裝依賴
uv sync

# 配置環境變數
cp .env.example .env
# 編輯 .env 填入你的配置
```

### OpenAI 自動註冊

```bash
# 測試單次註冊
uv run python main.py --once

# 註冊 5 個帳號
uv run python main.py -c 5

# 使用代理註冊 10 個帳號
uv run python main.py -p http://127.0.0.1:7890 -c 10

# 無限循環註冊，間隔 30-120 秒
uv run python main.py -smin 30 -smax 120
```

### CLI Proxy API

```bash
# 進入目錄
cd CLIProxyAPI

# 配置檔案
cp config.example.yaml config.yaml
# 編輯 config.yaml 填入你的 API 金鑰

# 啟動服務
docker-compose up -d

# 訪問 API
# http://localhost:8317
```

---

## 命令列參數

| 參數 | 說明 | 範例 |
|------|------|------|
| `-c, --count` | 註冊帳號數量（0=無限） | `-c 5` |
| `-p, --proxy` | 代理地址 | `-p http://127.0.0.1:7890` |
| `-smin, --sleep-min` | 最短等待秒數 | `-smin 10` |
| `-smax, --sleep-max` | 最長等待秒數 | `-smax 60` |
| `--once` | 只運行一次（測試用） | `--once` |
| `-d, --debug` | 啟用調試模式 | `-d` |

---

## 環境變數配置

建立 `.env` 檔案：

```env
# 郵箱配置
MAIL_DOMAIN=gmail.com

# Gmail IMAP（自動獲取驗證碼）
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=your-app-password

# 輸出目錄
TOKEN_OUTPUT_DIR=./tokens

# 網路設定
OPENAI_SSL_VERIFY=1
SKIP_NET_CHECK=0
```

### Gmail 應用程式密碼設定

1. 前往 [Google 帳戶安全性](https://myaccount.google.com/security)
2. 啟用「兩步驟驗證」
3. 前往 [應用程式密碼](https://myaccount.google.com/apppasswords)
4. 生成密碼並填入 `.env` 的 `EMAIL_PASS`

---

## 輸出檔案

- `tokens/token_<email>_<timestamp>.json` - Token 資訊
- `tokens/accounts.txt` - 帳號記錄（格式：`email----password`）

---

## 注意事項

1. 建議使用穩定的代理服務
2. 設定合理的等待時間（15-60 秒）避免 IP 被封
3. 不要將 `.env` 和 `config.yaml` 提交到版本控制
4. 本工具僅供學習和研究使用

---

## 常見問題

**Q: 為什麼需要 Gmail 應用程式密碼？**  
A: Gmail 安全政策要求使用應用程式密碼存取 IMAP。

**Q: 可以不配置 IMAP 嗎？**  
A: 可以，程式會提示手動輸入驗證碼。

**Q: 註冊失敗怎麼辦？**  
A: 檢查代理、使用 `-d` 查看日誌、確認 IMAP 配置、增加等待時間。

---

## 致謝

- OpenAI 註冊工具基於 [gaojilingjuli](https://www.youtube.com/@gaojilingjuli) 的原始工作
- CLI Proxy API 整合自 [CLIProxyAPIPlus](https://github.com/router-for-me/CLIProxyAPIPlus)

感謝原作者的貢獻！

---

## 授權

GNU Affero General Public License v3.0

---

⭐ 如果這個專案對你有幫助，請給個星星支持一下！
