"""OpenAI 註冊器模組"""
import json
import random
import re
import time
import urllib.parse
from typing import Any, Optional, Tuple

from curl_cffi import requests

from .config import Config
from .email_service import EmailService
from .logger import get_logger
from .oauth import OAuthClient
from .utils import decode_jwt_segment, generate_password

logger = get_logger()


class OpenAIRegistrar:
    """OpenAI 自動註冊器"""
    
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.oauth_client = OAuthClient()
        self.email_service = EmailService()
    
    def check_network(self) -> bool:
        """
        檢查網路連接和 IP 位置
        
        Returns:
            True 如果網路正常，False 否則
        """
        if Config.SKIP_NET_CHECK:
            return True
        
        try:
            s = requests.Session(proxies=self.proxies, impersonate="safari")
            trace = s.get(
                "https://cloudflare.com/cdn-cgi/trace",
                proxies=self.proxies,
                verify=Config.SSL_VERIFY,
                timeout=10,
            )
            trace_text = trace.text
            loc_re = re.search(r"^loc=(.+)$", trace_text, re.MULTILINE)
            loc = loc_re.group(1) if loc_re else None
            logger.info(f"當前 IP 所在地: {loc}")
            
            if loc in ("CN", "HK"):
                raise RuntimeError("檢查代理哦 - 所在地不支持")
            return True
        except Exception as e:
            logger.error(f"網路連接檢查失敗: {e}")
            return False
    
    def _post_with_retry(
        self,
        session: requests.Session,
        url: str,
        headers: dict,
        data: Any = None,
        json_body: Any = None,
        timeout: int = 30,
        retries: int = 2,
    ) -> Any:
        """帶重試的 POST 請求"""
        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                if json_body is not None:
                    return session.post(
                        url,
                        headers=headers,
                        json=json_body,
                        proxies=self.proxies,
                        verify=Config.SSL_VERIFY,
                        timeout=timeout,
                    )
                return session.post(
                    url,
                    headers=headers,
                    data=data,
                    proxies=self.proxies,
                    verify=Config.SSL_VERIFY,
                    timeout=timeout,
                )
            except Exception as e:
                last_error = e
                if attempt >= retries:
                    break
                time.sleep(2 * (attempt + 1))
        if last_error:
            raise last_error
        raise RuntimeError("請求失敗")
    
    def register(self) -> Tuple[Optional[str], Optional[str]]:
        """
        執行註冊流程
        
        Returns:
            (token_json, password) 元組，失敗時返回 (None, None)
            特殊情況：返回 ("retry_403", None) 表示遇到 403 錯誤需要重試
        """
        # 檢查網路
        if not self.check_network():
            return None, None
        
        # 獲取郵箱
        email, dev_token = self.email_service.get_email_and_token(self.proxies)
        if not email or not dev_token:
            return None, None
        logger.info(f"成功獲取臨時郵箱: {email}")
        
        # 生成 OAuth URL
        oauth = self.oauth_client.generate_auth_url()
        
        try:
            s = requests.Session(proxies=self.proxies, impersonate="safari")
            
            # 訪問授權頁面
            resp = s.get(oauth.auth_url, proxies=self.proxies, verify=True, timeout=15)
            did = s.cookies.get("oai-did")
            logger.info(f"Device ID: {did}")
            
            # 準備註冊數據
            signup_body = f'{{"username":{{"value":"{email}","kind":"email"}},"screen_hint":"signup"}}'
            sen_req_body = f'{{"p":"","id":"{did}","flow":"authorize_continue"}}'
            
            # 獲取 Sentinel token
            sen_resp = requests.post(
                "https://sentinel.openai.com/backend-api/sentinel/req",
                headers={
                    "origin": "https://sentinel.openai.com",
                    "referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html?sv=20260219f9f6",
                    "content-type": "text/plain;charset=UTF-8",
                },
                data=sen_req_body,
                proxies=self.proxies,
                impersonate="safari",
                verify=Config.SSL_VERIFY,
                timeout=15,
            )
            
            if sen_resp.status_code != 200:
                logger.error(f"Sentinel 異常攔截，狀態碼: {sen_resp.status_code}")
                return None, None
            
            sen_token = sen_resp.json()["token"]
            sentinel = f'{{"p": "", "t": "", "c": "{sen_token}", "id": "{did}", "flow": "authorize_continue"}}'
            
            # 提交註冊表單
            signup_resp = s.post(
                "https://auth.openai.com/api/accounts/authorize/continue",
                headers={
                    "referer": "https://auth.openai.com/create-account",
                    "accept": "application/json",
                    "content-type": "application/json",
                    "openai-sentinel-token": sentinel,
                },
                data=signup_body,
                proxies=self.proxies,
                verify=Config.SSL_VERIFY,
            )
            signup_status = signup_resp.status_code
            logger.info(f"提交註冊表單狀態: {signup_status}")
            
            if signup_status == 403:
                logger.error("提交註冊表單返回 403，將在10秒後重試...")
                return "retry_403", None
            if signup_status != 200:
                logger.error("提交註冊表單失敗")
                logger.debug(signup_resp.text)
                return None, None
            
            # 註冊密碼
            password = generate_password()
            register_body = json.dumps({"password": password, "username": email})
            logger.info(f"生成隨機密碼: {password[:4]}****")
            
            pwd_resp = s.post(
                "https://auth.openai.com/api/accounts/user/register",
                headers={
                    "referer": "https://auth.openai.com/create-account/password",
                    "accept": "application/json",
                    "content-type": "application/json",
                    "openai-sentinel-token": sentinel,
                },
                data=register_body,
                proxies=self.proxies,
                verify=Config.SSL_VERIFY,
            )
            logger.info(f"提交註冊(密碼)狀態: {pwd_resp.status_code}")
            if pwd_resp.status_code != 200:
                logger.debug(pwd_resp.text)
                return None, None
            
            # 處理郵箱驗證
            register_json = pwd_resp.json()
            register_continue = register_json.get("continue_url", "")
            register_page = (register_json.get("page") or {}).get("type", "")
            
            need_otp = "email-verification" in register_continue or "verify" in register_continue
            if not need_otp and register_page:
                need_otp = "verification" in register_page or "otp" in register_page
            
            if need_otp:
                logger.info("需要郵箱驗證，請輸入驗證碼")
                
                # 觸發發送 OTP
                if register_continue:
                    otp_send_url = register_continue
                    if not otp_send_url.startswith("http"):
                        otp_send_url = f"https://auth.openai.com{otp_send_url}"
                    logger.info(f"觸發發送 OTP: {otp_send_url}")
                    otp_send_resp = self._post_with_retry(
                        s,
                        otp_send_url,
                        headers={
                            "referer": "https://auth.openai.com/create-account/password",
                            "accept": "application/json",
                            "content-type": "application/json",
                            "openai-sentinel-token": sentinel,
                        },
                        json_body={},
                        timeout=30,
                        retries=2,
                    )
                    logger.info(f"OTP 發送狀態: {otp_send_resp.status_code}")
                    
                    # 隨機等待郵件系統處理
                    wait_time = random.randint(3, 15)
                    logger.info(f"等待 {wait_time} 秒讓郵件系統處理...")
                    time.sleep(wait_time)
                
                # 獲取驗證碼
                code = ""
                
                # 如果配置了 IMAP，先嘗試自動獲取
                if self.email_service.email_user and self.email_service.email_pass:
                    logger.info("嘗試自動從郵箱獲取驗證碼...")
                    code = self.email_service.get_verification_code(
                        target_email=email,
                        timeout=120,
                        check_interval=3,
                    )
                    
                    # 獲取到驗證碼後隨機等待，避免提交太快
                    if code:
                        wait_time = random.randint(3, 15)
                        logger.info(f"等待 {wait_time} 秒後提交驗證碼...")
                        time.sleep(wait_time)
                
                # 如果自動獲取失敗，要求手動輸入
                if not code:
                    code = input("\n[*] 請輸入收到的驗證碼: ").strip()
                
                if not code:
                    logger.error("未能獲取驗證碼")
                    return None, None
                
                # 驗證驗證碼
                logger.info("開始校驗驗證碼...")
                code_resp = self._post_with_retry(
                    s,
                    "https://auth.openai.com/api/accounts/email-otp/validate",
                    headers={
                        "referer": "https://auth.openai.com/email-verification",
                        "accept": "application/json",
                        "content-type": "application/json",
                        "openai-sentinel-token": sentinel,
                    },
                    json_body={"code": code},
                    timeout=30,
                    retries=2,
                )
                logger.info(f"驗證碼校驗狀態: {code_resp.status_code}")
                if code_resp.status_code != 200:
                    logger.debug(code_resp.text)
            else:
                logger.info("密碼註冊無需郵箱驗證")
            
            # 創建帳戶
            create_account_body = '{"name":"Neo","birthdate":"2000-02-20"}'
            logger.info("開始創建帳戶...")
            create_account_resp = self._post_with_retry(
                s,
                "https://auth.openai.com/api/accounts/create_account",
                headers={
                    "referer": "https://auth.openai.com/about-you",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=create_account_body,
                timeout=30,
                retries=2,
            )
            create_account_status = create_account_resp.status_code
            logger.info(f"帳戶創建狀態: {create_account_status}")
            
            if create_account_status != 200:
                logger.debug(create_account_resp.text)
                return None, None
            
            # 獲取 workspace
            auth_cookie = s.cookies.get("oai-client-auth-session")
            if not auth_cookie:
                logger.error("未能獲取到授權 Cookie")
                return None, None
            
            auth_json = decode_jwt_segment(auth_cookie.split(".")[0])
            workspaces = auth_json.get("workspaces") or []
            if not workspaces:
                logger.error("授權 Cookie 裡沒有 workspace 資訊")
                return None, None
            workspace_id = str((workspaces[0] or {}).get("id") or "").strip()
            if not workspace_id:
                logger.error("無法解析 workspace_id")
                return None, None
            
            # 選擇 workspace
            select_body = f'{{"workspace_id":"{workspace_id}"}}'
            logger.info("開始選擇 workspace...")
            select_resp = self._post_with_retry(
                s,
                "https://auth.openai.com/api/accounts/workspace/select",
                headers={
                    "referer": "https://auth.openai.com/sign-in-with-chatgpt/codex/consent",
                    "content-type": "application/json",
                },
                data=select_body,
                timeout=30,
                retries=2,
            )
            
            if select_resp.status_code != 200:
                logger.error(f"選擇 workspace 失敗，狀態碼: {select_resp.status_code}")
                logger.debug(select_resp.text)
                return None, None
            
            continue_url = str((select_resp.json() or {}).get("continue_url") or "").strip()
            if not continue_url:
                logger.error("workspace/select 響應裡缺少 continue_url")
                return None, None
            
            # 跟隨重定向獲取授權碼
            current_url = continue_url
            for _ in range(6):
                final_resp = s.get(
                    current_url,
                    allow_redirects=False,
                    proxies=self.proxies,
                    verify=Config.SSL_VERIFY,
                    timeout=15,
                )
                location = final_resp.headers.get("Location") or ""
                
                if final_resp.status_code not in [301, 302, 303, 307, 308]:
                    break
                if not location:
                    break
                
                next_url = urllib.parse.urljoin(current_url, location)
                if "code=" in next_url and "state=" in next_url:
                    # 交換 token
                    token_json = self.oauth_client.exchange_token(
                        callback_url=next_url,
                        code_verifier=oauth.code_verifier,
                        expected_state=oauth.state,
                    )
                    return token_json, password
                current_url = next_url
            
            logger.error("未能在重定向鏈中捕獲到最終 Callback URL")
            return None, None
            
        except Exception as e:
            logger.error(f"運行時發生錯誤: {e}")
            return None, None
