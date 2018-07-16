from core.decorators import instance
from core.logger import Logger
from __init__ import none_to_empty_string
import requests
import datetime


@instance()
class OrgPorkManager:
    def __init__(self):
        self.logger = Logger("org_pork_manager")

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.character_manager = registry.get_instance("character_manager")
        self.pork_manager = registry.get_instance("pork_manager")

    def get_org_info(self, org_id):
        url = "http://people.anarchy-online.com/org/stats/d/%d/name/%d/basicstats.xml?data_type=json" % (self.bot.dimension, org_id)

        r = requests.get(url)
        try:
            json = r.json()
        except ValueError as e:
            self.logger.warning("Error marshalling value as json: %s" % r.text, e)
            json = None

        org_info = json[0]
        org_members = json[1]
        last_updated = json[2]

        new_org_info = {
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
            "governing_name": org_info["GOVERNINGNAME"],
            "max_level": org_info["MAXLVL"],
            "org_id": org_info["ORG_INSTANCE"],
            "objective": org_info["OBJECTIVE"],
            "description": org_info["DESCRIPTION"],
            "history": org_info["HISTORY"],
            "avg_level": org_info["AVGLVL"],
            "name": org_info["NAME"],
            "faction": org_info["SIDE_NAME"],
            "faction_id": org_info["SIDE"],
        }

        members = []
        for org_member in org_members:
            char_info = {
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
            }

            self.pork_manager.save_character_info(char_info)

            members.append(char_info)

        return {"org_info": new_org_info,
                "org_members": members,
                "last_updated": int(datetime.datetime.strptime(last_updated, "%Y/%m/%d %H:%M:%S").timestamp())}
