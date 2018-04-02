class MapObject:
    def __init__(self, row):
        self.row = row

    def get_row_value(self, name):
        return self.row[name]

    def __getitem__(self, name):
        return self.row[name]

    def __getattr__(self, name):
        return self.get_row_value(name)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.row.__str__()