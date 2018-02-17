from core.decorators import instance


@instance()
class AccessManager:
    def __init__(self):
        self.access_levels = [{"label": "none", "level": 0, "handler": self.no_access}]

    def register_access_level(self, label, level, handler):
        self.access_levels.append({"label": label, "level": level, "handler": handler})

    def get_access_levels(self):
        return self.access_levels

    def no_access(self, char):
        return False
