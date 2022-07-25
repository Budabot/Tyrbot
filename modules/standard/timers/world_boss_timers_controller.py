import requests

from core.chat_blob import ChatBlob
from core.decorators import instance, command
import time

from core.dict_object import DictObject
from core.setting_types import TextSettingType


@instance()
class WorldBossTimersController:
    def __init__(self):
        self.bosses = {
            "tara": {
                "name": "Tara",
                "spawn_time": 3600 * 9,
                "invulnerable_time": 30 * 60
            },
            "vizaresh": {
                "name": "Vizaresh",
                "spawn_time": 3600 * 17,
                "invulnerable_time": 6 * 60
            },
            "father-time": {
                "name": "Father Time",
                "spawn_time": 3600 * 9,
                "invulnerable_time": 15 * 60
            },
        }

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.setting_service = registry.get_instance("setting_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")

    def start(self):
        self.setting_service.register(self.module_name, "boss_timers_api_address", "https://timers.aobots.org/api/v1.1/bosses",
                                      TextSettingType(["https://timers.aobots.org/api/v1.1/bosses"]),
                                      "The address of the Boss Timers API")

        self.setting_service.register(self.module_name, "gauntlet_timers_api_address", "https://timers.aobots.org/api/v1.1/gaubuffs",
                                      TextSettingType(["https://timers.aobots.org/api/v1.1/gaubuffs"]),
                                      "The address of the Gauntlet Buff Timers API")

        self.command_alias_service.add_alias("tara", "worldboss")
        self.command_alias_service.add_alias("loren", "worldboss")
        self.command_alias_service.add_alias("vizaresh", "worldboss")
        self.command_alias_service.add_alias("gauntlet", "gauntletbuffs")

    @command(command="worldboss", params=[], access_level="guest",
             description="Show current boss timers")
    def worldboss_cmd(self, request):
        url = self.setting_service.get("boss_timers_api_address").get_value()
        result = self.make_request(url)
        t = int(time.time())

        blob = ""
        # TODO sort by name? next spawn?
        for row in result.timers:
            if row.dimension != self.bot.dimension:
                continue

            boss = self.bosses.get(row.name, {})
            bossname = boss.get("name", row.name.capitalize())
            last_spawned = self.util.time_to_readable(t - row.last_spawn)
            if boss:
                next_spawn = self.util.time_to_readable((row.last_spawn + boss.get("spawn_time") + boss.get("invulnerable_time")) - t)
            else:
                next_spawn = "Unknown"

            blob += f"<header2>{bossname}</header2>\n"
            blob += f"Next Spawn: <highlight>{next_spawn}</highlight>\n"
            blob += f"Last Spawned: <highlight>{last_spawned} ago</highlight>\n\n"

        blob += "\nWorld Boss timers provided by <highlight>The Nadybot Team</highlight>"

        return ChatBlob("World Boss Timers", blob)

    @command(command="gauntletbuffs", params=[], access_level="guest",
             description="Show current boss timers")
    def gauntletbuffs_cmd(self, request):
        url = self.setting_service.get("gauntlet_timers_api_address").get_value()
        result = self.make_request(url)
        t = int(time.time())

        blob = ""
        for row in result.timers:
            if row.dimension != self.bot.dimension:
                continue

            time_left = self.util.time_to_readable(row.expires - t)
            blob += f"<header2>{row.faction.capitalize()}</header2>\n"
            blob += f"<highlight>{time_left} left</highlight>\n\n"

        if not result.timers:
            blob += "No Gauntlet buffs currently active\n\n"

        blob += self.text.make_tellcmd("Gauntlet Tradeskills", "info gauntlet_tradeskills") + "\n\n"

        blob += "Gauntlet timers provided by <highlight>The Nadybot Team</highlight>"

        return ChatBlob("Gauntlet Buff Timers", blob)

    def make_request(self, url):
        headers = {}
        headers.update({"User-Agent": f"Tyrbot {self.bot.version}"})

        params = []

        r = requests.get(url, params, headers=headers, timeout=5)
        result = DictObject({"timers": r.json()})
        return result

