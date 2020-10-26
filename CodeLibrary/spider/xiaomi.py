import os
import sys
import time
import json
import aiohttp
import asyncio
import contextlib
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from functools import lru_cache
from fake_useragent import UserAgent


def cmp(target, text, eq=True) -> bool:
    return (rinse(target) == rinse(text)) if eq else (rinse(target) in rinse(text))


def rinse(text) -> str:
    return ''.join(text.split()).upper()


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as w:
        json.dump(data, w, ensure_ascii=False, indent=4)


class MI:
    """小米爬虫"""

    def __init__(self, path=None, wait=5, now=False):
        self._path = path
        self.name = '小米'  # 渠道名称
        self.url = 'https://game.wali.com/search/'
        self.wait = wait  # 等待时间，暂未使用
        self.results = []  # 所有结果
        self.now = now
        self.s_now = None
        self.e_now = None
        not self.now or self.print_s_now()

    def print_s_now(self):
        self.s_now = datetime.now()
        print(f's_now：{self.s_now.strftime("%Y-%m-%d %H:%M:%S")}===name：{self.name}')

    def print_e_now(self):
        self.e_now = datetime.now()
        print(f'e_now：{self.e_now.strftime("%Y-%m-%d %H:%M:%S")}===name：{self.name}'
              f'===s：{(self.s_now-self.e_now).microseconds/1000000}')

    def get_url(self) -> str:
        return self.url

    def get_name(self) -> str:
        return self.name

    def get_results(self) -> tuple:
        not self.now or self.print_e_now()
        save_json(f'{self._path}/{self.name}.json', self.results)
        return self.name, self.results

    @staticmethod
    def get_param(url, method='get', headers=None, data=None, proxy=None, timeout=None):
        return url, method, headers or {'User-Agent': UserAgent().random}, data, proxy, timeout

    async def check(self, target: str):
        """检查查找对象是否存在"""
        async with aiohttp.ClientSession() as session:
            url, method, headers, data, proxy, timeout = self.build_param(target)
            can, exact_url = False, False
            with contextlib.suppress(aiohttp.ServerDisconnectedError):
                async with session.request(method, url, headers=headers, data=data, proxy=proxy,
                                           timeout=timeout) as res:
                    if res.status == 200:
                        content = await res.read()
                        can, exact_url = await self.dispose(target, content)
            self.results.append({target: {'搜寻网址': url, '是否存在': can, '下载网址': exact_url}})

    @lru_cache(maxsize=128, typed=True)
    def build_param(self, target):
        url = self.url + urllib.parse.quote(target)
        return self.get_param(url)

    async def dispose(self, target, content):
        soup = BeautifulSoup(content.decode(encoding='utf-8'), features='html.parser')
        keyword = 'window.__INITIAL_STATE__='
        with contextlib.suppress(AttributeError):
            scripts = soup.find_all('script')
            data = [s.text.replace(keyword, '') for s in scripts if keyword in s.text][0][:-1]
            ds = json.loads(data, encoding='utf-8')
            for d in ds['data']:
                if cmp(target, text=d['gameInfo']['gameName'],
                       eq=False): return True, f'https://game.xiaomi.com/game/{d["gameId"]}'
        return False, None


def run(target, path):
    s = MI(path=path)
    loop = asyncio.get_event_loop()
    tasks = asyncio.gather(*[asyncio.ensure_future(s.check(target))], loop=loop)
    loop.run_until_complete(tasks)
    loop.close()
    print(s.get_results())


if __name__ == '__main__':
    argv = sys.argv[1:]
    if len(argv) == 1:
        p = os.path.join(os.path.dirname(__file__), f'../cache/{argv[0]}_{str(time.time()).replace(".", "")}')
        os.path.exists(p) or os.mkdir(p)
        argv.append(p)
    run(*argv) if len(argv) == 2 else print('[error] no game name input')
