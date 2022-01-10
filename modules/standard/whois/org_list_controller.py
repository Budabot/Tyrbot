import time

from core.buddy_service import BuddyService
from core.chat_blob import ChatBlob
from core.command_param_types import Int, Any, NamedFlagParameters
from core.decorators import instance, command, event
from core.dict_object import DictObject


@instance()
class OrgListController:
    ORGLIST_BUDDY_TYPE = "orglist"

    DEFAULT_OFFLINE_MEMBER_DISPLAY_THRESHOLD = 200
    SHOW_ALL_OFFLINE_MEMBERS = 10000

    def __init__(self):
        self.orglist = None
        self.governing_types = DictObject({
            "Anarchism": ["Anarchist"],
            "Monarchy": ["Monarch", "Counsil", "Follower"],
            "Feudalism": ["Lord", "Knight", "Vassal", "Peasant"],
            "Republic": ["President", "Advisor", "Veteran", "Member", "Applicant"],
            "Faction": ["Director", "Board Member", "Executive", "Member", "Applicant"],
            "Department": ["President", "General", "Squad Commander", "Unit Commander", "Unit Leader", "Unit Member", "Applicant"]
        })

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")
        self.pork_service = registry.get_instance("pork_service")
        self.org_pork_service = registry.get_instance("org_pork_service")
        self.pork_service = registry.get_instance("pork_service")
        self.buddy_service: BuddyService = registry.get_instance("buddy_service")
        self.character_service = registry.get_instance("character_service")

    @command(command="orglist", params=[Int("org_id"), NamedFlagParameters(["show_all_offline"])], access_level="all",
             description="Show online status of characters in an org")
    def orglist_cmd(self, request, org_id, flag_params):
        self.start_orglist_lookup(request.reply,
                                  org_id,
                                  self.SHOW_ALL_OFFLINE_MEMBERS if flag_params.show_all_offline else self.DEFAULT_OFFLINE_MEMBER_DISPLAY_THRESHOLD)

    @command(command="orglist", params=[Any("character|org_name|org_id"), NamedFlagParameters(["show_all_offline"])], access_level="all",
             description="Show online status of characters in an org")
    def orglist_character_cmd(self, request, search, flag_params):
        if search.isdigit():
            org_id = int(search)
        else:
            orgs = self.pork_service.find_orgs(search)
            num_orgs = len(orgs)
            if num_orgs == 0:
                char_info = self.pork_service.get_character_info(search)
                if char_info:
                    if not char_info.org_id:
                        return "<highlight>%s</highlight> does not appear to belong to an org." % search.capitalize()
                    else:
                        org_id = char_info.org_id
                else:
                    return "Could not find character or org <highlight>%s</highlight>." % search
            elif num_orgs == 1:
                org_id = orgs[0].org_id
            else:
                blob = ""
                for org in orgs:
                    blob += self.text.make_tellcmd("%s (%d)" % (org.org_name, org.org_id), "orglist %d" % org.org_id) + "\n"
                return ChatBlob("Org List (%d)" % num_orgs, blob)

        self.start_orglist_lookup(request.reply,
                                  org_id,
                                  self.SHOW_ALL_OFFLINE_MEMBERS if flag_params.show_all_offline else self.DEFAULT_OFFLINE_MEMBER_DISPLAY_THRESHOLD)

    def start_orglist_lookup(self, reply, org_id, offline_member_display_threshold):
        if self.orglist:
            elapsed = int(time.time()) - self.orglist.get("started_at", )
            reply("There is an orglist already in progress. Elapsed time: " + self.util.time_to_readable(elapsed))
            return

        reply("Downloading org roster for org id %d..." % org_id)

        self.orglist = self.org_pork_service.get_org_info(org_id)
        self.orglist.started_at = int(time.time())

        if not self.orglist:
            reply("Could not find org with ID <highlight>%d</highlight>." % org_id)
            return

        self.orglist.org_members = list(self.orglist.org_members.values())
        self.orglist.reply = reply
        self.orglist.waiting_org_members = {}
        self.orglist.finished_org_members = {}
        self.orglist.offline_member_display_threshold = offline_member_display_threshold

        reply("Checking online status for %d members of <highlight>%s</highlight>..." % (len(self.orglist.org_members), self.orglist.org_info.name))

        # process all name lookups
        while self.bot.iterate(1):
            pass

        self.check_for_orglist_end()

    @event(event_type=BuddyService.BUDDY_LOGON_EVENT, description="Detect online buddies for orglist command", is_system=True)
    def buddy_logon_event(self, event_type, event_data):
        if self.orglist and event_data.char_id in self.orglist.waiting_org_members:
            self.update_online_status(event_data.char_id, True)
            self.check_for_orglist_end()

    @event(event_type=BuddyService.BUDDY_LOGOFF_EVENT, description="Detect offline buddies for orglist command", is_system=True)
    def buddy_logoff_event(self, event_type, event_data):
        if self.orglist and event_data.char_id in self.orglist.waiting_org_members:
            self.update_online_status(event_data.char_id, False)
            self.check_for_orglist_end()

    def update_online_status(self, char_id, status):
        self.orglist.finished_org_members[char_id] = self.orglist.waiting_org_members[char_id]
        self.orglist.finished_org_members[char_id].online = status
        del self.orglist.waiting_org_members[char_id]

    def check_for_orglist_end(self):
        if self.orglist.org_members:
            self.iterate_org_members()

        if not self.orglist.waiting_org_members:
            self.orglist.reply(self.format_result())
            self.orglist = None

    def format_result(self):
        org_ranks = {}
        for rank_name in self.governing_types[self.orglist.org_info.governing_type]:
            org_ranks[rank_name] = DictObject({
                "online_members": [],
                "offline_members": []
            })

        org_ranks["Inactive"] = DictObject({
            "online_members": [],
            "offline_members": []
        })

        for char_id, org_member in self.orglist.finished_org_members.items():
            if org_member.online == 2:
                org_ranks["Inactive"].offline_members.append(org_member)
            elif org_member.online == 1:
                org_ranks[org_member.org_rank_name].online_members.append(org_member)
            else:
                org_ranks[org_member.org_rank_name].offline_members.append(org_member)

        blob = "[%s] [%s] [%s]" % (
            self.text.make_chatcmd("HTML", f"/start http://people.anarchy-online.com/org/stats/d/5/name/{self.orglist.org_info.org_id}/"),
            self.text.make_chatcmd("XML", f"/start http://people.anarchy-online.com/org/stats/d/5/name/{self.orglist.org_info.org_id}/basicstats.xml"),
            self.text.make_chatcmd("JSON", f"/start http://people.anarchy-online.com/org/stats/d/5/name/{self.orglist.org_info.org_id}/basicstats.xml?data_type=json")
        )

        if self.orglist.offline_member_display_threshold == self.DEFAULT_OFFLINE_MEMBER_DISPLAY_THRESHOLD:
            blob += "  " + self.text.make_tellcmd("Show all offline members", f"orglist {self.orglist.org_info.org_id} --show_all_offline")

        blob += "\n\n"
        num_online = 0
        num_total = 0
        for rank_name, rank_info in org_ranks.items():
            rank_num_online = len(rank_info.online_members)
            rank_num_total = len(rank_info.offline_members) + rank_num_online
            blob += "<pagebreak><header2>%s (%d / %d)</header2>\n" % (rank_name, rank_num_online, rank_num_total)
            num_online += rank_num_online
            num_total += rank_num_total
            for org_member in sorted(rank_info.online_members, key=lambda x: x.name):
                level = org_member.level if org_member.ai_level == 0 else "%d/<green>%d</green>" % (org_member.level, org_member.ai_level)
                blob += "%s (Level <highlight>%s</highlight>, %s %s <highlight>%s</highlight>)\n" % (org_member.name, level, org_member.gender, org_member.breed, org_member.profession)

            if rank_num_total < self.orglist.offline_member_display_threshold:
                blob += "<font color='#555555'>" + ", ".join(map(lambda x: x.name, sorted(rank_info.offline_members, key=lambda x: x.name))) + "</font>"
                blob += "\n"
            else:
                blob += "<font color='#555555'>Offline members omitted for brevity</font>\n"
            blob += "\n"

        return ChatBlob("Orglist for '%s' (%d / %d)" % (self.orglist.org_info.name, num_online, num_total), blob)

    def iterate_org_members(self):
        # add org_members that we don't have online status for as buddies
        while self.orglist.org_members and self.buddy_list_has_available_slots():
            org_member = self.orglist.org_members.pop()
            char_id = org_member.char_id
            self.orglist.waiting_org_members[char_id] = org_member
            is_online = self.buddy_service.is_online(char_id)
            if is_online is None:
                if self.character_service.resolve_char_to_id(org_member.name):
                    self.buddy_service.add_buddy(char_id, self.ORGLIST_BUDDY_TYPE)
                    self.buddy_service.remove_buddy(char_id, self.ORGLIST_BUDDY_TYPE)
                else:
                    # character is inactive, set as offline
                    self.update_online_status(char_id, 2)
            else:
                self.update_online_status(char_id, is_online)

    def buddy_list_has_available_slots(self):
        return self.buddy_service.buddy_list_size - self.buddy_service.get_buddy_list_size() > 0
