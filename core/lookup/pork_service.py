from requests import ReadTimeout

from core.decorators import instance
from core.dict_object import DictObject
from core.aochat import server_packets
from core.logger import Logger
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

    def request_char_info(self, char_name, server_num):
        url = self.get_pork_url(server_num, char_name)

        try:
            r = requests.get(url, timeout=5)
            result = r.json()
        except ReadTimeout:
            self.logger.warning("Timeout while requesting '%s'" % url)
            result = None
        except ValueError as e:
            self.logger.debug("Error marshalling value as json for url '%s': %s" % (url, r.text), e)
            result = None

        char_info = None
        if result:
            char_info_json = result[0]
            org_info_json = result[1] if result[1] else {}

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
                "pvp_title": char_info_json["PVPTITLE"] or "",
                "head_id": char_info_json["HEADID"],
                "org_id": org_info_json.get("ORG_INSTANCE", 0),
                "org_name": org_info_json.get("NAME", ""),
                "org_rank_name": org_info_json.get("RANK_TITLE", ""),
                "org_rank_id": org_info_json.get("RANK", 0),
                "source": "people.anarchy-online.com",
                "cache_age": 0
            })

        return char_info

    def get_character_info(self, char, max_cache_age=86400):
        char_id = self.character_service.resolve_char_to_id(char)
        char_name = self.character_service.resolve_char_to_name(char)

        t = int(time.time())

        # if there is an entry in database and it is within the cache time, use that
        db_char_info = self.get_from_database(char_id=char_id, char_name=char_name)
        if db_char_info:
            db_char_info.cache_age = t - db_char_info.last_updated

            if db_char_info.cache_age < max_cache_age and db_char_info.source != "chat_server":
                return db_char_info

        # if we can't resolve to a char_name, we can't make a call to pork
        if not char_name:
            return db_char_info

        char_info = self.request_char_info(char_name, self.bot.dimension)

        if char_info and char_info.char_id == char_id:
            self.save_character_info(char_info)

            return char_info
        else:
            # return cached info from database, even tho it's old, and set cache_age (if it exists)
            if db_char_info:
                db_char_info.cache_age = t - db_char_info.last_updated

            return db_char_info

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
                "dimension": self.bot.dimension,
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
        if char_info["dimension"] != self.bot.dimension:
            return

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
                                      "", "", "", "", 0, 0, "", "", 6, self.bot.dimension, 0, 0, "",
                                      "chat_server", int(time.time())])

    def find_orgs(self, search):
        return self.db.query("SELECT DISTINCT org_name, org_id FROM player WHERE org_name <EXTENDED_LIKE=0> ?", [search], extended_like=True)

    def get_pork_url(self, dimension, char_name):
            return "http://people.anarchy-online.com/character/bio/d/%d/name/%s/bio.xml?data_type=json" % (dimension, char_name)
