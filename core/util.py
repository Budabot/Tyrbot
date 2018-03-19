from core.decorators import instance


@instance()
class Util:
    def __init__(self):
        pass

    def get_handler_name(self, handler):
        return handler.__module__ + "." + handler.__qualname__

    def get_module_name(self, handler):
        handler_name = self.get_handler_name(handler)
        return handler_name.split(".")[1]
