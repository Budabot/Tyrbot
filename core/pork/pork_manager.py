from core.decorators import instance
from core import MapObject, none_to_empty_string
import requests
import time
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
        self.db.load_sql_file("character.sql", os.path.dirname(__file__))

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

            char_info = MapObject({
                "name": char_info_json["NAME"],
                "char_id": char_info_json["CHAR_INSTANCE"],
                "first_name": char_info_json["FIRSTNAME"],
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
                "pvp_title": none_to_empty_string(char_info_json["PVPTITLE"]),
                "head_id": char_info_json["HEADID"],
                "source": "people.anarchy-online.com",
                "org": org_info
            })

            self.save_character_info(char_info)
            return char_info
        else:
            return None

    def get_character_history(self, char):
        pass

    def get_org_info(self, org_id):
        pass

    def load_character_info(self, char_id):
        char_info = self.get_character_info(char_id)
        if not char_info:
            char_info = MapObject({
                "name": "Unknown:" + str(char_id),
                "char_id": char_id,
                "first_name": "",
                "last_name": "",
                "level": 0,
                "breed": "",
                "dimension": 5,
                "gender": "",
                "faction": "",
                "profession": "",
                "profession_title": "",
                "ai_rank": "",
                "ai_level": 0,
                "pvp_rating": 0,
                "pvp_title": "",
                "head_id": 0,
                "source": "stub",
                "org": None
            })
            self.save_character_info(char_info)

    def save_character_info(self, char_info):
        c = char_info
        o = c.org
        if not o:
            o = MapObject({
                    "name": "",
                    "id": 0,
                    "rank_name": "",
                    "rank_id": 0
                })

        self.db.exec("DELETE FROM character WHERE char_id = ?", [char_info.char_id])

        insert_sql = """
            INSERT INTO character ( char_id, name, first_name, last_name, level, breed, gender, faction, profession,
                profession_title, ai_rank, ai_level, org_id, org_name, org_rank_name, org_rank_id, dimension, head_id,
                pvp_rating, pvp_title, source, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

        self.db.exec(insert_sql, [c.char_id, c.name, c.first_name, c.last_name, c.level, c.breed, c.gender, c.faction,
                                  c.profession, c.profession_title, c.ai_rank, c.ai_level, o.id, o.name,
                                  o.rank_name, o.rank_id, c.dimension, c.head_id, c.pvp_rating, c.pvp_title,
                                  c.source, int(time.time())])
