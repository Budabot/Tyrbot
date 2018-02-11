from decorators import instance


@instance
class SettingManager:
    def __init__(self):
        pass

    def inject(self, registry):
        pass

    def start(self):
        pass

    def get(self, name):
        # TODO
        return ""
