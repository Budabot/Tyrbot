from discord import Embed


class DiscordMessage:
    pass


class DiscordTextMessage(DiscordMessage):
    def __init__(self, content, channel=None):
        self.content = str(content).replace("\"", "'")
        self.channel = channel

    def get_message(self):
        return self.content


class DiscordEmbedMessage(DiscordMessage):
    def __init__(self, title, content, color=None, channel=None):
        self.title = str(title)
        self.content = str(content).replace("\"", "'")
        self.color = color
        self.channel = channel

        if self.color is None:
            self.color = 0

    def get_message(self):
        content = "\n" + self.content

        return Embed(title=self.title, description=content, color=self.color)
