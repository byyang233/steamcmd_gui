import subprocess, os, re
import time
import webview
from bs4 import BeautifulSoup
import requests
import urllib.parse
from urllib.parse import urlparse, parse_qs
import json


class steam:
    def __init__(self, root):
        self.root = root
        self.steam_cmd = f"{root}/steamcmd.exe"
        self.steam_cmd = os.path.abspath(self.steam_cmd)
        self.workshop_content = f"{root}/steamapps/workshop/content"
        self.workshop_content = os.path.abspath(self.workshop_content)

    def workshop_download(self, game_id, mods_id, obs=None):
        mods_map = dict()
        comm = []
        comp = 0
        for _, mod_id in enumerate(mods_id):
            mods_map[mod_id] = None
            if obs != None:
                obs(1, mod_id, [_], comp, len(mods_id))
            comm.append(f"+workshop_download_item {game_id} {mod_id}")
        comm = " ".join(comm)
        command = f"+login anonymous {comm} +quit"
        command = self.steam_cmd + " " + command
        process = subprocess.Popen(
            command,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout_temp = []
        while process.poll() != 0:
            output = process.stdout.readline()
            if len(output) != 0:
                data = self.paste(output.strip())
                stdout_temp.append(output)
                if len(data) != 0:
                    for item in data:
                        code = item[1]
                        if code == 2:
                            mods_map[item[3]] = item[4]
                            comp = comp + 1
                        if code == -1:
                            mods_map[item[3]] = False
                        if item != None:
                            if obs != None:
                                obs(2, item[2].format(*item), item, comp, len(mods_id))
        process.stdout.close()
        process.wait()
        return mods_map

    def paste(self, text):
        pattern_map = {
            "Loading Steam API...OK": [False, 0, "初始化Steam API..."],
            "Connecting anonymously to Steam Public...OK": [
                False,
                0,
                "正在匿名登陆Steam中...成功",
            ],
            "Waiting for client config...OK": [False, 0, "正在载入客户端配置...成功"],
            "Waiting for user info...OK": [False, 0, "正在获取用户数据...成功"],
            "Downloading item (\d+) ...": [True, 1, "正在下载 {3} 模组"],
            'Success. Downloaded item (\d+) to "(.*?)"': [
                True,
                2,
                '已下载 {3} 模组至 "{4}"',
            ],
            "ERROR! Download item (\d+) failed \((.*)\).": [
                False,
                -1,
                "下载模组 {3} 失败,原因:({4}) ...",
            ],
        }
        response = []
        for pattern in pattern_map:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if len(matches) != 0:
                if isinstance(matches[0], str):
                    data = [*pattern_map[pattern], matches[0]]
                else:
                    data = [*pattern_map[pattern], *matches[0]]
                response.append(data)
        return response


def myworkshopfiles(url, appid, cookies):
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
    window.title = "正在获取模组参数..."
    query_string = urllib.parse.urlencode(params)
    response = requests.get(f"{url}?{query_string}", headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    pages = soup.find_all(class_="pagelink")
    if len(pages) == 0:
        pages = 1
    else:
        pages = pages[-1].text
    print("页数", pages)
    window.title = f"模组共{pages}页..."
    mods_num = soup.select_one(".workshopBrowsePagingInfo").text
    matches = re.findall(r"(\d+)", mods_num)
    mods_num = int(matches[-1]) if matches else 0
    print("模组预计数量", mods_num)
    window.title = f"模组显示{mods_num}数量..."
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
        print(f"正在获取第 {index + 1}/{pages} 页")
        window.title = f"正在访问第{index + 1}/{pages}页..."
    print("模组实际数量", len(mods))
    window.title = f"模组数量:{len(mods)}"
    return mods


class Api:
    def save(self, key, value):
        if not ("dict_ui" in globals()):
            globals()["dict_ui"] = dict()
        global dict_ui
        dict_ui[key] = value
        with open("dict_ui.ini", "w") as file:
            json.dump(dict_ui, file)

    def read(self, key):
        if not ("dict_ui" in globals()):
            if not os.path.exists("dict_ui.ini"):
                value = dict()
            else:
                with open("dict_ui.ini", "r") as file:
                    value = json.load(file)
            globals()["dict_ui"] = value
        global dict_ui
        return dict_ui[key]

    def update(self, url, cookies):
        try:
            global steam_api
            if len(url) == 0 or len(cookies) == 0:
                return "请在填写参数后,再尝试重新提交"
            parsed_url = urlparse(url)
            scheme = parsed_url.scheme
            netloc = parsed_url.netloc
            path = parsed_url.path
            query = parsed_url.query
            curl = scheme + "://" + netloc + path
            appid = urllib.parse.parse_qs(query)["appid"][0]
            mods = myworkshopfiles(curl + "?" + query, appid, cookies)

            def obs(code, text, args, index, total):
                if code == 1:
                    window.evaluate_js(f"create_item({args[0]},{text},'队列')")
                if code == 2:
                    if args[1] in [-1, 1, 2]:
                        state = ""
                        if args[1] == -1:
                            state = "下载失败"
                        if args[1] == 1:
                            state = "正在下载"
                        if args[1] == 2:
                            state = "下载完成"
                        window.evaluate_js(f"update_txt(`{args[3]}`,`{state}`)")
                window.title = f"[{index}/{total}]:" + text

            results = steam_api.workshop_download(appid, mods, obs)
            os.startfile(os.path.join(steam_api.workshop_content, appid))
        except:
            window.title = "出现未知错误"
            return "出现未知错误"
        return results


def window_onload(window):
    globals()["steam_api"] = steam("steamcmd")


url = f"index.html"
webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
window = webview.create_window("Hello world", url, width=435, height=530, js_api=Api())
webview.start(window_onload, window, debug=True)
