from core.aochat.packets import *


class ClientPacket(Packet):
    def __init__(self, packet_id, types, args):
        self.id = packet_id
        self.types = types
        self.args = args

    def to_bytes(self):
        return encode_args(self.types, self.args)

    def __str__(self):
        return "ClientPacket(%d): %s" % (self.id, self.args)

    @classmethod
    def get_instance(cls, packet_id, data):
        if packet_id == LoginRequest.id:
            LoginRequest.from_bytes(data)
        elif packet_id == LoginSelect.id:
            LoginSelect.from_bytes(data)
        elif packet_id == CharacterLookup.id:
            CharacterLookup.from_bytes(data)
        elif packet_id == PrivateMessage.id:
            PrivateMessage.from_bytes(data)
        elif packet_id == BuddyAdd.id:
            BuddyAdd.from_bytes(data)
        elif packet_id == BuddyRemove.id:
            BuddyRemove.from_bytes(data)
        elif packet_id == PrivateChannelInvite.id:
            PrivateChannelInvite.from_bytes(data)
        elif packet_id == PrivateChannelKick.id:
            PrivateChannelKick.from_bytes(data)
        elif packet_id == PrivateChannelJoin.id:
            PrivateChannelJoin.from_bytes(data)
        elif packet_id == PrivateChannelLeave.id:
            PrivateChannelLeave.from_bytes(data)
        elif packet_id == PrivateChannelKickAll.id:
            PrivateChannelKickAll.from_bytes(data)
        elif packet_id == PrivateChannelMessage.id:
            PrivateChannelMessage.from_bytes(data)
        elif packet_id == PublicChannelMessage.id:
            PublicChannelMessage.from_bytes(data)
        elif packet_id == Ping.id:
            Ping.from_bytes(data)
        elif packet_id == ChatCommand.id:
            ChatCommand.from_bytes(data)
        else:
            return None


class LoginRequest(ClientPacket):
    id = 2
    types = "ISS"

    def __init__(self, unknown, username, key):
        self.unknown = unknown
        self.username = username
        self.key = key
        super().__init__(self.id, self.types, [self.unknown, self.username, self.key])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class LoginSelect(ClientPacket):
    id = 3
    types = "I"

    def __init__(self, char_id):
        self.char_id = char_id
        super().__init__(self.id, self.types, [self.char_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class CharacterLookup(ClientPacket):
    id = 21
    types = "S"

    def __init__(self, name):
        self.name = name
        super().__init__(self.id, self.types, [self.name])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateMessage(ClientPacket):
    id = 30
    types = "ISS"

    def __init__(self, char_id, message, blob):
        self.char_id = char_id
        self.message = message
        self.blob = blob
        super().__init__(self.id, self.types, [self.char_id, self.message, self.blob])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class BuddyAdd(ClientPacket):
    id = 40
    types = "IS"

    def __init__(self, char_id, status):
        self.char_id = char_id
        self.status = status
        super().__init__(self.id, self.types, [self.char_id, self.status])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class BuddyRemove(ClientPacket):
    id = 41
    types = "I"

    def __init__(self, char_id):
        self.char_id = char_id
        super().__init__(self.id, self.types, [self.char_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelInvite(ClientPacket):
    id = 50
    types = "I"

    def __init__(self, char_id):
        self.char_id = char_id
        super().__init__(self.id, self.types, [self.char_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelKick(ClientPacket):
    id = 51
    types = "I"

    def __init__(self, char_id):
        self.char_id = char_id
        super().__init__(self.id, self.types, [self.char_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelJoin(ClientPacket):
    id = 52
    types = "I"

    def __init__(self, private_channel_id):
        self.private_channel_id = private_channel_id
        super().__init__(self.id, self.types, [self.private_channel_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelLeave(ClientPacket):
    id = 53
    types = "I"

    def __init__(self, private_channel_id):
        self.private_channel_id = private_channel_id
        super().__init__(self.id, self.types, [self.private_channel_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelKickAll(ClientPacket):
    id = 54
    types = ""

    def __init__(self):
        super().__init__(self.id, self.types, [])

    @classmethod
    def from_bytes(cls, data):
        return cls()


class PrivateChannelMessage(ClientPacket):
    id = 57
    types = "ISS"

    def __init__(self, private_channel_id, message, blob):
        self.private_channel_id = private_channel_id
        self.message = message
        self.blob = blob
        super().__init__(self.id, self.types, [self.private_channel_id, self.message, self.blob])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PublicChannelMessage(ClientPacket):
    id = 65
    types = "GSS"

    def __init__(self, channel_id, message, blob):
        self.channel_id = channel_id
        self.message = message
        self.blob = blob
        super().__init__(self.id, self.types, [self.channel_id, self.message, self.blob])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class Ping(ClientPacket):
    id = 100
    types = "S"

    def __init__(self, blob):
        self.blob = blob
        super().__init__(self.id, self.types, [self.blob])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class ChatCommand(ClientPacket):
    id = 120
    types = "s"

    def __init__(self, commands):
        self.commands = commands
        super().__init__(self.id, self.types, [self.commands])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)
