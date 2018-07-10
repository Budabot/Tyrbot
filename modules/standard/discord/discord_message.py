from discord import Embed

class DiscordMessage():
    def __init__(self, dtype, channel, sender, content, command=False, color=None):
        self.dtype = str(dtype)
        self.channel = str(channel)
        self.sender = str(sender)
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
            content = "Online list\n" + self.content

            self.message = Embed(title="Command", description=content, color=self.color)

        elif self.dtype == "color":
            self.message = "```apache\n%s\n%s\n```" % ("Online list", self.content)
        else:
            self.message = ""

    def build_message(self):
        if self.dtype == "embed":
            content = self.sender+": "+self.content

            self.message = Embed(title=self.channel, description=content, color=self.color)
        elif self.dtype == "color":
            self.message = "```apache\n[%s] %s: \"%s\"\n```" % (self.channel, self.sender, self.content)
        else:
            self.message = "["+self.channel+"] "+self.sender+": "+self.content

    def get_message(self):
        return self.message

    def get_type(self):
        return self.dtype