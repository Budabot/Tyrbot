import logging
import socket
import struct
import select
import time

from core.aochat.server_packets import ServerPacket, LoginOK, LoginError, LoginCharacterList
from core.aochat.client_packets import LoginRequest, LoginSelect
from core.aochat.crypt import generate_login_key


class Bot:
    def __init__(self):
        self.socket = None
        self.char_id = None
        self.char_name = None
        self.is_main = None
        self.logger = logging.getLogger(__name__)

    def connect(self, host, port):
        self.logger.info(f"Connecting to '{host}:{port}'")
        self.socket = socket.create_connection((host, port), 10)

    def disconnect(self):
        if self.socket:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None

    def login(self, username, password, character, is_main, wait_for_logged_in=20):
        self.is_main = is_main

        character = character.capitalize()

        char_user_prefix = f"{character}({username}) -"

        # read seed packet
        self.logger.info(f"{char_user_prefix} Logging in")
        seed_packet = self.read_packet(10)
        seed = seed_packet.seed

        # send back challenge
        key = generate_login_key(seed, username, password)
        login_request_packet = LoginRequest(0, username, key)
        self.send_packet(login_request_packet)

        # read character list
        character_list_packet: LoginCharacterList = self.read_packet()
        if isinstance(character_list_packet, LoginError):
            self.logger.error(f"{char_user_prefix} Error logging in: {character_list_packet.message}")
            return False, character_list_packet
        if character not in character_list_packet.names:
            self.logger.error(f"{char_user_prefix} Character does not exist on this account")
            return False, character_list_packet
        index = character_list_packet.names.index(character)

        # select character
        self.char_id = character_list_packet.char_ids[index]
        self.char_name = character_list_packet.names[index]
        if character_list_packet.online_statuses[index] and wait_for_logged_in:
            self.logger.warning(f"{char_user_prefix} Character is already logged on, waiting {wait_for_logged_in}s before proceeding")
            time.sleep(wait_for_logged_in)
        login_select_packet = LoginSelect(self.char_id)
        self.send_packet(login_select_packet)

        # wait for OK
        packet = self.read_packet()
        if packet.id == LoginOK.id:
            self.logger.info(f"{char_user_prefix} Login successful!")
            return True, packet
        else:
            self.logger.error(f"{char_user_prefix} Error logging in: {packet.message}")
            return False, packet

    def read_packet(self, max_delay_time=1):
        """
        Wait for packet from server.
        """

        read, write, error = select.select([self.socket], [], [], max_delay_time)
        if not read:
            return None
        else:
            # Read data from server
            head = self.read_bytes(4)
            packet_type, packet_length = struct.unpack(">2H", head)
            data = self.read_bytes(packet_length)

            try:
                return ServerPacket.get_instance(packet_type, data)
            except Exception:
                self.logger.error("Error parsing packet parameters for packet_type '%d' and payload: %s" % (packet_type, data), exc_info=True)
                return None

    def send_packet(self, packet):
        data = packet.to_bytes()
        data = struct.pack(">2H", packet.id, len(data)) + data

        self.write_bytes(data)

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
