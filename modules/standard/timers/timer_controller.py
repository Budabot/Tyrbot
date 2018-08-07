from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any, Const, Time
import time


@instance()
class TimerController:
    def __init__(self):
        self.jobs = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.job_scheduler = registry.get_instance("job_scheduler")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS timer (name VARCHAR(255) NOT NULL, char_id INT NOT NULL, channel VARCHAR(10) NOT NULL, "
                     "duration INT NOT NULL, created_at INT NOT NULL, finished_at INT NOT NULL)")

        # add scheduled jobs for timers that are already running
        data = self.db.query("SELECT * FROM timer")
        for row in data:
            self.jobs[row.name] = self.job_scheduler.scheduled_job(self.timer_finished, row.finished_at, row.name)

    @command(command="timers", params=[], access_level="all",
             description="Show current timers", aliases=["timer"])
    def timers_list_cmd(self, request):
        t = int(time.time())
        data = self.db.query("SELECT t.*, p.name AS char_name FROM timer t LEFT JOIN player p ON t.char_id = p.char_id ORDER BY t.finished_at ASC")
        blob = ""
        for timer in data:
            blob += "<pagebreak>Name: <highlight>%s<end>\n" % timer.name
            blob += "Time left: <highlight>%s<end>\n" % self.util.time_to_readable(timer.created_at + timer.duration - t, max_levels=None)
            blob += "Owner: <highlight>%s<end>\n\n" % timer.char_name

        return ChatBlob("Timers (%d)" % len(data), blob)

    @command(command="timers", params=[Const("add", is_optional=True), Time("time"), Any("name", is_optional=True)], access_level="all",
             description="Add a timer")
    def timers_add_cmd(self, request, _, duration, timer_name):
        timer_name = timer_name or self.get_timer_name(request.sender.name)

        if self.get_timer(timer_name):
            return "A timer named <highlight>%s<end> is already running." % timer_name

        self.add_timer(timer_name, request.sender.char_id, request.channel, duration)

        return "Timer <highlight>%s<end> has been set for %s." % (timer_name, self.util.time_to_readable(duration, max_levels=None))

    def get_timer_name(self, base_name):
        # attempt base name first
        name = base_name

        idx = 1
        while self.get_timer(name):
            idx += 1
            name = base_name + str(idx)

        return name

    def get_timer(self, name):
        return self.db.query_single("SELECT * FROM timer WHERE name LIKE ?", [name])

    def add_timer(self, timer_name, char_id, channel, duration):
        t = int(time.time())

        self.jobs[timer_name] = self.job_scheduler.scheduled_job(self.timer_finished, t + duration, timer_name)

        self.db.exec("INSERT INTO timer (name, char_id, channel, duration, created_at, finished_at) VALUES (?, ?, ?, ?, ?, ?)",
                     [timer_name, char_id, channel, duration, t, t + duration])

    def remove_timer(self, timer_name):
        self.db.exec("DELETE FROM timer WHERE name LIKE ?", [timer_name])

        del self.jobs[timer_name]

    def timer_finished(self, t, timer_name):
        timer = self.get_timer(timer_name)
        msg = "Timer <highlight>%s<end> has gone off." % timer_name

        if timer.channel == "org":
            self.bot.send_org_message(msg)
        elif timer.channel == "priv":
            self.bot.send_private_channel_message(msg)
        else:
            self.bot.send_private_message(timer.char_id, msg)

        self.remove_timer(timer_name)
