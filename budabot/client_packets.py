from budabot.packets import *


class ClientPacket(Packet):
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

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.unknown, self.username, self.key])


class LoginSelect(ClientPacket):
    id = 3
    types = "I"

    def __init__(self, character_id):
        self.character_id = character_id

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.character_id])


class CharacterLookup(ClientPacket):
    id = 21
    types = "S"

    def __init__(self, name):
        self.name = name

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.name])


class PrivateMessage(ClientPacket):
    id = 30
    types = "ISS"

    def __init__(self, character_id, message, blob):
        self.character_id = character_id
        self.message = message
        self.blob = blob

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.character_id, self.message, self.blob])


class BuddyAdd(ClientPacket):
    id = 40
    types = "IS"

    def __init__(self, character_id, status):
        self.character_id = character_id
        self.status = status

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.character_id, self.status])


class BuddyRemove(ClientPacket):
    id = 41
    types = "I"

    def __init__(self, character_id):
        self.character_id = character_id

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.character_id])


class PrivateChannelInvite(ClientPacket):
    id = 50
    types = "I"

    def __init__(self, character_id):
        self.character_id = character_id

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.character_id])


class PrivateChannelKick(ClientPacket):
    id = 51
    types = "I"

    def __init__(self, character_id):
        self.character_id = character_id

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.character_id])


class PrivateChannelJoin(ClientPacket):
    id = 52
    types = "I"

    def __init__(self, private_channel_id):
        self.private_channel_id = private_channel_id

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.private_channel_id])


class PrivateChannelLeave(ClientPacket):
    id = 53
    types = "I"

    def __init__(self, private_channel_id):
        self.private_channel_id = private_channel_id

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.private_channel_id])


class PrivateChannelKickAll(ClientPacket):
    id = 54
    types = ""

    def __init__(self):
        pass

    @classmethod
    def from_bytes(cls, data):
        return cls()

    def to_bytes(self):
        return encode_args(self.types, [])


class PrivateChannelMessage(ClientPacket):
    id = 57
    types = "ISS"

    def __init__(self, private_channel_id, message, blob):
        self.private_channel_id = private_channel_id
        self.message = message
        self.blob = blob

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.private_channel_id, self.message, self.blob])


class PublicChannelMessage(ClientPacket):
    id = 65
    types = "GSS"

    def __init__(self, channel_id, message, blob):
        self.channel_id = channel_id
        self.message = message
        self.blob = blob

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.channel_id, self.message, self.blob])


class Ping(ClientPacket):
    id = 100
    types = "S"

    def __init__(self, blob):
        self.blob = blob

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.blob])


class ChatCommand(ClientPacket):
    id = 120
    types = "s"

    def __init__(self, commands):
        self.commands = commands

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)

    def to_bytes(self):
        return encode_args(self.types, [self.commands])
