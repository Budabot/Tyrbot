from core.decorators import instance


@instance()
class SettingManager:
    def __init__(self):
        self.settings = {}

    def register(self, name, value, description):
        self.settings[name] = {"value": value, "description": description}

    def get(self, name):
        return self.settings.get(name).get("value")
