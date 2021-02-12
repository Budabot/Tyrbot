class CommandRequest:
    def __init__(self, conn, channel, sender, reply):
        self.conn = conn
        self.channel = channel
        self.sender = sender
        self.reply = reply
