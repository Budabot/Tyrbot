class SenderObj:
    def __init__(self, char_id, name, access_level):
        self.char_id = char_id
        self.name = name
        self.access_level = access_level

    def __str__(self):
        return self.__dict__.__str__()

    def __repr__(self):
        return self.__str__()

    def __eq__(self, obj):
        return isinstance(obj, SenderObj) and \
               obj.char_id == self.char_id and \
               obj.name == self.name and \
               obj.access_level == self.access_level
