class MMDBParser:
    def __init__(self, filename):
        self.filename = filename

    def get_message_string(self, category_id, instance_id):
        with open(self.filename, "rb") as file:
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

    def find_entry(self, file, entry_id, min_offset, max_offset):
        file.seek(min_offset)
        entry = self.read_entry(file)
        while file.tell() < max_offset:
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
