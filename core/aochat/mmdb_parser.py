import struct
from core.logger import Logger


class MMDBParser:
    def __init__(self, filename):
        self.filename = filename
        self.logger = Logger(__name__)

    def get_message_string(self, category_id, instance_id):
        with open(self.filename, mode="rb") as file:
            categories = self.get_categories(file)

            try:
                category = next(categories)
                while category["id"] != category_id:
                    category = next(categories)
                next_category = next(categories)
            except StopIteration:
                return None

            instance = self.find_entry(file, instance_id, category["offset"], next_category["offset"])

            if instance:
                file.seek(instance["offset"])
                return self.read_string(file)
            else:
                return None

    def get_all_message_strings(self):
        with open(self.filename, mode="rb") as file:
            categories = iter(list(self.get_categories(file)))
            next_category = next(categories)

            while True:
                try:
                    category = next_category
                    next_category = next(categories)
                except StopIteration:
                    break

                max_offset = next_category["offset"]
                file.seek(category["offset"])

                instances = []
                while file.tell() < max_offset:
                    entry = self.read_entry(file)
                    instances.append(entry)

                for instance in instances:
                    file.seek(instance["offset"])
                    message_string = self.read_string(file)
                    print([category["id"], instance["id"], message_string])

    def find_entry(self, file, entry_id, min_offset, max_offset):
        file.seek(min_offset)
        entry = self.read_entry(file)
        while file.tell() <= max_offset:
            if entry["id"] == entry_id:
                return entry
            entry = self.read_entry(file)

        return None

    def get_categories(self, file):
        file.seek(4)
        num_categories = self.read_int(file)
        for i in range(0, num_categories):
            yield self.read_entry(file)

    def read_entry(self, file):
        return {"id": self.read_int(file), "offset": self.read_int(file)}

    def read_int(self, file):
        return int.from_bytes(file.read(4), byteorder="little")

    def read_string(self, file):
        message = bytearray()
        char = file.read(1)
        i = 0
        while char and char != b'\x00':
            i += 1
            message.append(ord(char))
            char = file.read(1)

        return message.decode("utf-8")

    def read_base_85(self, num_str):
        n = 0
        for i in range(0, 5):
            n = n * 85 + num_str[i] - 33
        return n

    def write_base_85(self, n):
        num_str = [None] * 5
        for i in reversed(range(0, 5)):
            num_str[i] = chr(n % 85 + 33)
            n = n // 85
        return "".join(num_str).encode("utf-8")

    def parse_params(self, param_arr):
        args = []
        while len(param_arr) > 0:
            data_type = chr(param_arr[0])
            param_arr = param_arr[1:]
            if data_type == "S":
                size = param_arr[0] * 256 + param_arr[1]
                args.append(param_arr[2:2 + size].decode("utf-8"))
                param_arr = param_arr[2 + size:]
            elif data_type == "s":
                size = param_arr[0] - 1  # size is 1 less than indicated
                args.append(param_arr[1:1 + size].decode("utf-8"))
                param_arr = param_arr[1 + size:]
            elif data_type == "I":
                args.append(struct.unpack(">I", param_arr[:4])[0])
                param_arr = param_arr[4:]
            elif data_type == "i" or data_type == "u":
                args.append(self.read_base_85(param_arr[:5]))
                param_arr = param_arr[5:]
            elif data_type == "R":
                category_id = self.read_base_85(param_arr[:5])
                instance_id = self.read_base_85(param_arr[5:10])
                message = self.get_message_string(category_id, instance_id)
                if not message:
                    raise Exception("Could not find message string for category '%d' and instance '%d'" % (category_id, instance_id))
                args.append(message)
                param_arr = param_arr[10:]
            elif data_type == "l":
                category_id = 20000
                instance_id = struct.unpack(">I", param_arr[:4])[0]
                message = self.get_message_string(category_id, instance_id)
                if not message:
                    raise Exception("Could not find message string for category '%d' and instance '%d'" % (category_id, instance_id))
                args.append(message)
                param_arr = param_arr[4:]
            elif data_type == "~":
                break
            else:
                raise Exception("Unknown data type '%s'" % data_type)

        return args

    def write_param(self, data_type, value):
        result = bytes()
        result += data_type.encode("utf-8")
        if data_type == "s":
            size = len(value) + 1
            result += chr(size).encode("utf-8")
            result += value.encode("utf-8")
        else:
            raise Exception("Unknown data type '%s'" % data_type)
        return result

    def write_ext_message(self, category_id, instance_id, params=[]):
        ext_msg = bytes()
        ext_msg += b"~&"
        ext_msg += self.write_base_85(category_id)
        ext_msg += self.write_base_85(instance_id)

        for data_type, param in params:
            ext_msg += self.write_param(data_type, param)

        ext_msg += b"~"

        return ext_msg
