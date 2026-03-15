"""OAuth 授權模組"""
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict

from .config import Config
from .utils import (
    jwt_claims_no_verify,
    parse_callback_url,
    pkce_verifier,
    random_state,
    sha256_b64url_no_pad,
)


@dataclass(frozen=True)
class OAuthStart:
    """OAuth 授權開始資訊"""
    auth_url: str
    state: str
    code_verifier: str
    redirect_uri: str


class OAuthClient:
    """OAuth 客戶端"""
    
    def __init__(self):
        self.auth_url = Config.AUTH_URL
        self.token_url = Config.TOKEN_URL
        self.client_id = Config.CLIENT_ID
        self.redirect_uri = Config.REDIRECT_URI
        self.scope = Config.SCOPE
    
    def generate_auth_url(self) -> OAuthStart:
        """
        生成 OAuth 授權 URL
        
        Returns:
            OAuthStart 物件，包含授權 URL 和相關參數
        """
        state = random_state()
        code_verifier = pkce_verifier()
        code_challenge = sha256_b64url_no_pad(code_verifier)

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "login",
            "id_token_add_organizations": "true",
            "codex_cli_simplified_flow": "true",
        }
        auth_url = f"{self.auth_url}?{urllib.parse.urlencode(params)}"
        return OAuthStart(
            auth_url=auth_url,
            state=state,
            code_verifier=code_verifier,
            redirect_uri=self.redirect_uri,
        )
    
    def exchange_token(
        self,
        callback_url: str,
        expected_state: str,
        code_verifier: str,
    ) -> str:
        """
        使用授權碼交換 Token
        
        Args:
            callback_url: OAuth 回調 URL
            expected_state: 預期的 state 參數
            code_verifier: PKCE verifier
            
        Returns:
            Token JSON 字串
        """
        cb = parse_callback_url(callback_url)
        
        if cb["error"]:
            desc = cb["error_description"]
            raise RuntimeError(f"OAuth 錯誤: {cb['error']}: {desc}".strip())

        if not cb["code"]:
            raise ValueError("回調 URL 缺少 ?code= 參數")
        if not cb["state"]:
            raise ValueError("回調 URL 缺少 ?state= 參數")
        if cb["state"] != expected_state:
            raise ValueError("state 參數不匹配")

        token_resp = self._post_form(
            self.token_url,
            {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "code": cb["code"],
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier,
            },
        )

        access_token = (token_resp.get("access_token") or "").strip()
        refresh_token = (token_resp.get("refresh_token") or "").strip()
        id_token = (token_resp.get("id_token") or "").strip()
        expires_in = self._to_int(token_resp.get("expires_in"))

        claims = jwt_claims_no_verify(id_token)
        email = str(claims.get("email") or "").strip()
        auth_claims = claims.get("https://api.openai.com/auth") or {}
        account_id = str(auth_claims.get("chatgpt_account_id") or "").strip()

        now = int(time.time())
        expired_rfc3339 = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + max(expires_in, 0))
        )
        now_rfc3339 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))

        config = {
            "id_token": id_token,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "account_id": account_id,
            "last_refresh": now_rfc3339,
            "email": email,
            "type": "codex",
            "expired": expired_rfc3339,
        }

        return json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    
    @staticmethod
    def _to_int(v: Any) -> int:
        """安全轉換為整數"""
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0
    
    @staticmethod
    def _post_form(url: str, data: Dict[str, str], timeout: int = 30) -> Dict[str, Any]:
        """發送 POST 表單請求"""
        body = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        try:
            context = None
            if not Config.SSL_VERIFY:
                context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                raw = resp.read()
                if resp.status != 200:
                    raise RuntimeError(
                        f"Token 交換失敗: {resp.status}: {raw.decode('utf-8', 'replace')}"
                    )
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            raise RuntimeError(
                f"Token 交換失敗: {exc.code}: {raw.decode('utf-8', 'replace')}"
            ) from exc
