import hashlib
import io
import json
import warnings
import zipfile
from contextlib import contextmanager

import requests

from penguin_recognizer_tools.icon.decrypt import decrypt


class FileGetter:
    _NETWORK_CONFIG_URLS = {
        'CN': 'https://ak-conf.hypergryph.com/config/prod/official/network_config',
        'JP': 'https://ak-conf.arknights.jp/config/prod/official/network_config',
        'US': 'https://ak-conf.arknights.global/config/prod/official/network_config',
        'KR': 'https://ak-conf.arknights.kr/config/prod/official/network_config',
        'TW': 'https://ak-conf.txwy.tw/config/prod/official/network_config',
    }

    _TEXT_ASSET_ROOT_URLS = {
        'CN': 'https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/',
        'JP': 'https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ja_JP/',
        'US': 'https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/en_US/',
        'KR': 'https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ko_KR/',
    }

    def __init__(self, server) -> None:
        self.server = server
        self._platform = "Android"
        self._network_config = self._get_network_config()
        self._version = self._get_version()
        self._file_list = self._get_file_list()

    @contextmanager
    def get(self, filename, **kwargs):
        z = self._get_file(filename, **kwargs)
        if z is None:
            raise FileNotFoundError
        if type(z) == dict:
            yield z
        else:
            with z.open(filename) as f:
                yield f

    def version(self):
        return self._version

    def _get_file(self, filename: str, text_asset=False):
        text_asset_root_url = self._TEXT_ASSET_ROOT_URLS.get(self.server, None)
        if text_asset_root_url is None:
            text_asset_root_url = self._root_url
        if text_asset:
            url = text_asset_root_url + filename
            return self._get_json(url.replace(".ab", ".json"))
        url = self._root_url + \
              (filename.rsplit('.', 1)[0] + ".dat") \
                  .replace('/', '_') \
                  .replace('#', '__')
        return zipfile.ZipFile(io.BytesIO(requests.get(url).content), 'r')

    @staticmethod
    def _get_json(json_url: str):
        res = requests.get(json_url).content.decode()
        return json.loads(res)

    def _get_network_config(self) -> dict:
        network_config_url = FileGetter._NETWORK_CONFIG_URLS[self.server]
        network_config = self._get_json(network_config_url)
        return json.loads(network_config["content"])

    def _get_version(self) -> str:
        func_ver = self._network_config["funcVer"]
        self.version_url = self._network_config["configs"][func_ver]["network"]["hv"] \
            .replace("{0}", self._platform)
        return self._get_json(self.version_url)["resVersion"]

    def _get_file_list(self) -> dict:
        func_ver = self._network_config["funcVer"]
        self._root_url = self._network_config["configs"][func_ver]["network"]["hu"] \
                         + f"/{self._platform}/assets/{self._version}/"
        self.file_list_url = self._root_url + "hot_update_list.json"
        file_arr: list = self._get_json(self.file_list_url)["abInfos"]
        return {_["name"]: _["md5"] for _ in file_arr}


if __name__ == "__main__":
    fg = FileGetter("CN")
    with fg.get("activity/[uc]act25side.ab") as f:
        import UnityPy

        with open("activity_[uc]act25side.ab", "wb") as ff:
            ff.write(f.read())

        env = UnityPy.load(f)
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                text_asset_file = obj.read()
                stage_table = decrypt(text_asset_file)
                # print(stage_table)
        print(fg._get_json(fg.version_url))
