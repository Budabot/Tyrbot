from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.command_param_types import Any
from core.chat_blob import ChatBlob


@instance()
class WhompahController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.pork_manager = registry.get_instance("pork_manager")

    @command(command="whompah", params=[], access_level="all",
             description="Show list of whompah cities")
    def whompah_list_cmd(self, channel, sender, reply, args):
        cities = self.db.query("SELECT id, city_name, zone, faction, short_name FROM whompah_cities ORDER BY city_name ASC")

        blob = ""
        for city in cities:
            blob += "%s (%s)\n" % (city.city_name, self.text.make_chatcmd(city.short_name, "/tell <myname> whompah %s" % city.short_name))

        reply(ChatBlob("Whompah Cities", blob))

    @command(command="whompah", params=[Any("city1"), Any("city2")], access_level="all",
             description="Show whompah route between two cities")
    def whompah_travel_cmd(self, channel, sender, reply, args):
        city_name1 = args[0]
        city_name2 = args[1]
        city1 = self.get_whompah_city(city_name1)
        city2 = self.get_whompah_city(city_name2)

        if not city1:
            reply("Could not find whompah city <highlight>%s<end>." % city_name1)
            return
        elif not city2:
            reply("Could not find whompah city <highlight>%s<end>." % city_name2)
            return

        data = self.db.query("SELECT w1.*, w2.city2_id AS city_rel FROM whompah_cities w1 JOIN whompah_cities_rel w2 ON w1.id = w2.city1_id")

        cities = {}
        for city in data:
            rel = cities.get(city.id, {}).get("rel", [])
            rel.append(city.city_rel)
            cities[city.id] = city.row
            cities[city.id]["rel"] = rel

        path = self.format_path(self.find_path(cities, city1.id, city2.id))
        reply(" -> ".join(path))

    @command(command="whompah", params=[Any("city")], access_level="all",
             description="Show whompah destinations for a city")
    def whompah_city_cmd(self, channel, sender, reply, args):
        city_name = args[0]
        city = self.get_whompah_city(city_name)

        if not city:
            reply("Could not find whompah city <highlight>%s<end>." % city_name)
            return

        cities = self.db.query("SELECT w2.* FROM whompah_cities_rel w1 JOIN whompah_cities w2 ON w1.city2_id = w2.id WHERE w1.city1_id = ?", [city.id])
        msg = "From %s you can get to: " % city.city_name
        msg += ", ".join(map(lambda x: "<highlight>%s<end> (%s)" % (x.city_name, x.short_name), cities))
        reply(msg)

    def get_whompah_city(self, city):
        return self.db.query_single("SELECT id, city_name, zone, faction, short_name FROM whompah_cities WHERE city_name LIKE ? OR short_name LIKE ?", [city, city])

    def find_path(self, cities, start_city_id, end_city_id):
        def get_and_remove(key):
            value = cities[key]
            del cities[key]
            return value

        end_city = get_and_remove(end_city_id)

        if start_city_id == end_city_id:
            return end_city

        # create stack and initialize
        # start with ending city and traverse backwards so we don't have to reverse the result
        stack = [end_city]
        while stack:
            root = stack.pop(0)
            for rel in root["rel"]:
                if rel in cities:
                    c = get_and_remove(rel)
                    c["parent"] = root
                    if c["id"] == start_city_id:
                        return c
                    stack.append(c)
        return None

    def format_path(self, path):
        result = []
        root = path
        while root:
            result.append(root["city_name"])
            root = root.get("parent")
        return result
