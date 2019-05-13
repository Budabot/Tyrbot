class SenderObj:
    def __init__(self, char_id, name, access_level):
        self.char_id = char_id
        self.name = name
        self.access_level = access_level

    def __str__(self):
        return self.__dict__.__str__()
