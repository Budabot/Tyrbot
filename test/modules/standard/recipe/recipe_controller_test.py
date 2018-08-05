import unittest
from modules.standard.recipe.recipe_controller import RecipeController


class RecipeControllerTest(unittest.TestCase):

    def test_format_recipe_text(self):
        recipe_controller = RecipeController()

        self.assertEqual("this is a test\n<a href='chatcmd:///tell <myname> recipe 10'>Recipe 10</a>\nand this is the end",
                         recipe_controller.format_recipe_text("""this is a test\\n#L "Recipe 10" "/tell <myname> recipe 10"\\nand this is the end"""))
