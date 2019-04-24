import threading

from core.decorators import instance, event, timerevent, setting, command
from core.command_param_types import Const
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.setting_types import ColorSettingType
from core.text import Text
from .gridnet_worker import GridnetWorker


@instance()
class GridnetController:
    def __init__(self):
        self.dthread = None
        self.queue = []
        self.logger = Logger(__name__)
        self.worker = None

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.text: Text = registry.get_instance("text")

    def start(self):
        self.worker = GridnetWorker(self.queue, "wss://gridnet.jkbff.com/subscribe/gridnet.rk%d" % self.bot.dimension)

    @setting(name="gridnet_channel_color", value="#FFFF00", description="Color of the channel in Gridnet messages")
    def gridnet_channel_color(self):
        return ColorSettingType()

    @setting(name="gridnet_message_color", value="#FCA712", description="Color of the message content in Gridnet messages")
    def gridnet_message_color(self):
        return ColorSettingType()

    @setting(name="gridnet_sender_color", value="#00DE42", description="Color of the sender in Gridnet messages")
    def gridnet_sender_color(self):
        return ColorSettingType()

    @command(command="gridnet", params=[Const("on")], access_level="superadmin", description="Connect to Gridnet")
    def gridnet_on(self, request, _):
        self.connect()

    @command(command="gridnet", params=[Const("off")], access_level="superadmin", description="Disconnect from Gridnet")
    def gridnet_off(self, request, _):
        self.disconnect()

    @timerevent(budatime="1s", description="Relay messages from Gridnet to org and private channel")
    def handle_queue_event(self, event_type, event_data):
        while self.queue:
            obj = self.queue.pop(0)
            message = "[Gridnet] %s" % obj.payload.message\
                .replace("<channel_color>", self.gridnet_channel_color().get_font_color())\
                .replace("<message_color>", self.gridnet_message_color().get_font_color())\
                .replace("<sender_color>", self.gridnet_sender_color().get_font_color())

            self.bot.send_org_message(message, fire_outgoing_event=False)
            self.bot.send_private_channel_message(message, fire_outgoing_event=False)

    @event(event_type="connect", description="Connect to Gridnet on startup")
    def handle_connect_event(self, event_type, event_data):
        if self.bot.dimension == 6:
            self.connect()

    def connect(self):
        if self.worker.running:
            self.logger.info("Already connected to Gridnet")
            return

        self.dthread = threading.Thread(target=self.worker.run, daemon=True)
        self.dthread.start()

    def disconnect(self):
        if not self.worker.running:
            self.logger.info("Already disconnected from Gridnet")
            return

        self.logger.info("Disconnecting from Gridnet")
        self.worker.stop()