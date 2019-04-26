import socket
import struct
import select
from core.aochat.server_packets import ServerPacket, LoginOK, LoginError, LoginCharacterList
from core.aochat.client_packets import LoginRequest, LoginSelect, Ping
from core.logger import Logger
from core.aochat.crypt import generate_login_key
import time


class Bot:
    def __init__(self):
        self.socket = None
        self.char_id = None
        self.char_name = None
        self.logger = Logger(__name__)
        self.packet_last_sent_timestamp = 0

    def connect(self, host, port):
        self.logger.info("Connecting to '%s:%d'" % (host, port))
        self.socket = socket.create_connection((host, port), 10)

    def disconnect(self):
        if self.socket:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None

    def login(self, username, password, character):
        character = character.capitalize()

        # read seed packet
        self.logger.info("Logging in as '%s'" % character)
        seed_packet = self.read_packet(10)
        seed = seed_packet.seed

        # send back challenge
        key = generate_login_key(seed, username, password)
        login_request_packet = LoginRequest(0, username, key)
        self.send_packet(login_request_packet)

        # read character list
        character_list_packet: LoginCharacterList = self.read_packet()
        if isinstance(character_list_packet, LoginError):
            self.logger.error("Error logging in: %s" % character_list_packet.message)
            return False
        if character not in character_list_packet.names:
            self.logger.error("character '%s' does not exist on this account" % character)
            return False
        index = character_list_packet.names.index(character)

        # select character
        self.char_id = character_list_packet.char_ids[index]
        self.char_name = character_list_packet.names[index]
        if character_list_packet.online_statuses[index]:
            sleep_duration = 20
            self.logger.warning("character '%s' is already logged on, waiting %ds before proceeding" % (self.char_name, sleep_duration))
            time.sleep(sleep_duration)
        login_select_packet = LoginSelect(self.char_id)
        self.send_packet(login_select_packet)

        # wait for OK
        packet = self.read_packet()
        if packet.id == LoginOK.id:
            self.logger.info("Connected!")
            return True
        else:
            self.logger.error("Error logging in: %s" % packet.message)
            return False

    def read_packet(self, max_delay_time=1):
        """
        Wait for packet from server.
        """

        read, write, error = select.select([self.socket], [], [], max_delay_time)
        if not read:
            if time.time() - self.packet_last_sent_timestamp > 60:
                self.send_packet(Ping("tyrbot_aochat"))

            return None
        else:
            # Read data from server
            head = self.read_bytes(4)
            packet_type, packet_length = struct.unpack(">2H", head)
            data = self.read_bytes(packet_length)

            try:
                return ServerPacket.get_instance(packet_type, data)
            except Exception as e:
                self.logger.error("Error parsing packet parameters for packet_type '%d' and payload: %s" % (packet_type, data), e)
                return None

    def send_packet(self, packet):
        data = packet.to_bytes()
        data = struct.pack(">2H", packet.id, len(data)) + data

        self.write_bytes(data)
        self.packet_last_sent_timestamp = time.time()

    def read_bytes(self, num_bytes):
        data = bytes()

        while num_bytes > 0:
            chunk = self.socket.recv(num_bytes)

            if len(chunk) == 0:
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
