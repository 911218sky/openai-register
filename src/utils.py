"""工具函數模組"""
import base64
import hashlib
import json
import random
import re
import secrets
import string
import urllib.parse
from typing import Any, Dict


def generate_password(length: int = 16) -> str:
    """生成符合 OpenAI 要求的隨機強密碼（大小寫+數字+特殊字符）"""
    upper = random.choices(string.ascii_uppercase, k=2)
    lower = random.choices(string.ascii_lowercase, k=2)
    digits = random.choices(string.digits, k=2)
    specials = random.choices("!@#$%&*", k=2)
    rest_len = length - 8
    pool = string.ascii_letters + string.digits + "!@#$%&*"
    rest = random.choices(pool, k=rest_len)
    chars = upper + lower + digits + specials + rest
    random.shuffle(chars)
    return "".join(chars)


def generate_random_email(domain: str) -> str:
    """生成隨機前綴的郵箱地址"""
    prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{prefix}@{domain}"


def b64url_no_pad(raw: bytes) -> str:
    """Base64 URL 編碼（無填充）"""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def sha256_b64url_no_pad(s: str) -> str:
    """SHA256 雜湊後進行 Base64 URL 編碼"""
    return b64url_no_pad(hashlib.sha256(s.encode("ascii")).digest())


def random_state(nbytes: int = 16) -> str:
    """生成隨機狀態字串"""
    return secrets.token_urlsafe(nbytes)


def pkce_verifier() -> str:
    """生成 PKCE verifier"""
    return secrets.token_urlsafe(64)


def decode_jwt_segment(seg: str) -> Dict[str, Any]:
    """解碼 JWT 片段（不驗證簽名）"""
    raw = (seg or "").strip()
    if not raw:
        return {}
    pad = "=" * ((4 - (len(raw) % 4)) % 4)
    try:
        decoded = base64.urlsafe_b64decode((raw + pad).encode("ascii"))
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        return {}


def jwt_claims_no_verify(id_token: str) -> Dict[str, Any]:
    """從 ID Token 中提取聲明（不驗證簽名）"""
    if not id_token or id_token.count(".") < 2:
        return {}
    payload_b64 = id_token.split(".")[1]
    return decode_jwt_segment(payload_b64)


def parse_callback_url(callback_url: str) -> Dict[str, Any]:
    """解析 OAuth 回調 URL"""
    candidate = callback_url.strip()
    if not candidate:
        return {"code": "", "state": "", "error": "", "error_description": ""}

    if "://" not in candidate:
        if candidate.startswith("?"):
            candidate = f"http://localhost{candidate}"
        elif any(ch in candidate for ch in "/?#") or ":" in candidate:
            candidate = f"http://{candidate}"
        elif "=" in candidate:
            candidate = f"http://localhost/?{candidate}"

    parsed = urllib.parse.urlparse(candidate)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    fragment = urllib.parse.parse_qs(parsed.fragment, keep_blank_values=True)

    for key, values in fragment.items():
        if key not in query or not query[key] or not (query[key][0] or "").strip():
            query[key] = values

    def get1(k: str) -> str:
        v = query.get(k, [""])
        return (v[0] or "").strip()

    code = get1("code")
    state = get1("state")
    error = get1("error")
    error_description = get1("error_description")

    if code and not state and "#" in code:
        code, state = code.split("#", 1)

    if not error and error_description:
        error, error_description = error_description, ""

    return {
        "code": code,
        "state": state,
        "error": error,
        "error_description": error_description,
    }


def extract_otp_code(content: str) -> str:
    """從郵件內容中提取 OTP 驗證碼"""
    if not content:
        return ""
    patterns = [
        r"Your ChatGPT code is\s*(\d{6})",
        r"ChatGPT code is\s*(\d{6})",
        r"verification code to continue:\s*(\d{6})",
        r"Subject:.*?(\d{6})",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
    fallback = re.search(r"(?<!\d)(\d{6})(?!\d)", content)
    return fallback.group(1) if fallback else ""
