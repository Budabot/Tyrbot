import time

from requests import ReadTimeout

from core.decorators import instance
from core.dict_object import DictObject
from core.logger import Logger
from __init__ import none_to_empty_string
import requests
import datetime
import json


@instance()
class OrgPorkService:
    CACHE_GROUP = "org_roster"
    CACHE_MAX_AGE = 86400

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.character_service = registry.get_instance("character_service")
        self.pork_service = registry.get_instance("pork_service")
        self.cache_service = registry.get_instance("cache_service")

    def get_org_info(self, org_id):
        cache_key = "%d.%d.json" % (org_id, self.bot.dimension)

        t = int(time.time())

        # check cache for fresh value
        cache_result = self.cache_service.retrieve(self.CACHE_GROUP, cache_key)

        is_cache = False
        if cache_result and cache_result.last_modified > (t - self.CACHE_MAX_AGE):
            result = json.loads(cache_result.data)
            is_cache = True
        else:
            url = "https://pork.jkbff.com/org/stats/d/%d/name/%d/basicstats.xml?data_type=json" % (self.bot.dimension, org_id)

            try:
                r = requests.get(url, timeout=5)
                result = r.json()

                # if data is invalid
                if result[0]["ORG_INSTANCE"] != org_id:
                    result = None
            except ReadTimeout:
                self.logger.warning("Timeout while requesting '%s'" % url)
                result = None
            except ValueError as e:
                self.logger.warning("Error marshalling value as json for url '%s': %s" % (url, r.text), e)
                result = None

            if result:
                # store result in cache
                self.cache_service.store(self.CACHE_GROUP, cache_key, json.dumps(result))
            elif cache_result:
                # check cache for any value, even expired
                result = json.loads(cache_result.data)
                is_cache = True

        if not result:
            return None

        org_info = result[0]
        org_members = result[1]
        last_updated = result[2]

        new_org_info = DictObject({
            "counts": {
                "gender": {
                    "Female": org_info["FEMALECOUNT"],
                    "Male": org_info["MALECOUNT"],
                    "Neuter": org_info["NEUTERCOUNT"],
                },
                "breed": {
                    "Atrox": org_info["ATROXCOUNT"],
                    "Nanomage": org_info["NANORACECOUNT"],
                    "Opifex": org_info["OPIFEXCOUNT"],
                    "Solitus": org_info["SOLITUSCOUNT"],
                },
                "profession": {
                    "Monster": org_info["MONSTERCOUNT"],
                    "Adventurer": org_info["ADVENTURERCOUNT"],
                    "Agent": org_info["AGENTCOUNT"],
                    "Bureaucrat": org_info["BTCOUNT"],
                    "Doctor": org_info["DOCTORCOUNT"],
                    "Enforcer": org_info["ENFCOUNT"],
                    "Engineer": org_info["ENGINEEERCOUNT"],
                    "Fixer": org_info["FIXERCOUNT"],
                    "Keeper": org_info["KEEPERCOUNT"],
                    "Martial Artist": org_info["MACOUNT"],
                    "Meta-Physicist": org_info["METACOUNT"],
                    "Nano-Technician": org_info["NANOCOUNT"],
                    "Shade": org_info["SHADECOUNT"],
                    "Soldier": org_info["SOLIDERCOUNT"],
                    "Trader": org_info["TRADERCOUNT"],
                }
            },
            "min_level": org_info["MINLVL"],
            "num_members": org_info["NUMMEMBERS"],
            "dimension": org_info["ORG_DIMENSION"],
            "governing_type": org_info["GOVERNINGNAME"],
            "max_level": org_info["MAXLVL"],
            "org_id": org_info["ORG_INSTANCE"],
            "objective": org_info["OBJECTIVE"],
            "description": org_info["DESCRIPTION"],
            "history": org_info["HISTORY"],
            "avg_level": org_info["AVGLVL"],
            "name": org_info["NAME"],
            "faction": org_info["SIDE_NAME"],
            "faction_id": org_info["SIDE"],
        })

        with self.db.transaction():
            members = {}
            for org_member in org_members:
                char_info = DictObject({
                    "name": org_member["NAME"],
                    "char_id": org_member["CHAR_INSTANCE"],
                    "first_name": org_member["FIRSTNAME"],
                    "last_name": org_member["LASTNAME"],
                    "level": org_member["LEVELX"],
                    "breed": org_member["BREED"],
                    "dimension": org_member["CHAR_DIMENSION"],
                    "gender": org_member["SEX"],
                    "faction": org_info["SIDE_NAME"],
                    "profession": org_member["PROF"],
                    "profession_title": org_member["PROF_TITLE"],
                    "ai_rank": org_member["DEFENDER_RANK_TITLE"],
                    "ai_level": org_member["ALIENLEVEL"],
                    "pvp_rating": org_member["PVPRATING"],
                    "pvp_title": none_to_empty_string(org_member["PVPTITLE"]),
                    "head_id": org_member["HEADID"],
                    "org_id": org_info.get("ORG_INSTANCE", 0),
                    "org_name": org_info.get("NAME", ""),
                    "org_rank_name": org_member.get("RANK_TITLE", ""),
                    "org_rank_id": org_member.get("RANK", 0),
                    "source": "people.anarchy-online.com"
                })

                if not is_cache:
                    self.pork_service.save_character_info(char_info)

                # prefetch char ids from chat server
                self.character_service._send_lookup_if_needed(char_info.name)

                members[char_info.char_id] = char_info

        if len(members) == 0:
            return None
        else:
            return DictObject({"last_modified": cache_result.last_modified if is_cache else t,
                               "org_info": new_org_info,
                               "org_members": members,
                               "last_updated": int(datetime.datetime.strptime(last_updated, "%Y/%m/%d %H:%M:%S").timestamp())})
