from core.logger import Logger
import discord
import asyncio


class DiscordWrapper(discord.Client):
    def __init__(self, channels, servers, dqueue, aoqueue, db):
        super().__init__(loop=asyncio.new_event_loop())
        self.logger = Logger(__name__)
        self.relay_to = {}
        self.dqueue = dqueue
        self.aoqueue = aoqueue
        self.channels = channels
        self.available_servers = servers
        self.db = db

    async def on_ready(self):
        self.dqueue.append(("discord_ready", "ready"))
        self.dqueue.append(("discord_channels", self.get_all_channels()))

        for server in self.servers:
            self.available_servers.append(server)

    async def on_message(self, message):
        if message.content.startswith("!") and len(message.content) > 1:
            command = message.content[1:]
            self.dqueue.append(("discord_command", command))

        elif not message.author.bot:
            cid = message.channel.id
            if cid in self.channels:
                if self.channels[cid].relay_dc:
                    self.dqueue.append(("discord_message", message))
    
    async def relay_message(self):
        await self.wait_until_ready()

        while not self.is_closed:
            if self.aoqueue:
                try:
                    dtype, message = self.aoqueue.pop(0)

                    if dtype == "get_invite":
                        name = message[0]
                        server = message[1]

                        invites = await self.invites_from(server)
                        self.dqueue.append(("discord_invites", (name, invites)))

                    else:
                        content = message.get_message()

                        for cid, channel in self.channels.items():
                            if channel.relay_ao:
                                if message.get_type() == "embed":
                                    await self.send_message(discord.Object(id=cid), embed=content)
                                else:
                                    await self.send_message(discord.Object(id=cid), content)
                except Exception as e:
                    self.logger.error("Exception raised during Discord event (%s, %s)" % (str(dtype), str(message)), e)

            await asyncio.sleep(1)
