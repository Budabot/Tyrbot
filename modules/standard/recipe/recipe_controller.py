from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any, Int, NamedParameters
import os
import re
import json


@instance()
class RecipeController:
    def __init__(self):
        self.recipe_name_regex = re.compile(r"(\d+)\.(txt|json)")
        self.recipe_item_regex = re.compile(r"#L \"([^\"]+)\" \"([\d+]+)\"")
        self.recipe_link_regex = re.compile(r"#L \"([^\"]+)\" \"([^\"]+)\"")

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.items_controller = registry.get_instance("items_controller")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("r", "recipe")
        self.command_alias_service.add_alias("tradeskill", "recipe")

        recipe_dir = os.path.dirname(os.path.realpath(__file__)) + "/recipes/"
        self.db.exec("DROP TABLE IF EXISTS recipe")
        self.db.exec("CREATE TABLE recipe (id INT NOT NULL PRIMARY KEY, name VARCHAR(50) NOT NULL, author VARCHAR(50) NOT NULL, recipe TEXT NOT NULL);")

        for file in os.listdir(recipe_dir):
            m = self.recipe_name_regex.match(file)
            if m:
                recipe_id = m.group(1)
                file_type = m.group(2)

                if file_type == "txt":
                    with open(recipe_dir + file) as f:
                        lines = f.readlines()

                    name = lines.pop(0).strip()[6:]
                    author = lines.pop(0).strip()[8:]
                    content = "".join(lines)

                    self.db.exec("INSERT INTO recipe (id, name, author, recipe) VALUES (?, ?, ?, ?)", [recipe_id, name, author, content])
                elif file_type == "json":
                    with open(recipe_dir + file) as f:
                        recipe = json.load(f)

                    name = recipe["name"]
                    author = recipe["author"]

                    items = {}
                    for i in recipe["items"]:
                        item = self.items_controller.get_by_item_id(i["item_id"], i.get("ql"))
                        if not item:
                            raise Exception("Could not fund recipe item '%d' for recipe id %s" % (i["item_id"], recipe_id))

                        item.ql = i.get("ql") or (item.highql if i["item_id"] == item.highid else item.lowql)
                        items[i["alias"]] = item

                    content = "<font color=#FFFF00>------------------------------</font>\n"
                    content += "<font color=#FF0000>Ingredients</font>\n"
                    content += "<font color=#FFFF00>------------------------------</font>\n\n"

                    ingredients = items.copy()
                    for step in recipe["steps"]:
                        del ingredients[step["result"]]

                    for _, ingredient in ingredients.items():
                        content += self.text.make_image(ingredient["icon"]) + "<tab>"
                        content += self.text.make_item(ingredient["lowid"], ingredient["highid"], ingredient["ql"], ingredient["name"]) + "\n"

                    content += "\n"
                    content += "<font color=#FFFF00>------------------------------</font>\n"
                    content += "<font color=#FF0000>Recipe</font>\n"
                    content += "<font color=#FFFF00>------------------------------</font>\n\n"

                    for step in recipe["steps"]:
                        source = items[step["source"]]
                        target = items[step["target"]]
                        result = items[step["result"]]
                        content += "<a href='itemref://%d/%d/%d'>%s</a>" % \
                                   (source["lowid"], source["highid"], source["ql"],
                                    self.text.make_image(source["icon"])) + ""
                        content += "<font color=#FFFFFF><tab>+<tab></font> "
                        content += "<a href='itemref://%d/%d/%d'>%s</a>" % \
                                   (target["lowid"], target["highid"], target["ql"],
                                    self.text.make_image(target["icon"])) + ""
                        content += "<font color=#FFFFFF><tab>=<tab></font> "
                        content += "<a href='itemref://%d/%d/%d'>%s</a>" % \
                                   (result["lowid"], result["highid"], result["ql"],
                                    self.text.make_image(result["icon"]))
                        content += "\n<tab><tab>" + self.text.make_item(source["lowid"], source["highid"], source["ql"], source["name"])
                        content += "\n + <tab>" + self.text.make_item(target["lowid"], target["highid"], target["ql"], target["name"])
                        content += "\n = <tab>" + self.text.make_item(result["lowid"], result["highid"], result["ql"], result["name"]) + "\n"

                        if "skills" in step:
                            content += "<font color=#FFFF00>Skills: | %s |</font>\n" % step["skills"]
                        content += "\n\n"

                    if "details" in recipe:
                        content += "<font color=#FFFF00>------------------------------</font>\n"
                        content += "<font color=#FF0000>Details</font>\n"
                        content += "<font color=#FFFF00>------------------------------</font>\n\n"

                        last_type = ""
                        for detail in recipe["details"]:
                            if "item" in detail:
                                last_type = "item"
                                i = detail["item"]

                                item = None
                                if "ql" in i:
                                    item = self.items_controller.get_by_item_id(i["id"], i["ql"])
                                else:
                                    item = self.items_controller.get_by_item_id(i["id"])
                                    item["ql"] = item["highql"]

                                content += "<font color=#009B00>%s</font>" % \
                                           self.text.make_item(item["lowid"],
                                                               item["highid"],
                                                               item["ql"],
                                                               item["name"])

                                if "comment" in i:
                                    content += " - " + i["comment"]

                                content += "\n"

                            elif "text" in detail:
                                if last_type == "item":
                                    content += "\n"

                                last_type = "text"
                                content += "<font color=#FFFFFF>%s</font>\n" % detail["text"]

                    self.db.exec("INSERT INTO recipe (id, name, author, recipe) VALUES (?, ?, ?, ?)", [recipe_id, name, author, content])

            elif file.startswith("_"):
                pass
            else:
                raise Exception("Unknown recipe format for '%s'" % file)

    @command(command="recipe", params=[Int("recipe_id")], access_level="all",
             description="Show a recipe")
    def recipe_show_cmd(self, request, recipe_id):
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return "Could not find recipe with ID <highlight>%d<end>." % recipe_id

        return self.format_recipe(recipe)

    @command(command="recipe", params=[Any("search"), NamedParameters(["page"])], access_level="all",
             description="Search for a recipe")
    def recipe_search_cmd(self, request, search, named_params):
        page = int(named_params.page or "1")
        page_size = 30
        offset = (page - 1) * page_size

        data = self.db.query("SELECT * FROM recipe WHERE recipe <EXTENDED_LIKE=0> ? ORDER BY name ASC", [search], extended_like=True)
        count = len(data)
        paged_data = data[offset:offset + page_size]

        blob = ""

        if count > page_size:
            if page > 1 and len(paged_data) > 0:
                blob += "   " + self.text.make_chatcmd("<< Page %d" % (page - 1), self.get_chat_command(search, page - 1))
            if offset + page_size < len(data):
                blob += "   Page " + str(page)
                blob += "   " + self.text.make_chatcmd("Page %d >>" % (page + 1), self.get_chat_command(search, page + 1))
            blob += "\n\n"

        for row in paged_data:
            blob += self.text.make_chatcmd(row.name, "/tell <myname> recipe %d" % row.id) + "\n"

        return ChatBlob("Recipes Matching '%s' (%d - %d of %d)" % (search, offset + 1, min(offset + page_size, count), count), blob)

    def get_recipe(self, recipe_id):
        return self.db.query_single("SELECT * FROM recipe WHERE id = ?", [recipe_id])

    def format_recipe(self, recipe):
        blob = "Recipe ID: <highlight>%d<end>\n" % recipe.id
        blob += "Author: <highlight>%s<end>\n\n" % (recipe.author or "Unknown")
        blob += self.format_recipe_text(recipe.recipe)

        return ChatBlob("Recipe for '%s'" % recipe.name, blob)

    def format_recipe_text(self, recipe_text):
        recipe_text = recipe_text.replace("\\n", "\n")
        recipe_text = self.recipe_item_regex.sub(self.lookup_item, recipe_text)
        recipe_text = self.recipe_link_regex.sub("<a href='chatcmd://\\2'>\\1</a>", recipe_text)
        return recipe_text

    def lookup_item(self, m):
        name = m.group(1)
        item_id = m.group(2)

        item = self.items_controller.get_by_item_id(item_id)
        if item:
            return self.text.make_item(item.lowid, item.highid, item.highql, item.name)
        else:
            return name

    def get_chat_command(self, search, page):
        return "/tell <myname> recipe %s --page=%d" % (search, page)
