from core.aochat.packets import *


class ServerPacket(Packet):
    def __init__(self, packet_id, types, args):
        self.id = packet_id
        self.types = types
        self.args = args

    def to_bytes(self):
        return encode_args(self.types, self.args)

    def __str__(self):
        return "ServerPacket(%d): %s" % (self.id, self.args)

    @classmethod
    def get_instance(cls, packet_id, data):
        if packet_id == LoginSeed.id:
            return LoginSeed.from_bytes(data)
        elif packet_id == LoginOK.id:
            return LoginOK.from_bytes(data)
        elif packet_id == LoginError.id:
            return LoginError.from_bytes(data)
        elif packet_id == LoginCharacterList.id:
            return LoginCharacterList.from_bytes(data)
        elif packet_id == CharacterUnknown.id:
            return CharacterUnknown.from_bytes(data)
        elif packet_id == CharacterName.id:
            return CharacterName.from_bytes(data)
        elif packet_id == CharacterLookup.id:
            return CharacterLookup.from_bytes(data)
        elif packet_id == PrivateMessage.id:
            return PrivateMessage.from_bytes(data)
        elif packet_id == VicinityMessage.id:
            return VicinityMessage.from_bytes(data)
        elif packet_id == BroadcastMessage.id:
            return BroadcastMessage.from_bytes(data)
        elif packet_id == SimpleSystemMessage.id:
            return SimpleSystemMessage.from_bytes(data)
        elif packet_id == SystemMessage.id:
            return SystemMessage.from_bytes(data)
        elif packet_id == BuddyAdded.id:
            return BuddyAdded.from_bytes(data)
        elif packet_id == BuddyRemoved.id:
            return BuddyRemoved.from_bytes(data)
        elif packet_id == PrivateChannelInvited.id:
            return PrivateChannelInvited.from_bytes(data)
        elif packet_id == PrivateChannelKicked.id:
            return PrivateChannelKicked.from_bytes(data)
        elif packet_id == PrivateChannelLeft.id:
            return PrivateChannelLeft.from_bytes(data)
        elif packet_id == PrivateChannelClientJoined.id:
            return PrivateChannelClientJoined.from_bytes(data)
        elif packet_id == PrivateChannelClientLeft.id:
            return PrivateChannelClientLeft.from_bytes(data)
        elif packet_id == PrivateChannelMessage.id:
            return PrivateChannelMessage.from_bytes(data)
        elif packet_id == PrivateChannelInviteRefused.id:
            return PrivateChannelInviteRefused.from_bytes(data)
        elif packet_id == PublicChannelJoined.id:
            return PublicChannelJoined.from_bytes(data)
        elif packet_id == PublicChannelLeft.id:
            return PublicChannelLeft.from_bytes(data)
        elif packet_id == PublicChannelMessage.id:
            return PublicChannelMessage.from_bytes(data)
        elif packet_id == Pong.id:
            return Pong.from_bytes(data)
        else:
            return None


class LoginSeed(ServerPacket):
    id = 0
    types = "S"

    def __init__(self, seed):
        self.seed = seed
        super().__init__(self.id, self.types, [self.seed])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class LoginOK(ServerPacket):
    id = 5
    types = ""

    def __init__(self):
        super().__init__(self.id, self.types, [])

    @classmethod
    def from_bytes(cls, data):
        return cls()


class LoginError(ServerPacket):
    id = 6
    types = "S"

    def __init__(self, message):
        self.message = message
        super().__init__(self.id, self.types, [self.message])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class LoginCharacterList(ServerPacket):
    id = 7
    types = "isii"

    def __init__(self, char_ids, names, levels, online_statuses):
        self.char_ids = char_ids
        self.names = names
        self.levels = levels
        self.online_statuses = online_statuses
        super().__init__(self.id, self.types, [self.char_ids, self.names, self.levels, self.online_statuses])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class CharacterUnknown(ServerPacket):
    id = 10
    types = "I"

    def __init__(self, char_id):
        self.char_id = char_id
        super().__init__(self.id, self.types, [self.char_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class CharacterName(ServerPacket):
    id = 20
    types = "IS"

    def __init__(self, char_id, name):
        self.char_id = char_id
        self.name = name
        super().__init__(self.id, self.types, [self.char_id, self.name])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class CharacterLookup(ServerPacket):
    id = 21
    types = "IS"

    def __init__(self, char_id, name):
        self.char_id = char_id
        self.name = name
        super().__init__(self.id, self.types, [self.char_id, self.name])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateMessage(ServerPacket):
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


class VicinityMessage(ServerPacket):
    id = 34
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


class BroadcastMessage(ServerPacket):
    id = 35
    types = "SSS"

    def __init__(self, text, message, blob):
        self.text = text
        self.message = message
        self.blob = blob
        super().__init__(self.id, self.types, [self.text, self.message, self.blob])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class SimpleSystemMessage(ServerPacket):
    id = 36
    types = "S"

    def __init__(self, message):
        self.message = message
        super().__init__(self.id, self.types, [self.message])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class SystemMessage(ServerPacket):
    id = 37
    types = "IIIS"

    def __init__(self, client_id, window_id, message_id, message_args):
        self.client_id = client_id
        self.window_id = window_id
        self.message_id = message_id
        self.message_args = message_args
        super().__init__(self.id, self.types, [self.client_id, self.window_id, self.message_id, self.message_args])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class BuddyAdded(ServerPacket):
    id = 40
    types = "IIS"

    def __init__(self, char_id, online, status):
        self.char_id = char_id
        self.online = online
        self.status = status
        super().__init__(self.id, self.types, [self.char_id, self.online, self.status])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class BuddyRemoved(ServerPacket):
    id = 41
    types = "I"

    def __init__(self, char_id):
        self.char_id = char_id
        super().__init__(self.id, self.types, [self.char_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelInvited(ServerPacket):
    id = 50
    types = "I"

    def __init__(self, private_channel_id):
        self.private_channel_id = private_channel_id
        super().__init__(self.id, self.types, [self.private_channel_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelKicked(ServerPacket):
    id = 51
    types = "I"

    def __init__(self, private_channel_id):
        self.private_channel_id = private_channel_id
        super().__init__(self.id, self.types, [self.private_channel_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelLeft(ServerPacket):
    id = 53
    types = "I"

    def __init__(self, private_channel_id):
        self.private_channel_id = private_channel_id
        super().__init__(self.id, self.types, [self.private_channel_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelClientJoined(ServerPacket):
    id = 55
    types = "II"

    def __init__(self, private_channel_id, char_id):
        self.private_channel_id = private_channel_id
        self.char_id = char_id
        super().__init__(self.id, self.types, [self.private_channel_id, self.char_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelClientLeft(ServerPacket):
    id = 56
    types = "II"

    def __init__(self, private_channel_id, char_id):
        self.private_channel_id = private_channel_id
        self.char_id = char_id
        super().__init__(self.id, self.types, [self.private_channel_id, self.char_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelMessage(ServerPacket):
    id = 57
    types = "IISS"

    def __init__(self, private_channel_id, char_id, message, blob):
        self.private_channel_id = private_channel_id
        self.char_id = char_id
        self.message = message
        self.blob = blob
        super().__init__(self.id, self.types, [self.private_channel_id, self.char_id, self.message, self.blob])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PrivateChannelInviteRefused(ServerPacket):
    id = 58
    types = "II"

    def __init__(self, private_channel_id, char_id):
        self.private_channel_id = private_channel_id
        self.char_id = char_id
        super().__init__(self.id, self.types, [self.private_channel_id, self.char_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PublicChannelJoined(ServerPacket):
    id = 60
    types = "GSIS"

    def __init__(self, channel_id, name, unknown, flags):
        self.channel_id = channel_id
        self.name = name
        self.unknown = unknown
        self.flags = flags
        super().__init__(self.id, self.types, [self.channel_id, self.name, self.unknown, self.flags])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PublicChannelLeft(ServerPacket):
    id = 61
    types = "G"

    def __init__(self, channel_id):
        self.channel_id = channel_id
        super().__init__(self.id, self.types, [self.channel_id])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class PublicChannelMessage(ServerPacket):
    id = 65
    types = "GISS"

    def __init__(self, channel_id, char_id, message, blob):
        self.channel_id = channel_id
        self.char_id = char_id
        self.message = message
        self.blob = blob
        super().__init__(self.id, self.types, [self.channel_id, self.char_id, self.message, self.blob])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)


class Pong(ServerPacket):
    id = 100
    types = "S"

    def __init__(self, blob):
        self.blob = blob
        super().__init__(self.id, self.types, [self.blob])

    @classmethod
    def from_bytes(cls, data):
        args = decode_args(cls.types, data)
        return cls(*args)
