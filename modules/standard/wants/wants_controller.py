from core.command_param_types import Any, Int, Const, Options, Item
from core.decorators import instance, command
from core.chat_blob import ChatBlob
import time


@instance()
class WantsController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.alts_service = registry.get_instance("alts_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS wants ("
                     "id INT PRIMARY KEY AUTO_INCREMENT, "
                     "char_id INT NOT NULL, "
                     "want TEXT NOT NULL,"
                     "created_at INT NOT NULL)")

    @command(command="wants", params=[], access_level="all",
             description="Show your wants")
    def wants_list_cmd(self, request):
        alts = self.alts_service.get_alts(request.sender.char_id)

        cnt = 0
        blob = ""
        for alt in alts:
            data = self.db.query("SELECT * FROM wants WHERE char_id = ? ORDER BY created_at DESC", [alt.char_id])
            alt_cnt = len(data)
            cnt += alt_cnt

            if alt_cnt:
                for row in data:
                    blob += "%s %s\n\n" % (row.want, self.text.make_tellcmd("Remove", "wants remove %d" % row.id))

        return ChatBlob("Wants for %s (%d)" % (alts[0].name, cnt), blob)

    @command(command="wants", params=[Const("add"), Any("item")], access_level="all",
             description="Add a want")
    def wants_add_cmd(self, request, _, want):
        self.db.exec("INSERT INTO wants (char_id, want, created_at) VALUES (?, ?, ?)", [request.sender.char_id, want, int(time.time())])

        return "Want added successfully."

    @command(command="wants", params=[Options(["rem", "remove"]), Int("want_id")], access_level="all",
             description="Remove a want")
    def wants_remove_cmd(self, request, _, want_id):
        want = self.db.query_single("SELECT n.*, p.name FROM wants n LEFT JOIN player p ON n.char_id = p.char_id WHERE n.id = ?", [want_id])

        if not want:
            return "Could not find want with ID <highlight>%d</highlight>." % want_id

        if self.alts_service.get_main(request.sender.char_id).char_id != self.alts_service.get_main(want.char_id).char_id:
            return "You must be a confirmed alt of <highlight>%s</highlight> to remove this want." % want.name

        self.db.exec("DELETE FROM wants WHERE id = ?", [want_id])

        return "Want with ID <highlight>%d</highlight> deleted successfully." % want_id

    @command(command="wants", params=[Const("search"), Item("item")], access_level="all",
             description="Search wants by itemref")
    def wants_search_itemref_cmd(self, request, _, item):
        return self.search_wants(item.name)

    @command(command="wants", params=[Const("search"), Any("name")], access_level="all",
             description="Search wants by name")
    def wants_search_name_cmd(self, request, _, wants_search):
        return self.search_wants(wants_search)

    def search_wants(self, wants_search):
        wants = self.db.query("SELECT w.char_id, w.want, p.name FROM wants w LEFT JOIN player p ON w.char_id = p.char_id WHERE want LIKE ?", ["%" + wants_search + "%"])

        blob = ""
        for want in wants:
            alts = self.alts_service.get_alts(want.char_id)
            main_name = alts[0].name
            blob += "<header2>%s</header2>\n%s\n\n" % (main_name, want.want)

        return ChatBlob("Search Results (%d)" % len(wants), blob)

    @command(command="wants", params=[Const("list")], access_level="all",
             description="Shows all wants")
    def wants_all_cmd(self, request, _):
        sql = "SELECT w.*, p.name FROM wants w \
               LEFT JOIN alts a ON w.char_id = a.char_id \
               LEFT JOIN alts a2 ON (a2.group_id = a.group_id AND a2.status = 2) \
               LEFT JOIN player p ON p.char_id = COALESCE(a2.char_id, w.char_id) \
               ORDER BY p.name ASC"

        data = self.db.query(sql)

        blob = ""
        current_main_name = ""
        for want in data:
            if want.name != current_main_name:
                blob += "\n<header2>%s</header2>\n" % want.name
                current_main_name = want.name

            blob += want.want + "\n"

        return ChatBlob("Wants List (%d)" % len(data), blob)
