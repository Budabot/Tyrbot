from core.decorators import instance
from core.aochat.client_packets import CharacterLookup
from core.aochat import server_packets
from core.logger import Logger
import time


@instance()
class CharacterService:
    SYSTEM_CHAR_ID = 4294967295
    # Default budget for a single lookup, used when the caller does not supply its own deadline.
    # A timeout here is read by callers as "the character is inactive" - an inactive character's
    # name does not resolve on the chat server, which is how they are detected - so erring short
    # misreports an active character, and erring long costs latency.
    CHAR_LOOKUP_TIMEOUT = 30

    def __init__(self):
        self.logger = Logger(__name__)
        self.name_to_id = {}
        self.id_to_name = {}
        self.waiting_for_response = set()
        self.notify_on_receive = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")

    def pre_start(self):
        self.bot.register_packet_handler(server_packets.CharacterLookup.id, self.update)
        self.bot.register_packet_handler(server_packets.CharacterName.id, self.update)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS name_history (char_id INT NOT NULL, name VARCHAR(20) NOT NULL, created_at INT NOT NULL, PRIMARY KEY (char_id, name))")

    async def _wait_for_char_id(self, char_name, deadline=None):
        # char_name must be .capitalize()'ed

        # This re-enters the main dispatch loop from inside a command handler, so handlers run
        # nested inside other handlers. Until that is restructured, bound how long it can last:
        # without a deadline the loop continues for as long as *any* packet keeps arriving, so a
        # single unresolvable name can stall every other command indefinitely.
        #
        # `deadline` lets a caller resolving many names share one budget across all of them rather
        # than granting each name its own - see OrgListController, where 9000 names at 30s each
        # would be days. A caller that passes a deadline owns the reporting; the warning below is
        # only for the one-name-at-a-time case, where it would otherwise be silent.
        caller_owns_deadline = deadline is not None
        if not caller_owns_deadline:
            deadline = time.time() + self.CHAR_LOOKUP_TIMEOUT

        # the shared budget may already be spent, in which case do not wait at all
        if time.time() >= deadline:
            return self.name_to_id.get(char_name, None)

        packet = await self.bot.iterate(1)
        while packet and char_name not in self.name_to_id:
            if time.time() > deadline:
                if not caller_owns_deadline:
                    self.logger.warning("gave up waiting for char id of '%s' after %ds"
                                        % (char_name, self.CHAR_LOOKUP_TIMEOUT))
                break
            packet = await self.bot.iterate(1)

        # None here is not new: the pre-existing exit (no packet arrived) returns it too, and
        # callers already treat it as "the character is inactive"
        return self.name_to_id.get(char_name, None)

    async def resolve_char_to_id(self, char_name_or_id, deadline=None):
        """
        Args:
            char_name_or_id: name or char id
            deadline: optional time.time() value shared across a run of lookups. Without it each
                      call gets its own CHAR_LOOKUP_TIMEOUT.
        """

        if isinstance(char_name_or_id, int):
            return char_name_or_id
        elif char_name_or_id.isdigit():
            return int(char_name_or_id)
        else:
            char_name = char_name_or_id.capitalize()
            if char_name in self.name_to_id:
                return self.name_to_id[char_name]
            else:
                # the request always goes out, even past the deadline: the chat server answers
                # at its own steady rate, so a name sent now may well have been resolved by the
                # time it is asked for again
                self._send_lookup_if_needed(char_name)
                return await self._wait_for_char_id(char_name, deadline)

    def resolve_char_to_name(self, char_name_or_id, default=None):
        if isinstance(char_name_or_id, int) or char_name_or_id.isdigit():
            char_name = self.get_char_name(char_name_or_id)
            return char_name if char_name else default
        else:
            return char_name_or_id

    def get_char_name(self, char_id):
        return self.id_to_name.get(char_id, None)

    def update(self, conn, packet):
        self.waiting_for_response.discard(packet.name)

        if packet.char_id == self.SYSTEM_CHAR_ID:
            self.name_to_id[packet.name] = None
        else:
            self.id_to_name[packet.char_id] = packet.name
            self.name_to_id[packet.name] = packet.char_id
            self._update_name_history(packet.name, packet.char_id)

    def _update_name_history(self, char_name, char_id):
        params = [char_name, char_id, int(time.time())]
        self.db.exec("INSERT IGNORE INTO name_history (name, char_id, created_at) VALUES (?, ?, ?)", params)

    def _send_lookup_if_needed(self, char_name):
        # char_name must be .capitalize()'ed
        if char_name not in self.name_to_id and char_name not in self.waiting_for_response:
            self.waiting_for_response.add(char_name)
            # TODO load balance over all conns?
            self.bot.get_primary_conn().send_packet(CharacterLookup(char_name))
