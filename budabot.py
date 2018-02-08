from bot import Bot
import server_packets


class Budabot(Bot):
    def run(self):
        while True:
            packet = self.read_packet()
            if packet is not None:
                if isinstance(packet, server_packets.PrivateMessage):
                    print("Got private message!")
                print(packet)
