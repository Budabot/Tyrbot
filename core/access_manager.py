from core.decorators import instance
from core.logger import Logger


@instance()
class AccessManager:
    def __init__(self):
        self.access_levels = [
            {"label": "none", "level": 0, "handler": self.no_access},
            {"label": "all", "level": 100, "handler": self.all_access}]
        self.logger = Logger("access_manager")

    def inject(self, registry):
        self.character_manager = registry.get_instance("character_manager")
        self.alts_manager = registry.get_instance("alts_manager")

    def register_access_level(self, label, level, handler):
        self.logger.debug("Registering access level %d with label '%s'" % (level, label))
        self.access_levels.append({"label": label.lower(), "level": level, "handler": handler})
        self.access_levels = sorted(self.access_levels, key=lambda k: k["level"])

    def get_access_levels(self):
        return self.access_levels

    def get_access_level(self, char):
        char_id = self.character_manager.resolve_char_to_id(char)
        if not char_id:
            return None

        alts = self.alts_manager.get_alts(char_id)
        main = alts[0]
        access_level1 = self.get_single_access_level(char_id)
        if main.char_id == char_id:
            return access_level1
        else:
            access_level2 = self.get_single_access_level(main.char_id)
            if access_level1["level"] < access_level2["level"]:
                return access_level1
            else:
                return access_level2

    def get_single_access_level(self, char):
        char_id = self.character_manager.resolve_char_to_id(char)
        for access_level in self.access_levels:
            if access_level["handler"](char_id):
                return access_level

    def get_access_level_by_level(self, level):
        for access_level in self.access_levels:
            if access_level["level"] == level:
                return access_level
        return None

    def get_access_level_by_label(self, label):
        for access_level in self.access_levels:
            if access_level["label"] == label.lower():
                return access_level
        return None

    def check_access(self, char, access_level_label):
        return self.get_access_level(char)["level"] <= self.get_access_level_by_label(access_level_label)["level"]

    def no_access(self, char_id):
        return False

    def all_access(self, char_id):
        return True
