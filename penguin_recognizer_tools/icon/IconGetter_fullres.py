import logging
import os
import tempfile
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import UnityPy
import coloredlogs
import cv2
import numpy
from PIL import Image

from FileGetter import FileGetter
from decrypt import decrypt

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG')


class IconGetter:
    file_list = [
        "spritepack/ui_item_icons_h1_0.ab",  # basic items
        "spritepack/ui_item_icons_h1_acticon_0.ab",  # randomMaterial
        "spritepack/ui_item_icons_h1_apsupply_0.ab",  # ap supply
        "activity/commonassets.ab",  # activity items
        "activity/[uc]act24side.ab",  # activity items
        "activity/[uc]act25side.ab"  # activity items
    ]

    def __init__(self, server, lazy: bool = False) -> None:
        self.server = server
        self.fg = FileGetter(server)
        if not lazy:
            self.load()

    def load(self):
        self.item_table = self._get_item_table()
        self.item_list = self._get_item_list()
        self.bkg_img_list = self._get_bkg_img()
        self.item_img_list = self._get_item_img()

    def make_zip(self, path):
        with tempfile.TemporaryDirectory() as temp:
            logging.debug('make_zip: making temp dir: %s', temp)
            logging.debug('make_zip: adding %d files to zip',
                          len(self.item_img_list))
            for item_id, pilimg in self.item_img_list.items():
                cv2img = cv2.cvtColor(numpy.array(pilimg), cv2.COLOR_RGBA2BGRA)
                cv2.imwrite(temp + "/" + item_id + ".png", cv2img)
            resource_name = "icons_" + self.server + "_" + self.fg._version
            filename = resource_name + ".zip"

            zip_savepath = os.path.join(path, filename)
            src_path = Path(temp).expanduser().resolve(strict=True)
            with ZipFile(zip_savepath, 'w', ZIP_STORED) as zf:
                for file in src_path.rglob('*'):
                    # zf.write(file, file.relative_to(src_path))
                    with file.open('rb') as f:
                        info = ZipInfo(str(file.relative_to(src_path)))
                        zf.writestr(info, f.read())

            logging.debug('make_zip: zip file created at: %s',
                          zip_savepath)

            return zip_savepath

            # # calculate sha512 hash for the zip file
            # zip_hash = None
            # with open(zip_savepath, 'rb') as f:
            #     zip_hash = hashlib.sha512(f.read()).hexdigest()

            # # set fname to github actions output
            # github_output = os.environ.get('GITHUB_OUTPUT')
            # if github_output:
            #     with open(github_output, 'w') as f:
            #         f.write(f"resource-name={filename}\n")
            #         f.write(f"resource-path={zip_savepath}\n")
            #         f.write(f"resource-dir={path}\n")
            #         f.write(f"resource-sha512={zip_hash}\n")

    def _get_item_table(self):
        res = {}
        with self.fg.get("gamedata/excel/item_table.ab") as f:
            env = UnityPy.load(f)
            for obj in env.objects:
                if obj.type.name == "TextAsset":
                    text_asset_file = obj.read()
                    item_table = decrypt(text_asset_file)
                    for _, item in item_table["items"].items():
                        item_id = item["itemId"]
                        rarity = item["rarity"]
                        icon_id = item["iconId"]
                        res[item_id] = {
                            "iconId": icon_id, "rarity": rarity}
                    break
        logging.debug(
            "_get_item_table: item_table loaded with %d items", len(res))
        return res

    def _get_item_list(self):
        item_set = set()

        logging.debug(
            "_get_item_list: fetching item list from Penguin Statistics API...")
        penguin_stages = self.fg._get_json(
            "https://penguin-stats.io/PenguinStats/api/v2/stages?server=" + self.server)
        for stage in penguin_stages:
            if stage["stageId"] == "recruit":
                continue
            if "dropInfos" in stage:
                for item in stage["dropInfos"]:
                    if ("itemId" in item):
                        logger.debug("stage: %s, item: %s", stage["stageId"], item["itemId"])
                        item_set.add(item["itemId"])
                    # else:
                    #     logger.warning("item without itemId: %s", item)
            if "recognitionOnly" in stage:
                for item in stage["recognitionOnly"]:
                    item_set.add(item)

        logging.debug(
            "_get_item_list: got %d de-duplicated and cleaned items from Penguin Statistics API", len(item_set))

        res = {}
        for item_id in item_set:
            if item_id == "furni":
                continue
            icon_id = self.item_table[item_id]["iconId"]
            rarity = self.item_table[item_id]["rarity"]
            if icon_id not in res:
                res[icon_id] = []
            res[icon_id].append({"itemId": item_id, "rarity": rarity})

        logging.debug(
            "_get_item_list: item_list loaded with %d icons", len(res))

        return res

    @staticmethod
    def _get_bkg_img():
        res = {"item": {}, "charm": {}, "act24side": {}}
        for i in range(6):
            img = Image.open(
                os.path.join(os.path.dirname(__file__), "background", f"sprite_item_r{i}.png"))
            res["item"][i] = img
        for i in range(1, 6):
            img = Image.open(
                os.path.join(os.path.dirname(__file__), "background", f"act24side_melding_{i}_bg.png"))
            res["act24side"][i] = img
        logging.debug("_get_bkg_img: item background loaded")
        return res

    def _get_item_img(self):
        res = {}
        for fname in IconGetter.file_list:
            with self.fg.get(fname) as f:
                env = UnityPy.load(f)
                for obj in env.objects:
                    if obj.type.name == "Sprite":
                        sprite_file = obj.read()
                        if (sprite_file.name in self.item_list):
                            item_img = sprite_file.image
                            for item in self.item_list[sprite_file.name]:
                                item_id = item["itemId"]
                                rarity = item["rarity"]
                                if item_id.startswith("act24side"):
                                    bkg_img = \
                                        self.bkg_img_list["act24side"][rarity + 1].copy()
                                else:
                                    bkg_img = \
                                        self.bkg_img_list["item"][rarity].copy()
                                offset_old = sprite_file.m_RD.textureRectOffset
                                x = round(offset_old.X)
                                y = bkg_img.height - item_img.height - \
                                    round(offset_old.Y)
                                if item_id.startswith("act24side"):
                                    inner_height = item_img.height
                                    inner_width = item_img.width
                                    outer_height = bkg_img.height
                                    outer_width = bkg_img.width
                                    offset = ((outer_width - inner_width) // 2, (outer_height - inner_height) // 2)
                                else:
                                    offset = (x + 1, y + 1)
                                bkg_img.alpha_composite(item_img, offset)
                                res[item_id] = bkg_img
                        # else:
                        #     logging.warning(
                        #         "_get_item_img: sprite %s not in item_list", sprite_file.name)
        logging.debug(
            "_get_item_img: item images loaded with %d items", len(res))
        return res


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--server", help="server name", type=str, default="CN")
    parser.add_argument(
        "--output-dir", help="output directory of the zip file", type=str, default=".")
    args = parser.parse_args()
    ig = IconGetter(args.server)
    ig.make_zip(args.output_dir)
