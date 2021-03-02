import threading
import time

from core.aochat.bot import Bot
from core.aochat.client_packets import Ping
from core.aochat.delay_queue import DelayQueue
from core.dict_object import DictObject


class Conn(Bot):
    def __init__(self, _id, failure_callback):
        super().__init__()
        self.id = _id
        self.packet_queue = DelayQueue(2, 2.5)
        self.packet_last_received_timestamp = time.time()
        self.failure_callback = failure_callback
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

    def read_packet(self, max_delay_time=1):
        self.check_outgoing_message_queue()
        packet = super().read_packet(max_delay_time)
        if not packet:
            time_since = time.time() - self.packet_last_received_timestamp
            if time_since > 90:
                self.logger.error(f"no packet received in 90 seconds for conn {self.id}")
                self.failure_callback()
            elif time_since > 60:
                self.send_packet(Ping("tyrbot_aochat"))
        else:
            self.packet_last_received_timestamp = time.time()
        return packet

    def send_packet(self, packet):
        # synchronize sending packets
        try:
            with self.send_lock:
                super().send_packet(packet)
        except Exception as e:
            self.failure_callback()

    def add_packet_to_queue(self, packet):
        self.packet_queue.enqueue(packet)
        self.check_outgoing_message_queue()

    def check_outgoing_message_queue(self):
        # check packet queue for outgoing packets
        outgoing_packet = self.packet_queue.dequeue()
        while outgoing_packet:
            self.send_packet(outgoing_packet)
            outgoing_packet = self.packet_queue.dequeue()

        num_messages = len(self.packet_queue)
        if num_messages > 30:
            self.logger.warning("automatically clearing outgoing message queue (%d messages)" % num_messages)
            self.packet_queue.clear()
        elif num_messages > 10:
            self.logger.warning("%d messages in outgoing message queue" % num_messages)

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
