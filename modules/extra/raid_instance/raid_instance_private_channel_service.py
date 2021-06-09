from core.aochat import server_packets
from core.conn import Conn
from core.decorators import instance
from core.dict_object import DictObject
from core.private_channel_service import PrivateChannelService


@instance("private_channel_service", override=True)
class RaidInstancePrivateChannelService(PrivateChannelService):
    def handle_private_channel_message(self, conn: Conn, packet: server_packets.PrivateChannelMessage):
        char_name = self.character_service.get_char_name(packet.char_id)
        if packet.private_channel_id != conn.char_id:
            # channel_name = self.character_service.get_char_name(packet.private_channel_id)
            # self.logger.log_chat(conn, f"Private Channel({channel_name})", char_name, packet.message)
            pass
        else:
            self.logger.log_chat(conn, "Private Channel", char_name, packet.message)

            if not conn.is_main or conn.char_id == packet.char_id:
                return

            if not self.handle_private_channel_command(conn, packet):
                message = packet.message
                self.event_service.fire_event(self.PRIVATE_CHANNEL_MESSAGE_EVENT, DictObject({"char_id": packet.char_id,
                                                                                              "name": char_name,
                                                                                              "message": message,
                                                                                              "conn": conn}))

                if message.startswith("@") and len(message) > 1:
                    message = "[%s] %s: %s" % (conn.id, char_name, message[1:])
                    for _id, conn in self.bot.get_conns(lambda x: x.is_main and x != conn):
                        self.bot.send_private_channel_message(message, conn=conn)
