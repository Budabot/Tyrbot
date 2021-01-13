class ChatBlob:
    def __init__(self, title, msg):
        self.title = title
        self.msg = msg
        self.page_prefix = ""
        self.page_postfix = ""

    def __str__(self):
        return f"ChatBlob('{self.title}', '{self.msg}')"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, obj):
        return isinstance(obj, ChatBlob) and \
               obj.title == self.title and \
               obj.msg == self.msg and \
               obj.page_prefix == self.page_prefix and \
               obj.page_postfix == self.page_postfix
