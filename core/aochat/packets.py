import struct


class UnknownArgumentType(Exception):
    pass


class PacketMissingArgument(Exception):
    pass


def decode_args(types, data):
    args = []
    for argtype in types:
        if argtype == "I":
            elem, data = data[:4], data[4:]
            result = struct.unpack(">I", elem)[0]

        elif argtype == "S":
            length = struct.unpack(">H", data[:2])[0]
            result = data[2:2 + length].decode("utf-8")
            data = data[2 + length:]

        elif argtype == "G":
            result, data = data[:5], data[5:]
            # Convert result (5 bytes) to a long.  Can't use
            # struct.unpack(">Q", "\x00"*3 + result), since we
            # can't rely on "long long" being available.
            high, low = struct.unpack(">BI", result)
            result = (high << 32) + low

        elif argtype == "i":
            length = struct.unpack(">H", data[:2])[0]
            result = struct.unpack(">%sI" % length, data[2:2 + 4 * length])
            data = data[2 + 4 * length:]

        elif argtype == "s":
            length = struct.unpack(">H", data[:2])[0]
            data = data[2:]
            result = []
            while length:
                slength = struct.unpack(">H", data[:2])[0]
                result.append(data[2:2 + slength].decode("utf-8"))
                data = data[2 + slength:]
                length -= 1

        else:
            raise UnknownArgumentType(argtype)

        args.append(result)

    return args


def encode_args(types, args):
    data = b""

    for argtype in types:
        if not args:
            raise PacketMissingArgument

        it = args[0]
        del args[0]

        if argtype == "I":
            data += struct.pack(">I", it)

        elif argtype == "S":
            encoded = it.encode("utf-8")
            data += struct.pack(">H", len(encoded))
            data += encoded

        elif argtype == "G":
            data += struct.pack(">BI", it >> 32, it & 0xffffffff)

        elif argtype == "s":
            data += struct.pack(">H", len(it))
            for it_elem in it:
                encoded = it_elem.encode("utf-8")
                data += struct.pack(">H", len(encoded))
                data += encoded

        else:
            raise UnknownArgumentType(argtype)

    return data


class Packet:
    pass
