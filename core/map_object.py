class MapObject(dict):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def get_value(self, name):
        val = self[name]
        if isinstance(val, dict) and not isinstance(val, MapObject):
            self[name] = MapObject(val)
            val = self[name]

        return val

    def __getattr__(self, name):
        return self.get_value(name)

    def __setattr__(self, key, value):
        self[key] = value
