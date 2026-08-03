import asyncio
import struct
import threading
import time

from core.aochat.client_packets import LoginRequest, LoginSelect, Ping
from core.aochat.crypt import generate_login_key
from core.aochat.delay_queue import DelayQueue
from core.aochat.server_packets import ServerPacket, LoginOK, LoginError, LoginCharacterList
from core.bot_status import BotStatus
from core.dict_object import DictObject
from core.feature_flags import FeatureFlags
from core.logger import Logger
from core.registry import Registry


class Conn:
    def __init__(self, _id, failure_callback, async_service):
        self.id = _id
        self.logger = Logger(__name__)
        self.failure_callback = failure_callback

        self.char_id = None
        self.char_name = None
        self.is_main = None

        self.reader: asyncio.StreamReader = None
        self.writer: asyncio.StreamWriter = None
        self.packet_loop_task = None
        self.async_service = async_service

        self.packet_queue = DelayQueue(2, 2.5)
        self.packet_last_received_timestamp = time.time()
        self.send_lock = threading.Lock()
        self.org_channel_id = None
        self.org_id = None
        self.org_name = None
        self.channels = {}
        self.buddy_list = {}
        self.private_channel = {}
        # store module data that is conn-specific here
        self.data = DictObject({
            "wave_counter_job_id": None
        })

    # Pure async methods (scheduled on AsyncService background loop)

    async def _async_connect(self, host, port):
        self.logger.info(f"[{self.id}] Connecting via asyncio to '{host}:{port}'")
        self.reader, self.writer = await asyncio.open_connection(host, port)

    async def _async_disconnect(self):
        if self.packet_loop_task:
            self.packet_loop_task.cancel()
            self.packet_loop_task = None
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None

    async def _async_read_packet(self, timeout=1):
        if not self.reader:
            return None

        try:
            head = await asyncio.wait_for(self.reader.readexactly(4), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        except (asyncio.IncompleteReadError, EOFError, ConnectionError, OSError):
            raise EOFError("Connection closed by remote host")

        packet_type, packet_length = struct.unpack(">2H", head)

        try:
            data = await asyncio.wait_for(self.reader.readexactly(packet_length), timeout=10)
        except (asyncio.IncompleteReadError, EOFError, ConnectionError, OSError):
            raise EOFError("Connection closed while reading packet payload")

        try:
            return ServerPacket.get_instance(packet_type, data)
        except Exception:
            self.logger.error(f"[{self.id}] Error parsing packet {packet_type}", exc_info=True)
            return None

    async def _async_send_packet(self, packet):
        if not self.writer:
            raise RuntimeError("Cannot send packet: not connected")

        data = packet.to_bytes()
        header = struct.pack(">2H", packet.id, len(data))
        self.writer.write(header + data)
        await self.writer.drain()

    async def _async_login(self, username, password, character, is_main, wait_for_logged_in=20):
        self.is_main = is_main
        character = character.capitalize()
        char_user_prefix = f"[{self.id}] {character}({username}) -"

        self.logger.info(f"{char_user_prefix} Logging in via asyncio")
        seed_packet = await self._async_read_packet(timeout=10)
        if not seed_packet:
            return False, None
        seed = seed_packet.seed

        key = generate_login_key(seed, username, password)
        login_request_packet = LoginRequest(0, username, key)
        await self._async_send_packet(login_request_packet)

        character_list_packet: LoginCharacterList = await self._async_read_packet(timeout=10)
        if not character_list_packet or isinstance(character_list_packet, LoginError):
            self.logger.error(f"{char_user_prefix} Error logging in: {getattr(character_list_packet, 'message', 'No response')}")
            return False, character_list_packet

        if character not in character_list_packet.names:
            self.logger.error(f"{char_user_prefix} Character does not exist on this account")
            return False, character_list_packet

        index = character_list_packet.names.index(character)
        self.char_id = character_list_packet.char_ids[index]
        self.char_name = character_list_packet.names[index]

        if character_list_packet.online_statuses[index] and wait_for_logged_in:
            self.logger.warning(f"{char_user_prefix} Character is already logged on, waiting {wait_for_logged_in}s")
            await asyncio.sleep(wait_for_logged_in)

        login_select_packet = LoginSelect(self.char_id)
        await self._async_send_packet(login_select_packet)

        packet = await self._async_read_packet(timeout=10)
        if packet and packet.id == LoginOK.id:
            self.logger.info(f"{char_user_prefix} Login successful!")
            return True, packet
        else:
            msg = getattr(packet, "message", "Unknown error") if packet else "No response"
            self.logger.error(f"{char_user_prefix} Error logging in: {msg}")
            return False, packet

    async def _async_packet_loop(self, incoming_queue, mass_message_queue, get_bot_status):
        while get_bot_status() == BotStatus.RUN:
            try:
                self.check_outgoing_message_queue()
                packet = await self._async_read_packet(timeout=1)
                if packet:
                    self.packet_last_received_timestamp = time.time()
                    incoming_queue.put((self, packet))
                else:
                    time_since = time.time() - self.packet_last_received_timestamp
                    if time_since > 90:
                        self.logger.error(f"no packet received in 90 seconds for conn {self.id}")
                        if self.failure_callback:
                            self.failure_callback()
                    elif time_since > 60:
                        await self._async_send_packet(Ping("tyrbot_aochat"))

                if mass_message_queue:
                    if FeatureFlags.FORCE_LARGE_MESSAGES_FROM_SLAVES:
                        if self.packet_queue.is_empty():
                            pkt = mass_message_queue.get_or_default(block=False)
                            if pkt:
                                self.add_packets_to_queue([pkt])
                    else:
                        while self.packet_queue.is_empty():
                            pkt = mass_message_queue.get_or_default(block=False)
                            if pkt:
                                self.add_packets_to_queue([pkt])
                            else:
                                break

                await asyncio.sleep(0.01)
            except (EOFError, ConnectionError, OSError) as e:
                self.logger.error(f"[{self.id}] Connection lost: {e}")
                if self.failure_callback:
                    self.failure_callback()
                break
            except Exception as e:
                self.logger.error(f"[{self.id}] Unexpected error in packet loop", exc_info=True)
                if self.failure_callback:
                    self.failure_callback()
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                if isinstance(e, (EOFError, ConnectionResetError)):
                    self.logger.warning(f"[{self.id}] Connection closed")
                    if self.failure_callback:
                        self.failure_callback()
                    break
                self.logger.error(f"[{self.id}] Error in packet loop", exc_info=True)
                await asyncio.sleep(1)

    # Queue and helper methods

    def add_packets_to_queue(self, packets):
        for packet in packets:
            self.packet_queue.enqueue(packet)
        self.check_outgoing_message_queue()

    def check_outgoing_message_queue(self):
        # check packet queue for outgoing packets
        outgoing_packet = self.packet_queue.dequeue()
        while outgoing_packet:
            self._send_outgoing_packet(outgoing_packet)
            outgoing_packet = self.packet_queue.dequeue()

        num_messages = len(self.packet_queue)
        if num_messages > 30:
            self.logger.warning("automatically clearing outgoing message queue (%d messages)" % num_messages)
            self.packet_queue.clear()
        elif num_messages > 10:
            self.logger.warning("%d messages in outgoing message queue" % num_messages)

    def send_packet(self, packet, timeout=10):
        # synchronize sending packets
        with self.send_lock:
            return self.async_service.run_until_complete(self._async_send_packet(packet), timeout=timeout)

    def _send_outgoing_packet(self, packet):
        # synchronize sending packets
        with self.send_lock:
            self.async_service.run_coroutine(self._async_send_packet(packet))
    
    def disconnect(self, timeout=5):
        return self.async_service.run_until_complete(self._async_disconnect(), timeout=timeout)
    
    def connect(self, host, port, timeout=10):
        return self.async_service.run_until_complete(self._async_connect(host, port), timeout=timeout)

    def login(self, username, password, character, is_main, wait_for_logged_in=20):
        timeout = 30 + (wait_for_logged_in if wait_for_logged_in else 0)
        return self.async_service.run_until_complete(
            self._async_login(username, password, character, is_main, wait_for_logged_in),
            timeout=timeout
        )
        
    def start_packet_loop(self, incoming_queue, mass_message_queue, get_bot_status):
        self.packet_loop_task = self.async_service.run_coroutine(
            self._async_packet_loop(incoming_queue, mass_message_queue, get_bot_status)
        )

    def get_char_name(self):
        return self.char_name

    def get_char_id(self):
        return self.char_id

    def get_org_name(self):
        return self.org_name or f"UnknownOrg({self.org_id})"

    def __str__(self):
        return self.id

    def __repr__(self):
        return self.__str__()
