import socket
import struct
import select
from server_packets import ServerPacket, LoginOK
from client_packets import LoginRequest, LoginSelect
from crypt import generate_login_key


class Bot:
    def __init__(self):
        self.socket = None

    def connect(self, host, port):
        self.socket = socket.create_connection((host, port), 10)

    def login(self, username, password, character):
        seed_packet = self.read_packet()
        seed = seed_packet.seed

        key = generate_login_key(seed, username, password)
        login_request_packet = LoginRequest(0, username, key)
        self.send_packet(login_request_packet)

        character_list_packet = self.read_packet()
        index = character_list_packet.names.index(character.capitalize())

        login_select_packet = LoginSelect(character_list_packet.character_ids[index])
        self.send_packet(login_select_packet)

        packet = self.read_packet()
        return packet.id == LoginOK.id

    def read_packet(self, time=1):
        """
        Wait for packet from server.
        """

        if not select.select([self.socket], [], [], time)[0]:
            return None
        else:
            # Read data from server
            head = self.read_bytes(4)
            packet_type, packet_length = struct.unpack(">2H", head)
            data = self.read_bytes(packet_length)

            packet = ServerPacket.get_instance(packet_type, data)
            return packet

    def send_packet(self, packet):
        data = packet.to_bytes()
        data = struct.pack(">2H", packet.id, len(data)) + data

        self.write_bytes(data)

    def read_bytes(self, num_bytes):
        data = bytes()

        while num_bytes > 0:
            chunk = self.socket.recv(num_bytes)

            if chunk == "":
                raise EOFError

            num_bytes -= len(chunk)
            data = data + chunk

        return data

    def write_bytes(self, data):
        num_bytes = len(data)

        while num_bytes > 0:
            sent = self.socket.send(data)

            if sent == 0:
                raise EOFError

            data = data[sent:]
            num_bytes -= sent
