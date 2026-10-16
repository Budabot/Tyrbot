from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any, Int, NamedParameters, Item
from core.dict_object import DictObject
import os
import re
import json

from core.logger import Logger


@instance()
class RecipeController:
    def __init__(self):
        self.logger = Logger(__name__)

        self.recipe_name_regex = re.compile(r"(\d+)\.json")
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

        self.db.exec("CREATE TABLE IF NOT EXISTS recipe (id INT NOT NULL PRIMARY KEY, name VARCHAR(50) NOT NULL, author VARCHAR(50) NOT NULL, recipe TEXT NOT NULL, dt INT NOT NULL DEFAULT 0)")

        recipe_dir = os.path.dirname(os.path.realpath(__file__)) + "/recipes/"
        recipes = self.db.query("SELECT id, dt FROM recipe")

        for file in os.listdir(recipe_dir):
            if file.startswith("_"):
                continue

            m = self.recipe_name_regex.match(file)
            if m:
                recipe_id = m.group(1)
                dt = int(os.path.getmtime(recipe_dir + file))

                recipe = self.find_recipe(recipe_id, recipes)
                if recipe:
                    recipes.remove(recipe)
                    if recipe.dt == dt:
                        continue

                self.update_recipe(recipe_dir, recipe_id, dt)
            else:
                raise Exception("Unknown recipe format for '%s'" % file)

        # Remove recipes whose file no longer exists
        for recipe in recipes:
            self.db.exec("DELETE FROM recipe WHERE id = ?", [recipe.id])

    @command(command="recipe", params=[Int("recipe_id")], access_level="all", description="Show a recipe")
    def recipe_show_cmd(self, request, recipe_id):
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return "Could not find recipe with ID <highlight>%d</highlight>." % recipe_id

        return self.format_recipe(recipe)

    @command(command="recipe", params=[Item("item"), NamedParameters(["page"])], access_level="all", description="Search for a recipe")
    def recipe_search_item_cmd(self, request, item, named_params):
        page_number = int(named_params.page or "1")

        return self.get_search_results(item.name, page_number)

    @command(command="recipe", params=[Any("search"), NamedParameters(["page"])], access_level="all", description="Search for a recipe")
    def recipe_search_cmd(self, request, search, named_params):
        page_number = int(named_params.page or "1")

        return self.get_search_results(search, page_number)

    def get_search_results(self, search, page_number):
        page_size = 30
        offset = (page_number - 1) * page_size

        data = self.db.query("SELECT * FROM recipe WHERE recipe <EXTENDED_LIKE=0> ? ORDER BY name ASC", [search], extended_like=True)
        count = len(data)
        paged_data = data[offset:offset + page_size]

        blob = ""

        if len(data) == 0:
            return "No recipe matching <highlight>%s</highlight>." % search

        elif len(data) == 1:
            return self.format_recipe(data[0])

        else:
            blob += self.text.get_paging_links(f"recipe {search}", page_number, offset + page_size < len(data))
            blob += "\n\n"

            for row in paged_data:
                blob += self.text.make_tellcmd(row.name, "recipe %d" % row.id) + "\n"

            return ChatBlob("Recipes Matching '%s' (%d - %d of %d)" % (search, offset + 1, min(offset + page_size, count), count), blob)

    def get_recipe(self, recipe_id):
        return self.db.query_single("SELECT * FROM recipe WHERE id = ?", [recipe_id])

    def format_recipe(self, recipe):
        blob = "Recipe ID: <highlight>%d</highlight>\n" % recipe.id
        blob += "Author: <highlight>%s</highlight>\n\n" % (recipe.author or "Unknown")
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

    def find_recipe(self,recipe_id,recipes):
        for row in recipes:
            if str(row.id) == recipe_id:
                return row
        return None

    def update_recipe(self, recipe_dir, recipe_id, dt):
        with open(recipe_dir + recipe_id + ".json", mode="r", encoding="UTF-8") as f:
            recipe = json.load(f)

        name = recipe["name"]
        author = recipe["author"]

        if "raw" in recipe:
            content = recipe["raw"]
        else:
            content = self.format_json_recipe(recipe_id, recipe)

        self.db.exec("REPLACE INTO recipe (id, name, author, recipe, dt) VALUES (?, ?, ?, ?, ?)", [recipe_id, name, author, content, dt])

    def format_json_recipe(self, recipe_id, recipe):
        items = {}
        for i in recipe["items"]:
            if "item_id" in i:
                item = self.get_recipe_item(recipe_id, i)
            else:
                # Placeholder for an unknown item; displayed by name only, without a link
                item = DictObject({"name": i["name"], "icon": i.get("icon")})

            item.quantity = i.get("quantity")
            item.comment = i.get("comment")
            items[i["alias"]] = item

        content = ""

        if "intro" in recipe:
            content += self.format_detail_entries(recipe["intro"]) + "\n"

        results = set(step["result"] for step in recipe["steps"] if "text" not in step)
        ingredients = [(alias, item) for alias, item in items.items() if alias not in results]

        content += self.format_ingredients(ingredients)
        content += "\n"
        content += self.format_steps(items, recipe["steps"])

        if "details" in recipe:
            content += self.format_details(recipe["details"])

        return content

    def get_recipe_item(self, recipe_id, i):
        item = self.items_controller.get_by_item_id(i["item_id"], i.get("ql"))
        if item:
            item.ql = i.get("ql") or (item.highql if i["item_id"] == item.highid else item.lowql)
        elif "name" in i and "icon" in i and "ql" in i:
            # Item missing from the items db; displayed from the recipe's own name, icon and ql
            item = DictObject({"lowid": i["item_id"], "highid": i["item_id"], "ql": i["ql"], "name": i["name"], "icon": i["icon"]})
        else:
            raise Exception("Could not find recipe item '%d' for recipe id %s" % (i["item_id"], recipe_id))
        return item

    def format_ingredients(self, ingredients):
        content = "<font color=#FFFF00>------------------------------</font>\n"
        content += "<font color=#FF0000>Ingredients</font>\n"
        content += "<font color=#FFFF00>------------------------------</font>\n\n"

        for _, ingredient in ingredients:
            if ingredient.icon is not None:
                content += self.text.make_image(ingredient.icon)
            content += "<tab>" + self.format_item_name(ingredient)
            content += self.format_item_notes(ingredient) + "\n"

        return content

    def format_item_name(self, item):
        if "lowid" not in item:
            return item.name
        return self.text.make_item(item.lowid, item.highid, item.ql, item.name)

    def format_item_icon(self, item):
        image = item.name if item.icon is None else self.text.make_image(item.icon)
        if "lowid" not in item:
            return image
        return "<a href='itemref://%d/%d/%d'>%s</a>" % (item.lowid, item.highid, item.ql, image)

    def format_item_notes(self, item):
        content = ""
        if item.quantity:
            content += " x %s" % item.quantity
        if item.comment:
            content += " - " + item.comment
        return content

    def format_steps(self, items, steps):
        content = ""
        content += "<font color=#FFFF00>------------------------------</font>\n"
        content += "<font color=#FF0000>Recipe</font>\n"
        content += "<font color=#FFFF00>------------------------------</font>\n\n"

        for step in steps:
            if "text" in step:
                content += "<font color=#FFFFFF>%s</font>\n\n" % step["text"]
                continue

            source = items[step["source"]]
            target = items[step["target"]]
            result = items[step["result"]]
            content += self.format_item_icon(source)
            content += "<font color=#FFFFFF><tab>+<tab></font> "
            content += self.format_item_icon(target)
            content += "<font color=#FFFFFF><tab>=<tab></font> "
            content += self.format_item_icon(result)
            content += "\n<tab><tab>" + self.format_item_name(source)
            content += "\n + <tab>" + self.format_item_name(target)
            content += "\n = <tab>" + self.format_item_name(result)
            content += self.format_item_notes(result) + "\n"

            if "skills" in step:
                content += "<font color=#FFFF00>Skills: | %s |</font>\n" % step["skills"]
            content += "\n\n"

        return content

    def format_details(self, details):
        content = ""
        content += "<font color=#FFFF00>------------------------------</font>\n"
        content += "<font color=#FF0000>Details</font>\n"
        content += "<font color=#FFFF00>------------------------------</font>\n\n"
        content += self.format_detail_entries(details)

        return content

    def format_detail_entries(self, details):
        content = ""
        last_type = ""
        for detail in details:
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

        return content
