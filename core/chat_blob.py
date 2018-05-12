class ChatBlob:
    def __init__(self, title, msg, footer=None, max_num_pages=None):
        self.title = title
        self.msg = msg
        self.footer = footer
        self.max_num_pages = max_num_pages
