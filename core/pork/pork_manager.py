from core.decorators import instance
from core import MapObject
import requests
import os


@instance()
class PorkManager:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("budabot")
        self.db = registry.get_instance("db")
        self.character_manager = registry.get_instance("character_manager")

    def start(self):
        self.db.load_sql_file("characters.sql", os.path.dirname(__file__))

    def get_character_info(self, char):
        char_name = self.character_manager.resolve_char_to_name(char)
        url = "http://people.anarchy-online.com/character/bio/d/%d/name/%s/bio.xml?data_type=json" %\
              (self.bot.dimension, char_name)

        r = requests.get(url)
        json = r.json()
        if json:
            char_info_json = json[0]
            org_info_json = json[1]

            if org_info_json:
                org_info = MapObject({
                    "name": org_info_json["NAME"],
                    "id": org_info_json["ORG_INSTANCE"],
                    "rank_name": org_info_json["RANK_TITLE"],
                    "rank_id": org_info_json["RANK"]
                })
            else:
                org_info = None

            return MapObject({
                "name": char_info_json["NAME"],
                "char_id": char_info_json["CHAR_INSTANCE"],
                "first_name": char_info_json["LASTNAME"],
                "last_name": char_info_json["LASTNAME"],
                "level": char_info_json["LEVELX"],
                "breed": char_info_json["BREED"],
                "dimension": char_info_json["CHAR_DIMENSION"],
                "gender": char_info_json["SEX"],
                "faction": char_info_json["SIDE"],
                "profession": char_info_json["PROF"],
                "profession_title": char_info_json["PROFNAME"],
                "ai_rank": char_info_json["RANK_name"],
                "ai_level": char_info_json["ALIENLEVEL"],
                "pvp_rating": char_info_json["PVPRATING"],
                "pvp_title": char_info_json["PVPTITLE"],
                "head_id": char_info_json["HEADID"],
                "org": org_info
            })
        else:
            return None

    def get_character_history(self, char):
        pass

    def get_org_info(self, org_id):
        pass
