from core.decorators import instance, command, event
from core.command_param_types import Const, Any, Time, Int
from core.alts.alts_manager import AltsManager
from core.chat_blob import ChatBlob
from core.private_channel_manager import PrivateChannelManager
import os
import time


@instance()
class PollController:
    POLL_STATUS_CREATED = "created"
    POLL_STATUS_RUNNING = "running"
    POLL_STATUS_FINISHED = "finished"

    DEFAULT_DURATION = 86400

    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.pork_manager = registry.get_instance("pork_manager")

    def start(self):
        pass
        # self.db.load_sql_file("online.sql", os.path.dirname(__file__))
        # create scheduled job for active polls

    @command(command="poll", params=[], access_level="all",
             description="List the polls")
    def poll_list_cmd(self, channel, sender, reply, args):
        pass

    @command(command="poll", params=[Const("add"), Any("questions_and_choices")], access_level="all",
             description="Add a poll", extended_description="This command expects the poll question, followed by each of the choices, all separated by the pipe ('|') symbol")
    def poll_add_cmd(self, channel, sender, reply, args):
        pass

    @command(command="poll", params=[Int("poll_id"), Const("duration"), Time("poll_duration")], access_level="all",
             description="Set duration of a poll")
    def poll_set_duration_cmd(self, channel, sender, reply, args):
        pass

    @command(command="poll", params=[Int("poll_id"), Const("start")], access_level="all",
             description="List of polls on the bot")
    def poll_start_cmd(self, channel, sender, reply, args):
        pass

    @command(command="poll", params=[Int("poll_id"), Const("vote"), Int("choice_id")], access_level="all",
             description="Vote on a poll")
    def poll_vote_cmd(self, channel, sender, reply, args):
        pass

    @command(command="poll", params=[Int("poll_id"), Const("remvote")], access_level="all",
             description="Remove your vote on a poll")
    def poll_remvote_cmd(self, channel, sender, reply, args):
        pass

    def get_poll(self, poll_id):
        poll = self.db.query_single("SELECT * FROM poll WHERE id = ?", [poll_id])
        if poll:
            poll.questions = self.db.query("SELECT * FROM poll_choices WHERE poll_id = ?", [poll_id])
        else:
            return None

    def add_poll(self, question, choices):
        t = int(time.time())
        self.db.exec("INSERT INTO poll (question, status, duration, created_at, finished_at) VALUES (?, ?, ?, ?, ?)",
                     [question, self.POLL_STATUS_CREATED, self.DEFAULT_DURATION, t, t + self.DEFAULT_DURATION])

        poll_id = self.db.last_insert_id()

        for choice in choices:
            self.db.exec("INSERT INTO poll_choices (poll_id, choice) VALUES (?, ?)", [choice])

        return poll_id
