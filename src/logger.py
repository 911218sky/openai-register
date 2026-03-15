"""日誌管理模組"""
import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日誌格式化器"""
    
    # ANSI 顏色代碼
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 綠色
        'WARNING': '\033[33m',    # 黃色
        'ERROR': '\033[31m',      # 紅色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m',       # 重置
    }
    
    # 日誌級別前綴
    PREFIXES = {
        'DEBUG': '[DEBUG]',
        'INFO': '[*]',
        'WARNING': '[!]',
        'ERROR': '[Error]',
        'CRITICAL': '[CRITICAL]',
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日誌記錄"""
        # 獲取顏色和前綴
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        prefix = self.PREFIXES.get(record.levelname, '[*]')
        reset = self.COLORS['RESET']
        
        # 格式化消息
        message = record.getMessage()
        
        # 如果有時間格式，添加時間
        if self.datefmt:
            timestamp = self.formatTime(record, self.datefmt)
            return f"{color}[{timestamp}] {prefix} {message}{reset}"
        else:
            return f"{color}{prefix} {message}{reset}"


def setup_logger(
    name: str = "openai-register",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    show_time: bool = False,
) -> logging.Logger:
    """
    設置日誌記錄器
    
    Args:
        name: 日誌記錄器名稱
        level: 日誌級別
        log_file: 日誌檔案路徑（可選）
        show_time: 是否顯示時間戳
        
    Returns:
        配置好的 Logger 物件
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重複添加 handler
    if logger.handlers:
        return logger
    
    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 設置格式
    if show_time:
        formatter = ColoredFormatter(datefmt='%H:%M:%S')
    else:
        formatter = ColoredFormatter()
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 檔案 handler（如果指定）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# 全局 logger 實例
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """獲取全局 logger 實例"""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger
