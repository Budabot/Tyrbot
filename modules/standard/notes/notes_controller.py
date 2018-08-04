from core.command_param_types import Any, Int, Const, Options
from core.decorators import instance, command
from core.chat_blob import ChatBlob
import time


@instance()
class NotesController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.alts_service = registry.get_instance("alts_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS notes ("
                     "id INT PRIMARY KEY AUTO_INCREMENT, "
                     "char_id INT NOT NULL, "
                     "note TEXT NOT NULL,"
                     "created_at INT NOT NULL);")

    @command(command="notes", params=[], access_level="all",
             description="Show your notes")
    def notes_list_cmd(self, channel, sender, reply, args):
        alts = self.alts_service.get_alts(sender.char_id)

        cnt = 0
        blob = ""
        for alt in alts:
            data = self.db.query("SELECT * FROM notes WHERE char_id = ? ORDER BY created_at DESC", [alt.char_id])
            alt_cnt = len(data)
            cnt += alt_cnt

            if alt_cnt:
                blob += "\n<header2>%s<end>\n" % alt.name
                for row in data:
                    blob += "%s %s\n\n" % (row.note, self.text.make_chatcmd("Remove", "/tell <myname> notes remove %d" % row.id))

        reply(ChatBlob("Notes for %s (%d)" % (alts[0].name, cnt), blob))

    @command(command="notes", params=[Const("add"), Any("note")], access_level="all",
             description="Add a note")
    def notes_add_cmd(self, channel, sender, reply, args):
        note = args[1]

        self.db.exec("INSERT INTO notes (char_id, note, created_at) VALUES (?, ?, ?)", [sender.char_id, note, int(time.time())])

        reply("Note added successfully.")

    @command(command="notes", params=[Options(["rem", "remove"]), Int("note_id")], access_level="all",
             description="Remove a note")
    def notes_remove_cmd(self, channel, sender, reply, args):
        note_id = args[1]

        note = self.db.query_single("SELECT n.*, p.name FROM notes n LEFT JOIN player P ON n.char_id = p.char_id WHERE n.id = ?", [note_id])

        if not note:
            reply("Could not find note with ID <highlight>%d<end>." % note_id)
            return

        if self.alts_service.get_main(sender.char_id).char_id != self.alts_service.get_main(note.char_id).char_id:
            reply("You must be a confirmed alt of <highlight>%s<end> to remove this note." % note.name)
            return

        self.db.exec("DELETE FROM notes WHERE id = ?", [note_id])

        reply("Note with ID <highlight>%d<end> deleted successfully." % note_id)
