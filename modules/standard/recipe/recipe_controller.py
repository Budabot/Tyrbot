from core.decorators import instance, command
from core.command_param_types import Item, Int
import os


@instance()
class RecipeController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")

    def start(self):
        self.db.load_sql_file("recipes.sql", os.path.dirname(__file__))

    @command(command="recipe", params=[Item("item", is_optional=True)], access_level="all",
             description="Search for a recipe")
    def recipe_cmd(self, channel, sender, reply, args):
        item = args[1]
        reply("Search results for <highlight>%s<end>" % item.name)
