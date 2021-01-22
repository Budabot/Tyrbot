from core.chat_blob import ChatBlob
from core.command_param_types import Const, Any
from core.decorators import instance, command

from functools import partial


@instance()
class MessageHubController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.getresp = partial(registry.get_instance("translation_service").get_response, "module/system")

    def start(self):
        pass

    @command(command="messagehub", params=[], access_level="admin",
             description="Show the current message hub subscriptions")
    def messagehub_cmd(self, request):
        blob = self.getresp("messagehub_info") + "\n"
        subscriptions = self.message_hub_service.hub
        for destination, obj in subscriptions.items():
            edit_subs_link = self.text.make_chatcmd(destination, "/tell <myname> messagehub edit %s" % destination)
            blob += "\n%s\n" % edit_subs_link
            for source in obj.sources:
                blob +=  " └ %s\n" % source

        return ChatBlob(self.getresp("messagehub_title", {"count": len(subscriptions)}), blob)

    @command(command="messagehub", params=[Const("edit"), Any("destination")], access_level="admin",
             description="Edit subscriptions for a destination")
    def messagehub_edit_cmd(self, request, _, destination):
        obj = self.message_hub_service.hub[destination]
        if not obj:
            return self.getresp("destination_not_exist", {"destination": destination})

        blob = ""
        count = 0
        for source in self.message_hub_service.sources:
            if source in obj.invalid_sources:
                continue

            sub_link = self.text.make_chatcmd("Subscribe", "/tell <myname> messagehub subscribe %s %s" % (destination, source))
            unsub_link = self.text.make_chatcmd("Unsubscribe", "/tell <myname> messagehub unsubscribe %s %s" % (destination, source))
            status = ""
            if source in obj.sources:
                count += 1
                status = "<green>%s</green>" % self.getresp("subscribed")
            blob += "%s [%s] [%s] %s\n\n" % (source, sub_link, unsub_link, status)

        return ChatBlob(self.getresp("messagehub_edit_title", {"destination": destination.capitalize(), "count": count}), blob)

    @command(command="messagehub", params=[Const("subscribe"), Any("destination"), Any("source")], access_level="admin",
             description="Subscribe a destination to a source")
    def messagehub_subscribe_cmd(self, request, _, destination, source):
        obj = self.message_hub_service.hub[destination]
        if not obj:
            return self.getresp("module/system", "destination_not_exist", {"destination": destination})

        if source in obj.sources:
            return self.getresp("messagehub_already_subscribed", {"destination": destination, "source": source})

        if source in obj.invalid_sources:
            return self.getresp("messagehub_invalid_subscription", {"destination": destination, "source": source})

        self.message_hub_service.subscribe_to_source(destination, source)
        return self.getresp("messagehub_subscribe_success", {"destination": destination, "source": source})


    @command(command="messagehub", params=[Const("unsubscribe"), Any("destination"), Any("source")], access_level="admin",
             description="Unsubscribe a destination to a source")
    def messagehub_unsubscribe_cmd(self, request, _, destination, source):
        obj = self.message_hub_service.hub[destination]
        if not obj:
            return self.getresp("module/system", "destination_not_exist", {"destination": destination})

        if source not in obj.sources:
            return self.getresp("messagehub_not_subscribed", {"destination": destination, "source": source})

        self.message_hub_service.unsubscribe_from_source(destination, source)
        return self.getresp("messagehub_unsubscribe_success", {"destination": destination, "source": source})
