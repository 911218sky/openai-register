"""配置管理模組"""
import os


def load_dotenv(path: str = ".env") -> None:
    """載入 .env 檔案中的環境變數"""
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if not key or key in os.environ:
                    continue
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                os.environ[key] = value
    except Exception:
        pass


# 載入環境變數
load_dotenv()


class Config:
    """應用配置"""
    
    # 郵箱域名
    MAIL_DOMAIN = os.getenv("MAIL_DOMAIN", "your.domain.com").strip()
    
    # Gmail IMAP 配置
    IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com").strip()
    IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
    EMAIL_USER = os.getenv("EMAIL_USER", "").strip()
    # EMAIL_PASS 不要 strip，因為密碼可能包含空格
    EMAIL_PASS = os.getenv("EMAIL_PASS", "")
    
    # Token 輸出目錄
    TOKEN_OUTPUT_DIR = os.getenv("TOKEN_OUTPUT_DIR", "").strip()
    
    # SSL 驗證
    SSL_VERIFY = os.getenv("OPENAI_SSL_VERIFY", "1").strip().lower() not in {"0", "false", "no", "off"}
    
    # 跳過網路檢查
    SKIP_NET_CHECK = os.getenv("SKIP_NET_CHECK", "0").strip().lower() in {"1", "true", "yes", "on"}
    
    # OAuth 配置
    AUTH_URL = "https://auth.openai.com/oauth/authorize"
    TOKEN_URL = "https://auth.openai.com/oauth/token"
    CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
    REDIRECT_URI = "http://localhost:1455/auth/callback"
    SCOPE = "openid email profile offline_access"
