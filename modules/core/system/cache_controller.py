import os

from core.command_param_types import Const, Any
from core.decorators import instance, command


@instance()
class CacheController:
    invalid_chars = ["/", "\\", ".."]

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")

    @command(command="cache", params=[Const("delete"), Any("category"), Any("filename")], access_level="superadmin",
             description="Manually remove a cache entry")
    def cache_remove_cmd(self, request, _, category, filename):
        full_file_path = os.sep.join([".", "data", "cache", category, filename])
        full_file_path = os.path.normpath(full_file_path)
        if not full_file_path.startswith(os.path.normpath(os.sep.join([".", "data", "cache"]))):
            return f"<highlight>{full_file_path}</highlight> is not a valid cache entry."

        if os.path.isfile(full_file_path):
            os.remove(full_file_path)
            return f"Cache entry <highlight>{full_file_path}</highlight> has been removed."
        else:
            return f"Cache entry <highlight>{full_file_path}</highlight> does not exist or is not a file."
