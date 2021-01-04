class DictObject(dict):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def get_value(self, name):
        val = self[name]
        # convert dict to DictObject
        if isinstance(val, dict) and not isinstance(val, DictObject):
            self[name] = DictObject(val)
            val = self[name]

        # convert list of dicts to list of DictObjects
        elif isinstance(val, list):
            for k, v in enumerate(val):
                if isinstance(v, dict) and not isinstance(v, DictObject):
                    self[name][k] = DictObject(v)
            val = self[name]

        return val

    def __getattr__(self, name):
        return self.get_value(name)

    def __setattr__(self, key, value):
        self[key] = value
