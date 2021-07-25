import time
from datetime import datetime

import pytz
import requests
from requests import ReadTimeout

from core.chat_blob import ChatBlob
from core.command_param_types import Any, Int, Const, Options
from core.db import DB
from core.decorators import instance, command
from core.dict_object import DictObject
from core.feature_flags import FeatureFlags
from core.logger import Logger
from core.setting_types import TextSettingType, DictionarySettingType
from core.text import Text
from core.tyrbot import Tyrbot
from modules.standard.helpbot.playfield_controller import PlayfieldController


@instance()
class TowerController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.setting_service = registry.get_instance("setting_service")
        self.playfield_controller: PlayfieldController = registry.get_instance("playfield_controller")

    def pre_start(self):
        self.db.load_sql_file(self.module_dir + "/" + "tower_site.sql")
        self.db.load_sql_file(self.module_dir + "/" + "tower_site_bounds.sql")
        self.db.load_sql_file(self.module_dir + "/" + "scout_info.sql")

    def start(self):
        self.command_alias_service.add_alias("hot", "lc open")

        self.setting_service.register(self.module_name, "tower_api_address", "https://tower-api.jkbff.com/api/towers",
                                      TextSettingType(["https://tower-api.jkbff.com/api/towers"]),
                                      "The address of the Tower API")
        self.setting_service.register(self.module_name, "tower_api_custom_headers", "",
                                      DictionarySettingType(),
                                      "Custom headers for the Tower API")

    @command(command="lc", params=[], access_level="all",
             description="See a list of playfields containing land control tower sites")
    def lc_list_cmd(self, request):
        data = self.db.query("SELECT id, long_name, short_name FROM playfields WHERE id IN (SELECT DISTINCT playfield_id FROM tower_site) ORDER BY short_name")

        blob = ""
        for row in data:
            blob += "[%d] %s <highlight>%s</highlight>\n" % (row.id, self.text.make_tellcmd(row.long_name, "lc %s" % row.short_name), row.short_name)

        blob += "\n" + self.get_lc_blob_footer()

        return ChatBlob("Land Control Playfields (%d)" % len(data), blob)

    if FeatureFlags.USE_TOWER_API:
        @command(command="lc", params=[Const("org"), Any("org", is_optional=True)], access_level="all",
                 description="See a list of land control tower sites by org")
        def lc_org_cmd(self, request, _, org):
            params = {"enabled": "true"}
            if not org:
                org = str(request.conn.org_id)
                if not org:
                    return "Bot does not belong to an org so an org name or org id must be specified."

            if org.isdigit():
                params["org_id"] = org
            else:
                params["org_name"] = "%" + org + "%"
            data = self.lookup_tower_info(params).results

            if not data:
                return "Could not find tower info for org <highlight>%s</highlight>." % org

            blob = ""
            current_day_time = int(time.time()) % 86400
            for row in data:
                blob += "<pagebreak>" + self.format_site_info(row, current_day_time) + "\n\n"

            blob += self.get_lc_blob_footer()

            title = "Tower Info: %s (%d)" % (org, len(data))

            return ChatBlob(title, blob)

        @command(command="lc", params=[Const("unplanted")],
                 access_level="all", description="See a list of land control tower sites that are not currently planted")
        def lc_unplanted_cmd(self, request, _):
            params = {"enabled": "true", "planted": "false"}

            data = self.lookup_tower_info(params).results

            if not data:
                return "There are no tower sites matching your criteria."

            blob = ""
            for row in data:
                blob += "<pagebreak>" + self.format_site_info(row, None) + "\n\n"

            blob += self.get_lc_blob_footer()

            title = "Tower Info: Unplanted"
            title += " (%d)" % len(data)

            return ChatBlob(title, blob)

        @command(command="lc", params=[Options(["open", "closed", "all"]),
                                       Options(["omni", "clan", "neutral", "all"], is_optional=True),
                                       Int("min_ql", is_optional=True),
                                       Int("max_ql", is_optional=True)],
                 access_level="all", description="See a list of land control tower sites by QL, faction, and open status")
        def lc_search_cmd(self, request, site_status, faction, min_ql, max_ql):
            t = int(time.time())
            current_day_time = t % 86400
            min_ql = min_ql or 1
            max_ql = max_ql or 300

            params = {"enabled": "true", "min_ql": min_ql, "max_ql": max_ql}

            if faction:
                params["faction"] = faction

            if site_status.lower() == "open":
                params["min_close_time"] = current_day_time
                params["max_close_time"] = self.day_time(current_day_time + (3600 * 6))
            elif site_status.lower() == "closed":
                params["min_close_time"] = self.day_time(current_day_time + (3600 * 6))
                params["max_close_time"] = current_day_time

            data = self.lookup_tower_info(params).results

            if not data:
                return "There are no tower sites matching your criteria."

            blob = ""
            for row in data:
                blob += "<pagebreak>" + self.format_site_info(row, current_day_time) + "\n\n"

            blob += self.get_lc_blob_footer()

            title = "Tower Info: %s" % site_status.capitalize()
            title += " QL %d - %d" % (min_ql, max_ql)
            if faction:
                title += " [%s]" % faction.capitalize()
            title += " (%d)" % len(data)

            return ChatBlob(title, blob)

    @command(command="lc", params=[Any("playfield"), Int("site_number", is_optional=True)], access_level="all",
             description="See a list of land control tower sites in a particular playfield")
    def lc_playfield_cmd(self, request, playfield_name, site_number):
        playfield = self.playfield_controller.get_playfield_by_name(playfield_name)
        if not playfield:
            return "Could not find playfield <highlight>%s</highlight>." % playfield_name

        data = self.get_tower_site_info(playfield.id, site_number)

        if not data:
            if site_number:
                return "Could not find tower info for <highlight>%s %d</highlight>." % (playfield.long_name, site_number)
            else:
                return "Could not find tower info for <highlight>%s</highlight>." % playfield.long_name

        blob = ""
        current_day_time = int(time.time()) % 86400
        for row in data:
            blob += "<pagebreak>" + self.format_site_info(row, current_day_time) + "\n\n"

        blob += self.get_lc_blob_footer()

        if site_number:
            title = "Tower Info: %s %d" % (playfield.long_name, site_number)
        else:
            title = "Tower Info: %s (%d)" % (playfield.long_name, len(data))

        return ChatBlob(title, blob)

    def format_site_info(self, row, current_day_time):
        blob = "<highlight>%s %d</highlight> (QL %d-%d)\n" % (row.playfield_short_name, row.site_number, row.min_ql, row.max_ql)

        if row.get("org_name"):
            t = int(time.time())
            value = datetime.fromtimestamp(row.close_time, tz=pytz.UTC)
            current_status_time = row.close_time - current_day_time
            if current_status_time < 0:
                current_status_time += 86400

            if current_status_time <= 3600:
                status = "<red>5%%</red> (closes in %s)" % self.util.time_to_readable(current_status_time)
            elif current_status_time <= (3600 * 6):
                status = "<orange>25%%</green> (closes in %s)" % self.util.time_to_readable(current_status_time)
            else:
                status = "<green>75%%</green> (opens in %s)" % self.util.time_to_readable(current_status_time - (3600 * 6))

            blob += "%s (%d) [%s] <highlight>QL %d</highlight> - %s %s\n" % (
                row.org_name,
                row.org_id,
                self.text.get_formatted_faction(row.faction),
                row.ql,
                self.util.time_to_readable(t - row.created_at),
                self.text.make_chatcmd("%dx%d" % (row.x_coord, row.y_coord), "/waypoint %d %d %d" % (row.x_coord, row.y_coord, row.playfield_id)))
            blob += "Close Time: <highlight>%s</highlight> %s\n" % (value.strftime("%H:%M:%S %Z"), status)
        else:
            blob += "%s\n" % self.text.make_chatcmd("%dx%d" % (row.x_coord, row.y_coord), "/waypoint %d %d %d" % (row.x_coord, row.y_coord, row.playfield_id))
            if not row.enabled:
                blob += "<red>Disabled</red>\n"

        return blob

    def get_tower_site_info(self, playfield_id, site_number):
        if FeatureFlags.USE_TOWER_API:
            params = {"playfield_id": playfield_id}
            if site_number:
                params["site_number"] = site_number

            data = self.lookup_tower_info(params).results
        else:
            if site_number:
                data = self.db.query("SELECT t.*, p.short_name AS playfield_short_name, p.long_name AS playfield_long_name "
                                     "FROM tower_site t JOIN playfields p ON t.playfield_id = p.id WHERE t.playfield_id = ? AND site_number = ?",
                                     [playfield_id, site_number])
            else:
                data = self.db.query("SELECT t.*, p.short_name AS playfield_short_name, p.long_name AS playfield_long_name "
                                     "FROM tower_site t JOIN playfields p ON t.playfield_id = p.id WHERE t.playfield_id = ?",
                                     [playfield_id])

        return data

    def lookup_tower_info(self, params):
        url = self.setting_service.get("tower_api_address").get_value()

        try:
            headers = self.setting_service.get("tower_api_custom_headers").get_value() or {}
            headers.update({"User-Agent": f"Tyrbot {self.bot.version}"})
            r = requests.get(url, params, headers=headers, timeout=5)
            result = DictObject(r.json())
        except ReadTimeout:
            self.logger.warning("Timeout while requesting '%s'" % url)
            result = None
        except Exception as e:
            self.logger.error("Error requesting history for url '%s'" % url, e)
            result = None

        return result

    def day_time(self, day_t):
        if day_t > 86400:
            day_t -= 86400
        elif day_t < 0:
            day_t += 86400
        return day_t

    def get_lc_blob_footer(self):
        return "Thanks to Draex and Unk for providing the tower information. And a special thanks to Trey."
