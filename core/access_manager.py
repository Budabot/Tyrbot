from operator import itemgetter

from core.decorators import instance


@instance()
class AccessManager:
    def __init__(self):
        self.access_levels = [
            {"label": "none", "level": 0, "handler": self.no_access},
            {"label": "all", "level": 100, "handler": self.all_access}]

    def register_access_level(self, label, level, handler):
        self.access_levels.append({"label": label, "level": level, "handler": handler})
        self.access_levels = sorted(self.access_levels, key=lambda k: k["level"])

    def get_access_levels(self):
        return self.access_levels

    def get_access_level(self, char):
        for access_level in self.access_levels:
            if access_level["handler"](char):
                return access_level

    def get_access_level_by_level(self, level):
        for access_level in self.access_levels:
            if access_level["level"] == level:
                return access_level["label"]
        return None

    def get_access_level_by_label(self, label):
        for access_level in self.access_levels:
            if access_level["label"] == label:
                return access_level["level"]
        return None

    def check_access(self, char, access_level_label):
        return self.get_access_level(char)["level"] <= self.get_access_level_by_label(access_level_label)

    def no_access(self, char):
        return False

    def all_access(self, char):
        return True
