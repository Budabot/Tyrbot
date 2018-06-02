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
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")

    def start(self):
        pass
        # create scheduled job for active polls
        # add min access level for polls

    @command(command="poll", params=[], access_level="all",
             description="List the polls")
    def poll_list_cmd(self, channel, sender, reply, args):
        blob = ""
        t = int(time.time())
        state = ""
        polls = self.get_polls()
        for poll in polls:
            if poll.finished_at > t and state != "running":
                state = "running"
                blob += "\n<header2>Running<end>\n\n"
            elif poll.finished_at <= t and state != "finished":
                state = "finished"
                blob += "\n<header2>Finished<end>\n\n"

            time_string = self.util.time_to_readable(poll.finished_at - t) + " left" if state == "running" else self.util.time_to_readable(t - poll.finished_at) + " ago"

            blob += "%s - %s\n" % (self.text.make_chatcmd(poll.question, "/tell <myname> poll %d" % poll.id), time_string)

        reply(ChatBlob("Polls (%d)" % len(polls), blob))

    @command(command="poll", params=[Int("poll_id")], access_level="all",
             description="Add a poll", extended_description="View information for a poll")
    def poll_view_cmd(self, channel, sender, reply, args):
        poll_id = args[0]
        poll = self.get_poll(poll_id)

        if not poll:
            reply("Could not find poll with ID <highlight>%d<end>." % poll_id)
            return

        reply(self.show_poll_details_blob(poll))

    @command(command="poll", params=[Const("add"), Any("question")], access_level="all",
             description="Add a poll")
    def poll_add_cmd(self, channel, sender, reply, args):
        question = args[1]
        poll_id = self.add_poll(question, sender.char_id)

        reply(self.show_poll_details_blob(self.get_poll(poll_id)))

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

    def show_poll_details_blob(self, poll):
        blob = "Status: <highlight>%s<end>\n" % poll.status
        blob += "Duration: <highlight>%s<end>\n" % self.util.time_to_readable(poll.duration)
        blob += "Created: <highlight>%s<end>\n" % poll.created_at
        if poll.finished_at:
            blob += "Finished: <highlight>%s<end>\n" % poll.finished_at

        blob += "\n<header2>Choices<end>\n\n"
        idx = 1
        for choice in poll.choices:
            blob += "%d. %s\n" % (idx, choice)
            idx += 1

        return ChatBlob("Poll ID %d: %s" % (poll.id, poll.question), blob)

    def get_polls(self):
        return self.db.query("SELECT * FROM poll ORDER BY finished_at DESC")

    def get_poll(self, poll_id):
        poll = self.db.query_single("SELECT * FROM poll WHERE id = ?", [poll_id])
        if poll:
            poll.choices = self.db.query("SELECT * FROM poll_choice WHERE poll_id = ?", [poll_id])

        return poll

    def add_poll(self, question, char_id):
        t = int(time.time())
        self.db.exec("INSERT INTO poll (question, status, duration, min_access_level, char_id, created_at, finished_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     [question, self.POLL_STATUS_CREATED, self.DEFAULT_DURATION, "all", char_id, t, t + self.DEFAULT_DURATION])

        return self.db.last_insert_id()

    def add_poll_choice(self, poll_id, choice):
        self.db.exec("INSERT INTO poll_choice (poll_id, choice) VALUES (?, ?)", [poll_id, choice])

        return self.db.last_insert_id()
