"""郵箱服務模組"""
import email
import imaplib
import time
from email.header import decode_header
from typing import Optional

from .config import Config
from .logger import get_logger
from .utils import extract_otp_code, generate_random_email

logger = get_logger()


class EmailService:
    """郵箱服務類"""
    
    def __init__(self):
        self.domain = Config.MAIL_DOMAIN
        self.imap_server = Config.IMAP_SERVER
        self.imap_port = Config.IMAP_PORT
        self.email_user = Config.EMAIL_USER
        self.email_pass = Config.EMAIL_PASS
    
    def get_email_and_token(self, proxies=None):
        """生成隨機郵箱地址"""
        email_addr = generate_random_email(self.domain)
        return email_addr, email_addr
    
    def _decode_subject(self, subject: str) -> str:
        """解碼郵件主題"""
        if not subject:
            return ""
        
        decoded_parts = []
        for part, encoding in decode_header(subject):
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
            else:
                decoded_parts.append(str(part))
        return ''.join(decoded_parts)
    
    def _is_openai_email(self, subject: str, from_addr: str) -> bool:
        """判斷是否為 OpenAI 驗證郵件"""
        subject_lower = subject.lower()
        from_lower = from_addr.lower()
        
        return (
            "openai" in from_lower or
            "chatgpt" in subject_lower or
            "openai" in subject_lower or
            "code is" in subject_lower
        )
    
    def get_verification_code(
        self,
        target_email: str,
        timeout: int = 120,
        check_interval: int = 3,
    ) -> str:
        """
        從 Gmail 收件箱獲取驗證碼
        
        Args:
            target_email: 目標郵箱地址（用於日誌顯示）
            timeout: 超時時間（秒）
            check_interval: 檢查間隔（秒）
            
        Returns:
            驗證碼字串，失敗返回空字串
        """
        if not self.email_user or not self.email_pass:
            logger.warning("未配置 IMAP 憑證，跳過自動獲取驗證碼")
            return ""
        
        logger.info(f"正在等待郵箱 {target_email} 的驗證碼...")
        logger.info(f"將在 {timeout} 秒內每 {check_interval} 秒檢查一次郵箱")
        
        start_time = time.time()
        mail: Optional[imaplib.IMAP4_SSL] = None
        
        try:
            # 連接到 IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_user, self.email_pass.replace(" ", ""))
            mail.select("INBOX")
            logger.info("已連接到郵箱，開始搜尋驗證碼...")
            
            attempts = 0
            while time.time() - start_time < timeout:
                attempts += 1
                
                # 每 3 次顯示一次進度
                if attempts % 3 == 0:
                    elapsed = int(time.time() - start_time)
                    logger.info(f"已等待 {elapsed} 秒，繼續檢查郵箱...")
                
                # 搜尋最近 10 封郵件
                status, messages = mail.search(None, 'ALL')
                email_ids = []
                
                if status == "OK" and messages[0]:
                    all_ids = messages[0].split()
                    email_ids = all_ids[-10:] if len(all_ids) > 10 else all_ids
                
                if attempts == 1:  # 只在第一次顯示
                    logger.info(f"檢查最近 {len(email_ids)} 封郵件...")
                
                # 從最新的郵件開始檢查
                for email_id in reversed(email_ids):
                    try:
                        status, msg_data = mail.fetch(email_id, "(RFC822)")
                        if status != "OK" or not msg_data or not msg_data[0]:
                            continue
                        
                        # 解析郵件
                        msg = email.message_from_bytes(msg_data[0][1])
                        subject = self._decode_subject(msg.get("Subject", ""))
                        from_addr = msg.get("From", "")
                        
                        # 檢查是否為 OpenAI 郵件
                        if not self._is_openai_email(subject, from_addr):
                            continue
                        
                        logger.info(f"找到 OpenAI 驗證郵件，主題: {subject}")
                        
                        # 從主題提取驗證碼
                        code = extract_otp_code(subject)
                        if code:
                            logger.info(f"成功從主題獲取驗證碼: {code}")
                            return code
                        
                        logger.debug(f"主題中未找到驗證碼: {subject}")
                        
                    except Exception as e:
                        logger.debug(f"處理郵件時出錯: {e}")
                        continue
                
                time.sleep(check_interval)
            
            logger.warning(f"超時 {timeout} 秒，未收到驗證碼")
            return ""
            
        except Exception as e:
            logger.error(f"獲取驗證碼時發生錯誤: {e}")
            return ""
        
        finally:
            # 確保關閉連接
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass
