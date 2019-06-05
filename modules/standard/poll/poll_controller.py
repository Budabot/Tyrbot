import time

from core.chat_blob import ChatBlob
from core.command_param_types import Const, Any, Int
from core.decorators import instance, command, event
from modules.core.org_members.org_member_controller import OrgMemberController


@instance()
class PollController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")
        self.job_scheduler = registry.get_instance("job_scheduler")
        self.pork_service = registry.get_instance("pork_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.alts_service = registry.get_instance("alts_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS poll (id INT PRIMARY KEY AUTO_INCREMENT, question VARCHAR(1024) NOT NULL, duration INT NOT NULL, min_access_level VARCHAR(20) NOT NULL, char_id INT NOT NULL, created_at INT NOT NULL, finished_at INT NOT NULL, is_finished SMALLINT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS poll_choice (id INT PRIMARY KEY AUTO_INCREMENT, poll_id INT NOT NULL, choice VARCHAR(1024))")
        self.db.exec("CREATE TABLE IF NOT EXISTS poll_vote (poll_id INT NOT NULL, choice_id INT NOT NULL, char_id INT NOT NULL)")

        self.command_alias_service.add_alias("vote", "poll")

    @command(command="poll", params=[], access_level="all",
             description="List the polls")
    def poll_list_cmd(self, request):
        blob = ""
        t = int(time.time())
        state = ""
        polls = self.get_polls()
        for poll in polls:
            if poll.finished_at > t and state != "running":
                state = "running"
                blob += "\n<header2>Running<end>\n"
            elif poll.finished_at <= t and state != "finished":
                state = "finished"
                blob += "\n<header2>Finished<end>\n"

            if state == "running":
                time_string = self.util.time_to_readable(poll.finished_at - t) + " left"
            else:
                time_string = self.util.time_to_readable(t - poll.finished_at) + " ago"

            blob += "%d. %s (%d) - %s\n" % (poll.id, self.text.make_chatcmd(poll.question, "/tell <myname> poll %d" % poll.id), poll.total_cnt, time_string)

        return ChatBlob("Polls (%d)" % len(polls), blob)

    @command(command="poll", params=[Int("poll_id")], access_level="all",
             description="View a poll")
    def poll_view_cmd(self, request, poll_id):
        poll = self.get_poll(poll_id)

        if not poll:
            return "Could not find poll with ID <highlight>%d<end>." % poll_id

        return self.show_poll_details_blob(poll)

    @command(command="poll", params=[Const("add"), Any("duration|poll_question|option1|option2|...")], access_level="all",
             description="Add a poll")
    def poll_add_cmd(self, request, _, options):
        options = options.split("|")

        if len(options) < 4:
            return "You must enter a duration, a poll question, and at least two choices."

        time_str = options.pop(0).strip()
        question = options.pop(0).strip()
        choices = options

        duration = self.util.parse_time(time_str)
        if duration == 0:
            return "You must enter a valid duration."

        poll_id = self.add_poll(question, request.sender.char_id, duration)
        for choice in choices:
            self.add_poll_choice(poll_id, choice.strip())

        self.create_scheduled_job(self.get_poll(poll_id))

        return self.show_poll_details_blob(self.get_poll(poll_id))

    @command(command="poll", params=[Int("poll_id"), Const("vote"), Int("choice_id")], access_level="all",
             description="Vote on a poll")
    def poll_vote_cmd(self, request, poll_id, _, choice_id):
        poll = self.get_poll(poll_id)
        if not poll:
            return "Could not find poll with id <highlight>%d<end>." % poll_id

        choice = self.db.query_single("SELECT * FROM poll_choice WHERE poll_id = ? AND id = ?", [poll_id, choice_id])
        if not choice:
            return "Could not find choice with id <highlight>%d<end> for poll id <highlight>%d<end>." % (choice_id, poll_id)

        main = self.alts_service.get_main(request.sender.char_id)

        # retrieve pork info
        self.pork_service.get_character_info(main.char_id)

        cnt = self.db.exec("DELETE FROM poll_vote WHERE poll_id = ? AND (char_id = ? OR char_id = ?)", [poll_id, main.char_id, request.sender.char_id])
        self.db.exec("INSERT INTO poll_vote (poll_id, choice_id, char_id) VALUES (?, ?, ?)", [poll_id, choice_id, main.char_id])

        if cnt > 0:
            return "Your vote has been updated."
        else:
            return "Your vote has been saved."

    @command(command="poll", params=[Int("poll_id"), Const("remvote")], access_level="all",
             description="Remove your vote on a poll")
    def poll_remvote_cmd(self, request, poll_id, _):
        poll = self.get_poll(poll_id)
        if not poll:
            return "Could not find poll with id <highlight>%d<end>." % poll_id

        main = self.alts_service.get_main(request.sender.char_id)

        cnt = self.db.exec("DELETE FROM poll_vote WHERE poll_id = ? AND (char_id = ? OR char_id = ?)", [poll_id, main.char_id, request.sender.char_id])
        if cnt > 0:
            return "Your vote has been removed."
        else:
            return "You have not voted for that choice."

    @event(event_type="connect", description="Check for finished polls", is_hidden=True)
    def connect_event(self, event_type, event_data):
        self.check_for_finished_polls()
        self.create_scheduled_jobs_for_polls()

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGON_EVENT, description="Send active polls to org members logging on")
    def org_member_logon_event(self, event_type, event_data):
        if self.bot.is_ready():
            data = self.db.query("SELECT * FROM poll WHERE is_finished != 1 AND "
                                 "id NOT IN (SELECT poll_id FROM poll_vote WHERE char_id = ?) "
                                 "ORDER BY finished_at ASC, id ASC", [event_data.char_id])
            if data:
                row = data[0]
                self.bot.send_private_message(event_data.char_id, self.show_poll_details_blob(row))

    def create_scheduled_jobs_for_polls(self):
        data = self.db.query("SELECT * FROM poll WHERE is_finished != 1")

        for row in data:
            self.create_scheduled_job(row)

    def check_for_finished_polls(self):
        data = self.db.query("SELECT * FROM poll WHERE is_finished = 0 AND finished_at <= ?", [int(time.time())])

        for row in data:
            self.end_poll(row)

    def show_poll_details_blob(self, poll):
        blob = ""
        blob += "Duration: <highlight>%s<end>\n" % self.util.time_to_readable(poll.duration)
        blob += "Created: <highlight>%s<end>\n" % self.util.format_datetime(poll.created_at)
        blob += "Finished: <highlight>%s<end>\n" % self.util.format_datetime(poll.finished_at)

        blob += "\n<header2>Choices<end>\n"
        idx = 1
        for choice in self.get_choices(poll.id):
            blob += "%d. %s (%d)\n" % (idx, self.text.make_chatcmd(choice.choice, "/tell <myname> poll %d vote %d" % (poll.id, choice.id)), choice.cnt)
            for vote in self.get_votes(choice.id):
                blob += "<tab>%s\n" % self.text.format_char_info(vote)
            idx += 1

        return ChatBlob("Poll ID %d: %s" % (poll.id, poll.question), blob)

    def get_polls(self):
        return self.db.query("SELECT p.*, (SELECT COUNT(1) FROM poll_vote v WHERE v.poll_id = p.id) AS total_cnt FROM poll p ORDER BY finished_at DESC")

    def get_poll(self, poll_id):
        return self.db.query_single("SELECT * FROM poll WHERE id = ?", [poll_id])

    def get_choices(self, poll_id):
        return self.db.query("SELECT c.id, c.choice, COUNT(v.char_id) AS cnt FROM poll_choice c "
                             "LEFT JOIN poll_vote v ON c.id = v.choice_id "
                             "WHERE c.poll_id = ? "
                             "GROUP BY c.id, c.choice "
                             "ORDER BY c.id ASC", [poll_id])

    def get_votes(self, choice_id):
        return self.db.query("SELECT p.* FROM poll_vote v "
                             "LEFT JOIN player p ON v.char_id = p.char_id "
                             "WHERE v.choice_id = ?", [choice_id])

    def add_poll(self, question, char_id, duration, min_access_level="all"):
        t = int(time.time())
        self.db.exec("INSERT INTO poll (question, duration, min_access_level, char_id, created_at, finished_at, is_finished) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     [question, duration, min_access_level, char_id, t, t + duration, 0])

        return self.db.last_insert_id()

    def add_poll_choice(self, poll_id, choice):
        self.db.exec("INSERT INTO poll_choice (poll_id, choice) VALUES (?, ?)", [poll_id, choice])

        return self.db.last_insert_id()

    def create_scheduled_job(self, poll):
        self.job_scheduler.scheduled_job(self.show_results, poll.finished_at, poll.id)

    def show_results(self, t, poll_id):
        self.end_poll(self.get_poll(poll_id))

    def end_poll(self, poll):
        self.bot.send_private_message(poll.char_id, "Your poll <highlight>%d. %s<end> has finished." % (poll.id, poll.question))
        self.db.exec("UPDATE poll SET is_finished = 1 WHERE id = ?", [poll.id])
