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

    @command(command="messagehub", params=[], access_level="admin",
             description="Show the current message hub subscriptions")
    def messagehub_cmd(self, request):
        blob = "Destinations are listed below, along with the sources they are subscribed to.\n"
        subscriptions = self.message_hub_service.hub
        for destination, obj in subscriptions.items():
            edit_subs_link = self.text.make_tellcmd(destination, "messagehub edit %s" % destination)
            blob += "\n%s\n" % edit_subs_link
            for source in obj.sources:
                blob += " └ %s\n" % source

        return ChatBlob(f"Message Hub Subscriptions ({len(subscriptions)})", blob)

    @command(command="messagehub", params=[Const("edit"), Any("destination")], access_level="admin",
             description="Edit subscriptions for a destination")
    def messagehub_edit_cmd(self, request, _, destination):
        obj = self.message_hub_service.hub[destination]
        if not obj:
            return f"Destination <highlight>{destination}</highlight> does not exist."

        blob = ""
        count = 0
        for source in self.message_hub_service.sources:
            if source in obj.invalid_sources:
                continue

            sub_link = self.text.make_tellcmd("Subscribe", "messagehub subscribe %s %s" % (destination, source))
            unsub_link = self.text.make_tellcmd("Unsubscribe", "messagehub unsubscribe %s %s" % (destination, source))
            status = ""
            if source in obj.sources:
                count += 1
                status = "<green>Subscribed</green>"
            blob += "%s [%s] [%s] %s\n\n" % (source, sub_link, unsub_link, status)

        return ChatBlob(f"{destination.capitalize()} Subscriptions ({count})", blob)

    @command(command="messagehub", params=[Const("subscribe"), Any("destination"), Any("source")], access_level="admin",
             description="Subscribe a destination to a source")
    def messagehub_subscribe_cmd(self, request, _, destination, source):
        obj = self.message_hub_service.hub[destination]
        if not obj:
            return f"Destination <highlight>{destination}</highlight> does not exist."

        if source in obj.sources:
            return f"Destination <highlight>{destination}</highlight> is already subscribed to source <highlight>{source}</highlight>."

        if source in obj.invalid_sources:
            return f"Destination <highlight>{destination}</highlight> cannot be subscribed to source <highlight>{source}</highlight>."

        self.message_hub_service.subscribe_to_source(destination, source)
        return f"Destination <highlight>{destination}</highlight> has been subscribed to source <highlight>{source}</highlight> successfully."

    @command(command="messagehub", params=[Const("unsubscribe"), Any("destination"), Any("source")], access_level="admin",
             description="Unsubscribe a destination to a source")
    def messagehub_unsubscribe_cmd(self, request, _, destination, source):
        obj = self.message_hub_service.hub[destination]
        if not obj:
            return f"Destination <highlight>{destination}</highlight> does not exist."

        if source not in obj.sources:
            return f"Destination <highlight>{destination}</highlight> is not subscribed to source <highlight>{source}</highlight>."

        self.message_hub_service.unsubscribe_from_source(destination, source)
        return f"Destination <highlight>{destination}</highlight> has been unsubscribed from source <highlight>{source}</highlight> successfully."
