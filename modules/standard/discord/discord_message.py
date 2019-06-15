from discord import Embed


class DiscordMessage:
    def __init__(self, dtype, channel, sender, content, color=None):
        self.dtype = str(dtype)
        self.channel = str(channel)
        self.sender = sender
        self.content = str(content).replace("\"", "'")
        self.color = color

        if self.color is None:
            self.color = 0

    def build_command_message(self):
        content = "\n" + self.content

        return Embed(title=self.channel, description=content, color=self.color)

    def build_message(self):
        if self.sender:
            content = self.sender + ": " + self.content
        else:
            content = self.content

        if self.channel:
            return "[%s] %s" % (self.channel, content)
        else:
            return content

    def get_message(self):
        if self.dtype == "embed":
            return self.build_command_message()
        else:
            return self.build_message()

    def get_type(self):
        return self.dtype
