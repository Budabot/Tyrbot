import time

from core.decorators import instance, event
from core.private_channel_service import PrivateChannelService
from modules.standard.online.online_controller import OnlineController


@instance("online_controller", override=True)
class RaidInstanceOnlineController(OnlineController):
    @event(PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, "Record in database when someone joins private channel", is_hidden=True)
    def private_channel_joined_event(self, event_type, event_data):
        self.pork_service.load_character_info(event_data.char_id)
        channel_name = self.get_channel(event_data.conn)
        self.register_online_channel(channel_name)
        self.db.exec("INSERT INTO online (char_id, afk_dt, afk_reason, channel, dt) VALUES (?, ?, ?, ?, ?)",
                     [event_data.char_id, 0, "", channel_name, int(time.time())])

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Record in database when someone leaves private channel", is_hidden=True)
    def private_channel_left_event(self, event_type, event_data):
        self.db.exec("DELETE FROM online WHERE char_id = ? AND channel = ?",
                     [event_data.char_id, self.get_channel(event_data.conn)])

    def get_channel(self, conn):
        return conn.id
