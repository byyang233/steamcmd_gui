import os
import re
import requests
from bs4 import BeautifulSoup

# 文件路径
ACCOUNTS_FILE = "accounts.txt"
PASSWORDS_FILE = "passwords.txt"
APPIDS_FILE = "appids.txt"

# SteamCMD 目录
STEAMCMD_PATH = "steamcmd.exe"

# 匹配模式
patterns = {
    r"Downloading item (\d+) ...": 1,
    r'Success\. Downloaded item (\d+) to "(.*?)"': 2,
    r"ERROR! Download item (\d+) failed \((.*)\).": -1,
}

# 加载账号和密码
def load_accounts_and_passwords():
    accounts = []
    passwords = []

    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            accounts = f.read().splitlines()

    if os.path.exists(PASSWORDS_FILE):
        with open(PASSWORDS_FILE, "r", encoding="utf-8") as f:
            passwords = f.read().splitlines()

    if len(accounts) != len(passwords):
        raise ValueError("账号和密码数量不匹配！")

    return list(zip(accounts, passwords))

# 加载 APPID 列表
def load_appids():
    appids = []
    if os.path.exists(APPIDS_FILE):
        with open(APPIDS_FILE, "r", encoding="utf-8") as f:
            appids = f.read().splitlines()
    return appids

# 运行 SteamCMD 命令
def run_steamcmd(account, password, appid):
    command = f'{STEAMCMD_PATH} +login {account} {password} +workshop_download_item {appid} validate +quit'
    print(f"运行命令: {command}")
    result = os.popen(command).read()

    for pattern, status in patterns.items():
        match = re.search(pattern, result)
        if match:
            if status == 1:
                print(f"下载中：{match.group(1)}")
            elif status == 2:
                print(f"下载成功：{match.group(1)}，保存位置：{match.group(2)}")
            elif status == -1:
                print(f"下载失败：{match.group(1)}，错误信息：{match.group(2)}")
            return status
    print("未识别的输出：", result)
    return None

# 检测 APPID 并选择账号
def download_with_appid_detection():
    accounts_and_passwords = load_accounts_and_passwords()
    appids = load_appids()

    for appid in appids:
        print(f"检测 APPID: {appid}")
        selected_account = None

        # 按需选择对应的账号
        for account, password in accounts_and_passwords:
            if appid.startswith(account[:3]):  # 示例逻辑
                selected_account = (account, password)
                break

        if not selected_account:
            print(f"未找到适合的账号下载 APPID: {appid}")
            continue

        account, password = selected_account
        print(f"使用账号 {account} 下载 APPID {appid}")
        run_steamcmd(account, password, appid)

# 主函数
if __name__ == "__main__":
    try:
        download_with_appid_detection()
    except Exception as e:
        print(f"程序出错: {e}")
