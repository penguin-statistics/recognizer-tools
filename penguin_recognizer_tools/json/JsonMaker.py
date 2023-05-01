import json
import sys

import requests


class Maker():
    item_url = "https://penguin-stats.io/PenguinStats/api/v2/items"
    stage_url = "https://penguin-stats.io/PenguinStats/api/v2/stages"

    def __init__(self) -> None:
        self.item_index = {}
        self.stage_index = {}
        self._get_itemindex()
        self._get_stageindex()

    def _get_itemindex(self):
        with requests.get(self.item_url) as f:
            item_table = json.loads(f.text)
        for item in item_table:
            item_id = item["itemId"]
            name_i18n = item["name_i18n"]
            self.item_index[item_id] = {"name_i18n": name_i18n}

    def _get_stageindex(self):
        with requests.get(self.stage_url) as f:
            stage_table = json.loads(f.text)
        for stage in stage_table:
            code = stage["code"]
            stage_id = stage["stageId"]
            if stage_id[:5] == "tough":
                difficulty = "TOUGH"
            else:
                difficulty = "NORMAL"
            drops = []
            if "dropInfos" in stage:
                for item in stage["dropInfos"]:
                    if "itemId" in item and item["itemId"] != "furni":
                        drops.append(item["itemId"])
            if "recognitionOnly" in stage:
                for item_id in stage["recognitionOnly"]:
                    drops.append(item_id)
            if code not in self.stage_index:
                self.stage_index[code] = {}
            self.stage_index[code][difficulty] = {
                "stageId": stage_id,
                "drops": list(set(drops)),
                "existence": True
            }


if __name__ == "__main__":
    import pathlib

    current_path = pathlib.Path(__file__).parent.resolve()
    m = Maker()
    with open(current_path.joinpath("item_index.json"), 'w', encoding="utf-8") as f:
        f.write(json.dumps(m.item_index, ensure_ascii=False))
    with open(current_path.joinpath("stage_index.json"), 'w', encoding="utf-8") as f:
        f.write(json.dumps(m.stage_index, ensure_ascii=False))
