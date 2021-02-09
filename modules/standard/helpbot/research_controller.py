from core.decorators import instance, command
from core.command_param_types import Int
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob


@instance()
class ResearchController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")

    def pre_start(self):
        self.db.load_sql_file(self.module_dir + "/" + "research.sql")

    @command(command="research", params=[Int("research_level")], access_level="all",
             description="Show information about a specific research level")
    def research_command(self, request, research_level):
        if research_level > 10 or research_level < 1:
            return "Research level must be between 1 and 10."

        row = self.db.query_single("SELECT * FROM research WHERE level = ?", [research_level])

        capsk = int(row.sk * 0.1)

        blob = "You must be level <highlight>%d</highlight> to research <highlight>Research Level %d</highlight>.\n" % (row.levelcap, research_level)
        blob += "You need <highlight>%s SK</highlight> to reach <highlight>Research Level %d</highlight> per research line.\n\n" % (self.util.format_number(row.sk), research_level)
        blob += "This equals <highlight>%s XP</highlight>.\n\n" % (self.util.format_number(row.sk * 1000))
        blob += "Your research will cap at <highlight>%s XP</highlight> or <highlight>%s SK</highlight>." % (self.util.format_number(capsk * 1000), self.util.format_number(capsk))

        return ChatBlob("Research Level %d" % research_level, blob)

    @command(command="research", params=[Int("research_level"), Int("research_level")], access_level="all",
             description="Show the amount of SK needed from one research level to another")
    def research_span_command(self, request, research_level1, research_level2):
        if research_level1 > 10 or research_level1 < 1 or research_level2 > 10 or research_level2 < 1:
            return "Research level must be between 1 and 10."
        elif research_level1 == research_level2:
            return "You must specify different research levels."

        if research_level1 > research_level2:
            # swap researches so the lower is research_level1 and higher is research_level2
            research_level1, research_level2 = research_level2, research_level1

        row = self.db.query_single("SELECT SUM(sk) AS total_sk, MAX(levelcap) AS levelcap FROM research WHERE level > ? AND level <= ?", [research_level1, research_level2])

        blob = "You must be <highlight>Level %d</highlight> to reach Research Level <highlight>%d.</highlight>\n" % (row.levelcap, research_level2)
        blob += "It takes <highlight>%s SK</highlight> to go from Research Level <highlight>%d</highlight> to Research Level <highlight>%d</highlight> per research line.\n\n" \
                % (self.util.format_number(row.total_sk), research_level1, research_level2)
        blob += "This equals <highlight>%s XP</highlight>." % self.util.format_number(row.total_sk * 1000)

        return ChatBlob("Research Levels %d - %d" % (research_level1, research_level2), blob)
