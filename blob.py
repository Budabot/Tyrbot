class Blob:
    def __init__(self, title, msg):
        self.title = title
        self.msg = msg

    def get_pages(self, max_page_length, separators):
        return self.paginate(self.msg, max_page_length, separators)

    def paginate(self, msg, max_page_length, separators):
        if len(separators) == 0:
            return

        rest = msg
        current_page = ""
        pages = []

        while len(rest) > 0:
            line, rest = self.get_next_line(rest, max_page_length, separators)
            if len(current_page) + len(line) > max_page_length:
                pages.append(current_page)
                current_page = ""

            current_page += line

        pages.append(current_page)

        return pages

    def get_next_line(self, msg, max_page_length, separators):
        if len(separators) == 0:
            raise Exception("Could not paginate")

        separator = separators[0]
        result = msg.split(separator, 1)
        line = result[0]
        if len(result) == 1:
            rest = ""
        else:
            rest = result[1:][0]

        if separator == " " or separator == "\n":
            line += separator

        if len(line) > max_page_length:
            return self.get_next_line(msg, max_page_length, separators[1:])
        else:
            return line, rest

