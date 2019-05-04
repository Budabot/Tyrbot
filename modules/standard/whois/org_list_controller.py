from core.buddy_service import BuddyService
from core.chat_blob import ChatBlob
from core.command_param_types import Int, Any, Character
from core.decorators import instance, command, event
from core.dict_object import DictObject


@instance()
class OrgListController:
    ORGLIST_BUDDY_TYPE = "orglist"

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

    @command(command="orglist", params=[Int("org_id")], access_level="all",
             description="Show online status of characters in an org")
    def orglist_cmd(self, request, org_id):
        self.start_orglist_lookup(request.reply, org_id)

    @command(command="orglist", params=[Any("character|org_name|org_id")], access_level="all",
             description="Show online status of characters in an org")
    def orglist_character_cmd(self, request, search):
        if search.isdigit():
            org_id = int(search)
        else:
            orgs = self.pork_service.find_orgs(search)
            num_orgs = len(orgs)
            if num_orgs == 0:
                char_info = self.pork_service.get_character_info(search)
                if char_info:
                    if not char_info.org_id:
                        return "<highlight>%s<end> does not appear to belong to an org." % search.capitalize()
                    else:
                        org_id = char_info.org_id
                else:
                    return "Could not find character or org <highlight>%s<end>." % search
            elif num_orgs == 1:
                org_id = orgs[0].org_id
            else:
                blob = ""
                for org in orgs:
                    blob += self.text.make_chatcmd("%s (%d)" % (org.org_name, org.org_id), "/tell <myname> orglist %d" % org.org_id) + "\n"
                return ChatBlob("Org List (%d)" % num_orgs, blob)

        self.start_orglist_lookup(request.reply, org_id)

    def start_orglist_lookup(self, reply, org_id):
        if self.orglist:
            reply("There is an orglist already in progress.")
            return

        reply("Downloading org roster for org id %d..." % org_id)

        self.orglist = self.org_pork_service.get_org_info(org_id)

        if not self.orglist:
            reply("Could not find org with ID <highlight>%d<end>." % org_id)
            return

        self.orglist.reply = reply
        self.orglist.waiting_org_members = {}
        self.orglist.finished_org_members = {}

        reply("Checking online status for %d members of <highlight>%s<end>..." % (len(self.orglist.org_members), self.orglist.org_info.name))

        # process all name lookups
        while self.bot.iterate():
            pass

        self.iterate_org_members()

        self.check_for_orglist_end()

    @event(event_type=BuddyService.BUDDY_LOGON_EVENT, description="Detect online buddies for orglist command")
    def buddy_logon_event(self, event_type, event_data):
        if self.orglist and event_data.char_id in self.orglist.waiting_org_members:
            self.update_online_status(event_data.char_id, True)
            self.buddy_service.remove_buddy(event_data.char_id, self.ORGLIST_BUDDY_TYPE)
            self.check_for_orglist_end()

    @event(event_type=BuddyService.BUDDY_LOGOFF_EVENT, description="Detect offline buddies for orglist command")
    def buddy_logoff_event(self, event_type, event_data):
        if self.orglist and event_data.char_id in self.orglist.waiting_org_members:
            self.update_online_status(event_data.char_id, False)
            self.buddy_service.remove_buddy(event_data.char_id, self.ORGLIST_BUDDY_TYPE)
            self.check_for_orglist_end()

    def update_online_status(self, char_id, status):
        self.orglist.finished_org_members[char_id] = self.orglist.waiting_org_members[char_id]
        self.orglist.finished_org_members[char_id].online = status
        del self.orglist.waiting_org_members[char_id]

    def check_for_orglist_end(self):
        if self.orglist.org_members:
            self.iterate_org_members()
            return

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

        for char_id, org_member in self.orglist.finished_org_members.items():
            if org_member.online:
                org_ranks[org_member.org_rank_name].online_members.append(org_member)
            else:
                org_ranks[org_member.org_rank_name].offline_members.append(org_member)

        blob = ""
        num_online = 0
        num_total = 0
        for rank_name, rank_info in org_ranks.items():
            rank_num_online = len(rank_info.online_members)
            rank_num_total = len(rank_info.offline_members) + rank_num_online
            blob += "<header2>%s (%d / %d)<end>\n" % (rank_name, rank_num_online, rank_num_total)
            num_online += rank_num_online
            num_total += rank_num_total
            for org_member in rank_info.online_members:
                level = org_member.level if org_member.ai_level == 0 else "%d/<green>%d<end>" % (org_member.level, org_member.ai_level)
                blob += "%s (Level <highlight>%s<end>, %s %s <highlight>%s<end>)\n" % (org_member.name, level, org_member.gender, org_member.breed, org_member.profession)
            if rank_num_total < 200:
                blob += "<font color='#555555'>" + ", ".join(map(lambda x: x.name, rank_info.offline_members)) + "<end>"
                blob += "\n"
            else:
                blob += "<font color='#555555'>Offline members ommitted for brevity<end>\n"
            blob += "\n"

        return ChatBlob("Orglist for '%s' (%d / %d)" % (self.orglist.org_info.name, num_online, num_total), blob)

    def iterate_org_members(self):
        # add org_members that we don't have online status for as buddies
        for char_id, org_member in self.orglist.org_members.copy().items():
            self.orglist.waiting_org_members[char_id] = self.orglist.org_members[char_id]
            del self.orglist.org_members[char_id]
            is_online = self.buddy_service.is_online(char_id)
            if is_online is None:
                if self.character_service.resolve_char_to_id(org_member.name):
                    self.buddy_service.add_buddy(char_id, self.ORGLIST_BUDDY_TYPE)
                else:
                    # character is inactive, set as offline
                    self.update_online_status(char_id, False)
            else:
                self.update_online_status(char_id, is_online)

            if not self.buddy_list_has_available_slots():
                break

    def buddy_list_has_available_slots(self):
        return self.buddy_service.buddy_list_size - len(self.buddy_service.buddy_list) > 5
