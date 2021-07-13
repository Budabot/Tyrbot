from core.decorators import instance
from modules.core.private_channel.private_channel_controller import PrivateChannelController


@instance("private_channel_controller", override=True)
class RaidInstancePrivateChannelController(PrivateChannelController):
    def get_conn(self, conn):
        if conn:
            return conn
        else:
            return self.bot.get_primary_conn()

    def handle_incoming_relay_message(self, ctx):
        for _id, conn in self.get_conns(lambda x: x.is_main):
            self.bot.send_private_channel_message(ctx.formatted_message, conn=conn)
