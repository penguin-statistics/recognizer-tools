import logging
import os
import tempfile

import coloredlogs
import requests as r

from penguin_recognizer_tools.icon.IconGetter import IconGetter
from penguin_recognizer_tools.icon.MultiUploader import MultiUploader

logger = logging.getLogger(__name__)
coloredlogs.install(level="LOG_LEVEL" in os.environ and os.environ["LOG_LEVEL"] or "INFO")

SKIP_UPDATE_CHECK = False
HOST = "https://penguin-stats.io"


class ServerIconPackUpdater:
    def __init__(self, server: str, output_dir: str, current_version: str) -> None:
        self.server = server
        self.icon_getter = IconGetter(server, True)
        self.output_dir = output_dir
        self.logger = logging.getLogger("ServerIconPackUpdater." + server)
        self.latest_version = self.icon_getter.fg.version()
        self.current_version = current_version

    def invoke(self):
        if not SKIP_UPDATE_CHECK:
            self.logger.info("checking update: current version %s, latest version %s", self.current_version,
                             self.latest_version)
            if self.current_version == self.latest_version:
                self.logger.info("icon pack %s is up to date", self.latest_version)
                return

        self.icon_getter.load()
        save_path = self.icon_getter.make_zip(self.output_dir)
        self.logger.info("zip file saved at %s", save_path)

        filename = os.path.basename(save_path)
        filename_without_ext = os.path.splitext(filename)[0]

        MultiUploader(save_path, "recognition/resources/{}/{}/items.zip".format(self.server, self.latest_version))

        self.logger.info("icon pack %s uploaded", self.latest_version)

        r.post(HOST + "/api/admin/recognition/items-resources/updated", headers={
            "Authorization": "Bearer " + os.environ["PENGUIN_V3_ADMIN_KEY"]
        }, json={
            "server": self.server,
            "prefix": self.server + "/" + self.latest_version
        })

        self.logger.info("icon pack %s updated", self.latest_version)


class MultiServerIconPackUpdater:
    def __init__(self, servers: list[str], output_dir: str) -> None:
        self.current_versions = r.get(HOST + "/PenguinStats/api/v2/config").json()["recognition"]["items-resources"][
            "prefix"]
        self.output_dir = output_dir
        self.servers = servers

    def invoke(self):
        for server in self.servers:
            current_version: str | None = self.current_versions[server] if server in self.current_versions else None
            if current_version:
                current_version = current_version.removeprefix(server + "/")
            ServerIconPackUpdater(server, self.output_dir,
                                  current_version).invoke()


if __name__ == "__main__":
    tempdir = tempfile.TemporaryDirectory()
    u = MultiServerIconPackUpdater(servers=["CN", "US", "JP", "KR"], output_dir=tempdir.name)
    u.invoke()
