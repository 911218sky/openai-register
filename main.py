#!/usr/bin/env python3
"""OpenAI 自動註冊工具 - 主程式"""
import argparse
import json
import os
import random
import time
from datetime import datetime

from src.config import Config
from src.logger import setup_logger
from src.registrar import OpenAIRegistrar

# 設置日誌
logger = setup_logger(show_time=True)


def save_token(token_json: str, password: str) -> None:
    """
    保存 token 和密碼到檔案
    
    Args:
        token_json: Token JSON 字串
        password: 帳戶密碼
    """
    try:
        t_data = json.loads(token_json)
        fname_email = t_data.get("email", "unknown").replace("@", "_")
        account_email = t_data.get("email", "")
    except Exception:
        fname_email = "unknown"
        account_email = ""
    
    # 保存 token
    file_name = f"token_{fname_email}_{int(time.time())}.json"
    if Config.TOKEN_OUTPUT_DIR:
        os.makedirs(Config.TOKEN_OUTPUT_DIR, exist_ok=True)
        file_name = os.path.join(Config.TOKEN_OUTPUT_DIR, file_name)
    
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(token_json)
    logger.info(f"成功! Token 已保存至: {file_name}")
    
    # 追加記錄帳號密碼
    if account_email and password:
        accounts_file = os.path.join(Config.TOKEN_OUTPUT_DIR, "accounts.txt") if Config.TOKEN_OUTPUT_DIR else "accounts.txt"
        with open(accounts_file, "a", encoding="utf-8") as af:
            af.write(f"{account_email}----{password}\n")
        logger.info(f"帳號密碼已追加至: {accounts_file}")


def print_banner() -> None:
    """顯示程式橫幅"""
    print("[Info] OpenAI 自動註冊工具")
    print()
    print("=" * 60)
    print("  📺 原作者: gaojilingjuli")
    print("     YouTube: https://www.youtube.com/@gaojilingjuli")
    print()
    print("  🔧 本專案基於原作者的工作進行重構和優化")
    print("  ⭐ 感謝原作者的貢獻！")
    print("=" * 60)
    print()


def main() -> None:
    """主函數"""
    parser = argparse.ArgumentParser(description="OpenAI 自動註冊腳本")
    parser.add_argument(
        "--proxy", "-p", default=None, help="代理地址，如 http://127.0.0.1:7890"
    )
    parser.add_argument("--once", action="store_true", help="只運行一次")
    parser.add_argument("--count", "-c", type=int, default=0, help="註冊帳號數量（0=無限循環）")
    parser.add_argument("--sleep-min", "-smin", type=int, default=30, help="循環模式最短等待秒數")
    parser.add_argument("--sleep-max", "-smax", type=int, default=120, help="循環模式最長等待秒數")
    parser.add_argument("--debug", "-d", action="store_true", help="啟用調試模式")
    args = parser.parse_args()
    
    # 如果啟用調試模式，設置日誌級別
    if args.debug:
        import logging
        logger.setLevel(logging.DEBUG)
    
    sleep_min = max(1, args.sleep_min)
    sleep_max = max(sleep_min, args.sleep_max)
    
    print_banner()
    
    # 如果指定了 count，顯示目標數量
    if args.count > 0:
        logger.info(f"目標註冊數量: {args.count} 個帳號")
    
    count = 0
    success_count = 0
    registrar = OpenAIRegistrar(proxy=args.proxy)
    
    while True:
        count += 1
        logger.info(f">>> 開始第 {count} 次註冊流程 <<<")
        
        try:
            token_json, password = registrar.register()
            
            if token_json == "retry_403":
                logger.warning("檢測到 403 錯誤，等待10秒後重試...")
                time.sleep(10)
                continue
            
            if token_json:
                save_token(token_json, password)
                success_count += 1
                logger.info(f"✓ 已成功註冊 {success_count} 個帳號")
                
                # 如果達到目標數量，退出
                if args.count > 0 and success_count >= args.count:
                    logger.info(f"🎉 已完成目標！成功註冊 {success_count} 個帳號")
                    break
            else:
                logger.warning("本次註冊失敗")
        
        except Exception as e:
            logger.error(f"發生未捕獲異常: {e}", exc_info=args.debug)
        
        if args.once:
            break
        
        wait_time = random.randint(sleep_min, sleep_max)
        logger.info(f"休息 {wait_time} 秒...")
        time.sleep(wait_time)


if __name__ == "__main__":
    main()
