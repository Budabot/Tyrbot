from core.decorators import instance, command


@instance()
class ImplantDesignerController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.pork_service = registry.get_instance("pork_service")

    def start(self):
        # self.db.exec("CREATE TABLE IF NOT EXISTS implant_design (owner INT NOT NULL, updated_at INT NOT NULL, data TEXT)")
        pass

    @command(command="implantdesigner", params=[], access_level="all",
             description="Show your current implant design")
    def implant_designer_cmd(self, request):
        pass


"""
# skill
{
    "id": 123
    "name": "1h Blunt"
    "amount": 23
}

# implant
{
    "type": "implant",
    "ql": 100,
    "requirements": {
        "treatment": 404,
        "agility": 0,
        "intelligence": 0,
        "psychic": 0,
        "sense": 0,
        "stamina": 0,
        "strength": 100
    },
    "skills": {
        "shiny": "skill_1",
        "bright": "skill_2",
        "faded": "skill_3"
    }
}

# symbiant
{
    "type": "symbiant",
    "name": "Living Artillery Ocular",
    "requirements": {
        "treatment": 404,
        "agility": 100,
        "intelligence": 0,
        "psychic": 100,
        "sense": 0,
        "stamina": 0,
        "strength": 100
    },
    "skills": [
        "skill_1",
        "skill_2",
        "skill_3"
    ]
}

# build
{
    "ear": None,
    "head": None,
    "eye": None,
    ...
}
"""
