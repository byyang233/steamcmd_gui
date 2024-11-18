import os
import json
import re
import hashlib
import requests
from winpty import PTY
from tkinter import messagebox
from loguru import logger

class SteamAccountManager:
    def __init__(self, accounts_file):
        self.accounts_file = accounts_file
        self.accounts = self.load_accounts()

    def load_accounts(self):
        try:
            with open(self.accounts_file, 'r') as f:
                data = json.load(f)
                return data.get('accounts', [])
        except FileNotFoundError:
            print(f"错误: {self.accounts_file} 文件未找到!")
            return []

    def get_account_for_game(self, appid):
        for account in self.accounts:
            if appid in account['games']:
                return account
        return None


class SteamCMD:
    def __init__(self, root, account_manager):
        self.root = root
        self.steam_cmd = f"{root}/steamcmd.exe"
        self.steam_cmd = os.path.abspath(self.steam_cmd)
        self.workshop_content = f"{root}/steamapps/workshop/content"
        self.workshop_content = os.path.abspath(self.workshop_content)
        self.md5 = "2629c77b1149eee9203e045e289e68ef"
        self.mutex = False
        self.account_manager = account_manager

    def paste(self, text):
        pattern_map = {
            "Downloading item (\d+) ...": 1,
            'Success. Downloaded item (\d+) to "(.*?)"': 2,
            "ERROR! Download item (\d+) failed \((.*)\).": -1,
        }
        for pattern in pattern_map:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if len(matches) != 0:
                if type(matches[0]) == str:
                    matches[0] = (matches[0], None)
                return [pattern_map[pattern], matches]
        return None

    def workshop_download(self, app_id, mods_id, obs):
        queue = dict()
        command = []
        compnum = 0
        command.append(self.steam_cmd)
        
        # 获取拥有该游戏的账号
        account = self.account_manager.get_account_for_game(app_id)
        if account:
            command.append(f"+login {account['username']} {account['password']}")
        else:
            logger.error(f"没有找到拥有 appid {app_id} 的账号")
            return []

        if type(mods_id) == str:
            mods_id = [mods_id]
        for _, mod_id in enumerate(mods_id):
            queue[mod_id] = [None, None]  # 加入队列
            obs(0, None, [mod_id, _], compnum, len(mods_id))
            command.append(f"+workshop_download_item {app_id} {mod_id}")
        
        # 结束并退出
        command.append("+quit")
        command = " ".join(command)

        process = PTY(1000, 25)
        process.spawn(command)
        while process.isalive():
            line = process.read()
            if len(line) != 0:
                obs(-5, line, [], compnum, len(mods_id))  # 文本
                pack = self.paste(line.strip())
                if pack != None:
                    mod_id = pack[1][0][0]
                    if pack[0] == 1:  # 正在下载
                        queue[mod_id] = [1, None]
                    if pack[0] == 2:  # 下载完成
                        queue[mod_id] = [2, None]
                        compnum = compnum + 1
                    if pack[0] == -1:  # 下载失败
                        queue[mod_id] = [-1, pack[1][0][1]]
                    obs(
                        pack[0], None, [mod_id, queue[mod_id][1]], compnum, len(mods_id)
                    )
        del process
        return queue

    def update(self):
        md5_hash = hashlib.md5()
        with open(self.steam_cmd, "rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                md5_hash.update(chunk)
        full_md5 = md5_hash.hexdigest()
        if full_md5 == self.md5:
            self.mutex = True
            window.title = "即将初始化..."
            logger.debug(window.title)
            process = PTY(1000, 25)  # cols值不应过小,否则输出会被截断
            process.spawn(self.steam_cmd + " " + "+quit")
            while process.isalive():
                line = process.read()
                if len(line) != 0:
                    window.title = f"初始化: {line}"
                    logger.debug(window.title)
            window.title = f"初始化结束..."
            logger.debug(window.title)
            self.mutex = False
            del process
        else:
            logger.debug("初始化结束...")

    def exclude(self, appid, mods_id):
        mods_path = os.path.join(self.workshop_content, appid)
        dirs = os.listdir(mods_path)
        excludes = []
        for dir in dirs:
            full_path = os.path.join(mods_path, dir)
            if os.path.isdir(full_path):
                if not (dir in mods_id):
                    excludes.append(dir)
        if len(excludes) > 0:
            result = messagebox.askyesno(
                "移除未订阅文件?", json.dumps(excludes, ensure_ascii=False)
            )
            if result:
                for dir in excludes:
                    mod_dir = os.path.join(mods_path, dir)
                    os.rmdir(mod_dir)
                    logger.debug(f"移除: {mod_dir}")
