class MMDBParser:
    def __init__(self, filename):
        self.filename = filename

    def get_message_string(self, category_id, instance_id):
        with open(self.filename, "rb") as file:
            category = self.find_entry(file, category_id, 8)
            print(category)
            instance = self.find_entry(file, instance_id, category["offset"])
            print(instance)
            file.seek(instance["offset"])
            return self.read_string(file)

    def find_entry(self, file, entry_id, offset):
        file.seek(offset)
        previous_entry = None
        entry = self.read_entry(file)
        while not previous_entry or previous_entry["id"] < entry["id"]:
            if entry["id"] == entry_id:
                return entry
            entry = self.read_entry(file)

        return None

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
