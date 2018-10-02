from core.decorators import instance
from core.dict_object import DictObject
from core.aochat import server_packets
from core.logger import Logger
from __init__ import none_to_empty_string
import requests
import time


@instance()
class PorkService:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.character_service = registry.get_instance("character_service")

    def pre_start(self):
        self.bot.add_packet_handler(server_packets.CharacterLookup.id, self.update)
        self.bot.add_packet_handler(server_packets.CharacterName.id, self.update)

    def get_character_info(self, char, max_cache_age=86400):
        char_id = self.character_service.resolve_char_to_id(char)
        char_name = self.character_service.resolve_char_to_name(char)

        t = int(time.time())

        # if we have entry in database and it is within the cache time, use that
        char_info = self.get_from_database(char_id=char_id, char_name=char_name)
        if char_info:
            if char_info.source == "chat_server":
                char_info = None
            elif char_info.last_updated > t - max_cache_age:
                char_info.cache_age = t - char_info.last_updated
                return char_info

        if char_name:
            url = "http://people.anarchy-online.com/character/bio/d/%d/name/%s/bio.xml?data_type=json" % (self.bot.dimension, char_name)
        else:
            return None

        r = requests.get(url)
        try:
            json = r.json()
        except ValueError as e:
            self.logger.warning("Error marshalling value as json: %s" % r.text, e)
            json = None

        if json:
            char_info_json = json[0]
            org_info_json = json[1] if json[1] else {}

            char_info = DictObject({
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
                "org_id": org_info_json.get("ORG_INSTANCE", 0),
                "org_name": org_info_json.get("NAME", ""),
                "org_rank_name": org_info_json.get("RANK_TITLE", ""),
                "org_rank_id": org_info_json.get("RANK", 0),
                "source": "people.anarchy-online.com"
            })

            self.save_character_info(char_info)

            char_info.cache_age = 0
            return char_info
        else:
            # return cached info from database, even tho it's old, and set cache_age (if it exists)
            if char_info:
                char_info.cache_age = t - char_info.last_updated

            return char_info

    def get_character_history(self, char):
        pass

    def load_character_info(self, char_id):
        char_info = self.get_character_info(char_id)
        if not char_info:
            char_info = DictObject({
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
                "org_id": 0,
                "org_name": "",
                "org_rank_name": "",
                "org_rank_id": 6,
                "source": "stub"
            })
            self.save_character_info(char_info)

    def save_character_info(self, char_info):
        self.db.exec("DELETE FROM player WHERE char_id = ?", [char_info["char_id"]])

        insert_sql = """
            INSERT INTO player ( char_id, name, first_name, last_name, level, breed, gender, faction, profession,
                profession_title, ai_rank, ai_level, org_id, org_name, org_rank_name, org_rank_id, dimension, head_id,
                pvp_rating, pvp_title, source, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

        self.db.exec(insert_sql, [char_info["char_id"], char_info["name"], char_info["first_name"], char_info["last_name"], char_info["level"], char_info["breed"],
                                  char_info["gender"], char_info["faction"], char_info["profession"], char_info["profession_title"], char_info["ai_rank"], char_info["ai_level"],
                                  char_info["org_id"], char_info["org_name"], char_info["org_rank_name"], char_info["org_rank_id"], char_info["dimension"], char_info["head_id"],
                                  char_info["pvp_rating"], char_info["pvp_title"], char_info["source"], int(time.time())])

    def get_from_database(self, char_id=None, char_name=None):
        if char_id:
            return self.db.query_single("SELECT char_id, name, first_name, last_name, level, breed, gender, faction, profession, "
                                        "profession_title, ai_rank, ai_level, org_id, org_name, org_rank_name, org_rank_id, "
                                        "dimension, head_id, pvp_rating, pvp_title, source, last_updated "
                                        "FROM player WHERE char_id = ?", [char_id])
        elif char_name:
            return self.db.query_single("SELECT char_id, name, first_name, last_name, level, breed, gender, faction, profession, "
                                        "profession_title, ai_rank, ai_level, org_id, org_name, org_rank_name, org_rank_id, "
                                        "dimension, head_id, pvp_rating, pvp_title, source, last_updated "
                                        "FROM player WHERE name = ?", [char_name])
        else:
            return None

    def update(self, packet):
        # don't update if we didn't get a valid response
        if packet.char_id == 4294967295:
            return

        character = self.get_from_database(char_id=packet.char_id)

        if character:
            if character.name != packet.name:
                self.db.exec("UPDATE player SET name = ? WHERE char_id = ?", [packet.name, packet.char_id])
        else:
            insert_sql = """
                INSERT INTO player ( char_id, name, first_name, last_name, level, breed, gender, faction, profession,
                profession_title, ai_rank, ai_level, org_id, org_name, org_rank_name, org_rank_id, dimension, head_id,
                pvp_rating, pvp_title, source, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

            self.db.exec(insert_sql, [packet.char_id, packet.name, "", "", 0, "", "",
                                      "", "", "", "", 0, 0, "", "", 6, 5, 0, 0, "",
                                      "chat_server", int(time.time())])
