from core.decorators import instance, command
from core.command_param_types import Any, Const
from core.chat_blob import ChatBlob
import json


@instance()
class SqlController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")

    @command(command="sql", params=[Const("query"), Any("sql_statement")], access_level="superadmin",
             description="Execute a SQL query and return the results")
    def sql_cmd(self, channel, sender, reply, args):
        sql = args[1]
        try:
            results = list(map(lambda x: x.row, self.db.query(sql)))
            reply(ChatBlob("Results (%d)" % len(results), json.dumps(results, indent=4, sort_keys=True)))
        except Exception as e:
            reply("There was an error executing your query: %s" % str(e))
