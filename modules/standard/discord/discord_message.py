from discord import Embed


class DiscordMessage:
    def __init__(self, dtype, channel, sender, content, command=False, color=None):
        self.dtype = str(dtype)
        self.channel = str(channel)
        self.sender = sender
        self.content = str(content).replace("\"", "'")
        self.color = color

        if self.color is None:
            self.color = 0

        if command:
            self.build_command_message()
        else:
            self.build_message()

    def build_command_message(self):
        if self.dtype == "embed":
            content = "\n" + self.content

            self.message = Embed(title=self.channel, description=content, color=self.color)
        else:
            self.message = self.content

    def build_message(self):
        if self.sender:
            content = self.sender + ": " + self.content
        else:
            content = self.content

        if self.dtype == "embed":
            self.message = Embed(title=self.channel, description=content, color=self.color)
        else:
            self.message = "[%s] %s" % (self.channel, content)

    def get_message(self):
        return self.message

    def get_type(self):
        return self.dtype
