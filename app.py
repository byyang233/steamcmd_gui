import os, re
import webview
from bs4 import BeautifulSoup
import requests
import urllib.parse
from urllib.parse import urlparse, parse_qs
import json
from winpty import PTY


class steamcmd:
    def __init__(self, root):
        self.root = root
        self.steam_cmd = f"{root}/steamcmd.exe"
        self.steam_cmd = os.path.abspath(self.steam_cmd)
        self.workshop_content = f"{root}/steamapps/workshop/content"
        self.workshop_content = os.path.abspath(self.workshop_content)

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
        command.append("+login anonymous")
        if type(mods_id) == str:  # 字符串转数组
            mods_id = [mods_id]
        for _, mod_id in enumerate(mods_id):
            queue[mod_id] = [None, None]
            obs(0, None, [mod_id, _], compnum, len(mods_id))  # 队列项目
            command.append("+workshop_download_item {0} {1}".format(app_id, mod_id))
        command.append("+quit")
        command = " ".join(command)
        # --------------------------
        process = PTY(1000, 25)  # cols值不应过小,否则输出会被截断
        process.spawn(command)
        while process.isalive():
            line = process.read()
            if len(line) != 0:
                obs(-5, line, [], compnum, len(mods_id))  # 终端文本
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
                    )  # 项目进度
        del process
        return queue


def create_item(num, mid, text):
    window.evaluate_js(f"create_item(`{num}`,`{mid}`,`{text}`)")


def update_item(mid, text):
    window.evaluate_js(f"update_item(`{mid}`,`{text}`)")


def myworkshopfiles(url, appid, cookies, obs):
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
    obs(-5, "正在检索模组...", [], 0, 0)
    query_string = urllib.parse.urlencode(params)
    response = requests.get(f"{url}?{query_string}", headers=headers)
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
        page_data = requests.get(curl, headers=headers)
        page_soup = BeautifulSoup(page_data.text, "html.parser")
        parent = page_soup.select(".workshopItemPreviewHolder")
        for item in parent:
            link = item.parent.get("href")
            mods.append(get_url_params(link)["id"])
        obs(-5, f"正在读取第{index + 1}/{pages}页...", [], 0, 0)
    obs(-5, f"已检索模组数量:{len(mods)}", [], 0, 0)
    return mods


class Api:
    def __init__(self):
        self.config = self.read()

    def read(self):
        if os.path.exists("config.ui"):
            with open("config.ui", "r") as file:
                return json.load(file)
        return {}

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def get(self, key):
        return self.config.get(key, None)

    def save(self):
        with open("config.ui", "w") as file:
            json.dump(self.config, file)

    def update(self, url, cookies):
        parsed_url = urlparse(url)
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
        path = parsed_url.path
        query = parsed_url.query
        curl = scheme + "://" + netloc + path
        appid = urllib.parse.parse_qs(query)["appid"][0]

        def obs(code, text, args, num, total):
            """
            #code -5 终端文本
            #code -1 下载失败
            #code 0 加入队列
            #code 1 正在下载
            #code 2 下载完成
            """
            if code == 0:  # 加入队列
                create_item(args[1], args[0], "队列")
                text = f"加入队列 {args[0]}"
            if code == 1:  # 正在下载
                update_item(args[0], "正在下载")
                text = f"正在下载 {args[0]}"
            if code == 2:  # 正在下载
                update_item(args[0], "下载完成")
                text = f"下载完成 {args[0]}"
            if code == -1:  # 下载失败
                update_item(args[0], "下载失败 {args[1]}")
                text = f"下载失败 {args[0]} {args[1]}"
            window.title = f"[{num}/{total}] " + (text or "")

        mods = myworkshopfiles(curl + "?" + query, appid, cookies, obs)
        return steam_api.workshop_download(appid, mods, obs)


webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
steam_api = steamcmd("steamcmd")
window = webview.create_window(
    "Hello world", "html/index.html", width=435, height=530, js_api=Api()
)
webview.start(None, window, debug=True)
