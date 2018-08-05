from core.command_param_types import Any, Int, Const, Options, Time
from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.dict_object import DictObject
import random
import time
import re


@instance()
class RaffleController:
    def __init__(self):
        self.raffle = None

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.job_scheduler = registry.get_instance("job_scheduler")

    @command(command="raffle", params=[], access_level="all",
             description="Show current raffle")
    def raffle_show_cmd(self, channel, sender, reply, args):
        if not self.raffle:
            reply("There is no active raffle.")
            return

        t = int(time.time())

        reply(self.get_raffle_display(t))

    @command(command="raffle", params=[Const("cancel")], access_level="all",
             description="Cancel the raffle")
    def raffle_cancel_cmd(self, channel, sender, reply, args):
        if not self.raffle:
            reply("There is no active raffle.")
            return

        self.job_scheduler.cancel_job(self.raffle.scheduled_job.id)
        self.raffle = None

        msg = "The raffle has been cancelled."
        self.spam_raffle_channels(msg)

        if channel == "msg":
            reply(msg)

    @command(command="raffle", params=[Const("join")], access_level="all",
             description="Join the raffle")
    def raffle_join_cmd(self, channel, sender, reply, args):
        if not self.raffle:
            reply("There is no active raffle.")
            return

        if sender.name in self.raffle.members:
            reply("You are already in the raffle.")
            return

        self.raffle.members.append(sender.name)
        reply("You have joined the raffle.")

    @command(command="raffle", params=[Const("leave")], access_level="all",
             description="Leave the raffle")
    def raffle_leave_cmd(self, channel, sender, reply, args):
        if not self.raffle:
            reply("There is no active raffle.")
            return

        if sender.name not in self.raffle.members:
            reply("You are not in the raffle.")
            return

        self.raffle.members.remove(sender.name)
        reply("You have been removed from the raffle.")

    @command(command="raffle", params=[Const("start", is_optional=True), Any("item")], access_level="all",
             description="Raffle an item")
    def raffle_start_cmd(self, channel, sender, reply, args):
        duration = 180  # 3 minutes
        item = args[1]

        if self.raffle:
            reply("There is already a raffle in progress.")
            return

        t = int(time.time())

        self.raffle = DictObject({
            "owner": sender,
            "item": self.get_item_name(item),
            "started_at": t,
            "duration": duration,
            "finished_at": t + duration,
            "members": [],
            "reply": reply,
            "scheduled_job": self.job_scheduler.scheduled_job(self.alert_raffle_status, t + 60)
        })

        chatblob = self.get_raffle_display(t)

        self.spam_raffle_channels(chatblob)

        if channel == "msg":
            reply(chatblob)

    def get_raffle_display(self, t):
        time_left_str = self.util.time_to_readable(self.raffle.finished_at - t)

        blob = "Item: <highlight>%s<end>\n" % self.raffle.item
        blob += "By: <highlight>%s<end>\n" % self.raffle.owner.name
        blob += "Time left: <highlight>%s<end>\n" % time_left_str
        blob += "Members (%d): <highlight>%s<end>\n\n" % (len(self.raffle.members), ", ".join(self.raffle.members))
        blob += "Click %s to join the raffle!\n\n" % self.text.make_chatcmd("here", "/tell <myname> raffle join")
        blob += "Click %s if you wish to leave the raffle." % self.text.make_chatcmd("here", "/tell <myname> raffle leave")

        return ChatBlob("Raffle for %s! (ends in %s)" % (self.raffle.item, time_left_str), blob)

    def get_item_name(self, item):
        m = re.match(r"<a href=\"itemref://\d+/\d+/\d+\">(.+)</a>", item)
        if m:
            return m.group(1)
        else:
            return item

    def alert_raffle_status(self, t):
        if not self.raffle:
            pass

        if t >= self.raffle.finished_at:
            if len(self.raffle.members) == 0:
                self.spam_raffle_channels("The raffle has ended and there is no winner because no one entered the raffle.")
            else:
                self.spam_raffle_channels("Congrations <highlight>%s<end>! You have won the raffle for <highlight>%s<end>." % (self.get_raffle_winner(), self.raffle.item))
            self.raffle = None
        else:
            self.spam_raffle_channels(self.get_raffle_display(t))
            self.raffle.scheduled_job = self.job_scheduler.scheduled_job(self.alert_raffle_status, t + 60)

    def spam_raffle_channels(self, msg):
        self.bot.send_private_channel_message(msg)
        self.bot.send_org_message(msg)

    def get_raffle_winner(self):
        return random.choice(self.raffle.members)
