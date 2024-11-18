import os
import re
import webview
from bs4 import BeautifulSoup
import requests
import urllib.parse
from urllib.parse import urlparse
import json
from winpty import PTY
import hashlib
from loguru import logger
from tkinter.messagebox import *
from tkinter import messagebox


class steamcmd:
    def __init__(self, root):
        self.root = root
        self.steam_cmd = f"{root}/steamcmd.exe"
        self.steam_cmd = os.path.abspath(self.steam_cmd)
        self.workshop_content = f"{root}/steamapps/workshop/content"
        self.workshop_content = os.path.abspath(self.workshop_content)
        self.md5 = "2629c77b1149eee9203e045e289e68ef"
        self.mutex = False

    def paste(self, text):
        pattern_map = {
            r"Downloading item (\d+) ...": 1,
            r'Success. Downloaded item (\d+) to "(.*?)"': 2,
            r"ERROR! Download item (\d+) failed \((.*)\).": -1,
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
        user = open('user.txt', 'r').read()
        p = open('p.txt', 'r').read()
        command.append(f"+login {user} {p}")
        if type(mods_id) == str:  # 字符串转数组
            mods_id = [mods_id]
        for _, mod_id in enumerate(mods_id):
            queue[mod_id] = [None, None]  # 加入队列
            obs(0, None, [mod_id, _], compnum, len(mods_id))
            command.append("+workshop_download_item {0} {1}".format(app_id, mod_id))
        command.append("+quit")
        command = " ".join(command)
        # --------------------------
        process = PTY(1000, 25)  # cols值不应过小,否则输出会被截断
        process.spawn(command)
        while process.isalive():
            line = process.read()
            if len(line) != 0:
                obs(-5, line, [], compnum, len(mods_id))  # 文本
                pack = self.paste(line.strip())
                if pack is not None:
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
                    )  # 进度回调
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


def create_item(num, mid, text):
    window.evaluate_js(f"create_item(`{num}`,`{mid}`,`{text}`)")


def update_item(mid, text):
    window.evaluate_js(f"update_item(`{mid}`,`{text}`)")


def message_box(text):
    window.evaluate_js(f"alert(`{text}`)")


def myworkshopfiles(url, appid, cookies, obs, verify=True):
    def get_url_params(url):
        params = {}
        if "?" in url:
            query_string = url.split("?")[1]
            for param in query_string.split("&"):
                key_value = param.split("=")
                params[key_value[0]] = key_value[1]
        return params

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) ",
        "Cookie": cookies,
    }
    params = {
        "appid": appid,
        "browsefilter": "mysubscriptions",
        "numperpage": "30",
        "p": "1",
    }
    try:
        obs(-5, "正在检索模组...", [], 0, 0)
        query_string = urllib.parse.urlencode(params)
        response = requests.get(f"{url}?{query_string}", headers=headers, verify=verify)
        soup = BeautifulSoup(response.text, "html.parser")
        pages = soup.find_all(class_="pagelink")
        if len(pages) == 0:
            pages = 1
        else:
            pages = pages[-1].text
        mods_num = soup.select_one(".workshopBrowsePagingInfo").text
        matches = re.findall(r"(\d+)", mods_num)
        mods_num = int(matches[-1]) if matches else 0
        mods = []
        for index in range(int(pages)):
            params["p"] = index + 1
            curl = f"{url}?{urllib.parse.urlencode(params)}"
            page_data = requests.get(curl, headers=headers, verify=verify)
            page_soup = BeautifulSoup(page_data.text, "html.parser")
            parent = page_soup.select(".workshopItemPreviewHol
