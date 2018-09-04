from core.command_param_types import Any, Int, Const, Options
from core.decorators import instance, command
from core.chat_blob import ChatBlob
import time


@instance()
class LinksController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS links ("
                     "id INT PRIMARY KEY AUTO_INCREMENT,"
                     "char_id INT NOT NULL,"
                     "website VARCHAR(255) NOT NULL,"
                     "comments VARCHAR(255) NOT NULL,"
                     "created_at INT NOT NULL)")

    @command(command="links", params=[], access_level="all",
             description="Show links")
    def links_list_cmd(self, request):
        data = self.db.query("SELECT l.*, p.name FROM links l LEFT JOIN player p ON l.char_id = p.char_id ORDER BY name ASC")

        blob = ""
        for row in data:
            blob += "%s <highlight>%s<end> [%s] %s" % (self.text.make_chatcmd("[Link]", "/start %s" % row.website),
                                                       row.comments,
                                                       row.name,
                                                       self.text.make_chatcmd("Remove", "/tell <myname> links remove %d" % row.id))

        return ChatBlob("Links (%d)" % len(data), blob)

    @command(command="links", params=[Const("add"), Any("website"), Any("comment")], access_level="moderator",
             description="Add a link")
    def links_add_cmd(self, request, _, website, comment):
        if not website.startswith("https://") and not website.startswith("http://"):
            return "Website must start with 'http://' or 'https://'."

        self.db.exec("INSERT INTO links (char_id, website, comments, created_at) VALUES (?, ?, ?, ?)", [request.sender.char_id, website, comment, int(time.time())])
        return "Link added successfully."

    @command(command="links", params=[Options(["rem", "remove"]), Int("link_id")], access_level="moderator",
             description="Remove a link")
    def links_remove_cmd(self, request, _, link_id):
        link = self.db.query_single("SELECT * FROM links WHERE id = ?", [link_id])
        if not link:
            return "Could not find link with ID <highlight>%d<end>." % link_id

        self.db.exec("DELETE FROM links WHERE id = ?", [link_id])
        return "Link has been deleted"
