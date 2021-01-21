from core.command_param_types import Any, Const, Time
from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.dict_object import DictObject
import random
import time
import re


@instance()
class RaffleController:
    MESSAGE_SOURCE = "raffle"

    def __init__(self):
        self.raffle = None

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.job_scheduler = registry.get_instance("job_scheduler")
        self.message_hub_service = registry.get_instance("message_hub_service")

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    @command(command="raffle", params=[], access_level="all",
             description="Show current raffle")
    def raffle_show_cmd(self, request):
        if not self.raffle:
            return "There is no active raffle."

        t = int(time.time())

        return self.get_raffle_display(t)

    @command(command="raffle", params=[Const("cancel")], access_level="all",
             description="Cancel the raffle")
    def raffle_cancel_cmd(self, request, _):
        if not self.raffle:
            return "There is no active raffle."

        self.job_scheduler.cancel_job(self.raffle.scheduled_job_id)
        self.raffle = None

        msg = "The raffle has been cancelled."
        self.spam_raffle_channels(msg)

    @command(command="raffle", params=[Const("join")], access_level="all",
             description="Join the raffle")
    def raffle_join_cmd(self, request, _):
        if not self.raffle:
            return "There is no active raffle."

        if request.sender.name in self.raffle.members:
            return "You are already in the raffle."

        self.raffle.members.append(request.sender.name)
        return "You have joined the raffle."

    @command(command="raffle", params=[Const("leave")], access_level="all",
             description="Leave the raffle")
    def raffle_leave_cmd(self, request, _):
        if not self.raffle:
            return "There is no active raffle."

        if request.sender.name not in self.raffle.members:
            return "You are not in the raffle."

        self.raffle.members.remove(request.sender.name)
        return "You have been removed from the raffle."

    @command(command="raffle", params=[Const("start", is_optional=True), Any("item"), Time("duration", is_optional=True)], access_level="all",
             description="Raffle an item")
    def raffle_start_cmd(self, request, _, item, duration):
        duration = duration or 180  # 3 minutes

        if self.raffle:
            return "There is already a raffle in progress."

        t = int(time.time())
        finished_at = t + duration

        self.raffle = DictObject({
            "owner": request.sender,
            "item": self.get_item_name(item),
            "started_at": t,
            "duration": duration,
            "finished_at": finished_at,
            "members": [],
            "reply": request.reply,
            "scheduled_job_id": self.job_scheduler.scheduled_job(self.alert_raffle_status, self.get_next_alert_time(t, finished_at))
        })

        chatblob = self.get_raffle_display(t)

        self.spam_raffle_channels(chatblob)

    def get_raffle_display(self, t):
        time_left_str = self.util.time_to_readable(self.raffle.finished_at - t)

        blob = "Item: <highlight>%s</highlight>\n" % self.raffle.item
        blob += "By: <highlight>%s</highlight>\n" % self.raffle.owner.name
        blob += "Time left: <highlight>%s</highlight>\n" % time_left_str
        blob += "Members (%d): <highlight>%s</highlight>\n\n" % (len(self.raffle.members), ", ".join(self.raffle.members))
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
                self.spam_raffle_channels("Congratulations <highlight>%s</highlight>! You have won the raffle for <highlight>%s</highlight>." % (self.get_raffle_winner(), self.raffle.item))
            self.raffle = None
        else:
            self.spam_raffle_channels(self.get_raffle_display(t))
            self.raffle.scheduled_job_id = self.job_scheduler.scheduled_job(self.alert_raffle_status, self.get_next_alert_time(t, self.raffle.finished_at))

    def spam_raffle_channels(self, msg):
        self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, msg)

    def get_raffle_winner(self):
        return random.choice(self.raffle.members)

    def get_next_alert_time(self, current_time, finished_at):
        time_left = finished_at - current_time
        if time_left > 60:
            return current_time + 60
        else:
            return current_time + time_left
