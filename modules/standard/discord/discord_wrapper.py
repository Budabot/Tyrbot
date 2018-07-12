from core.logger import Logger
from discord.errors import Forbidden, NotFound
import discord
import asyncio


class DiscordWrapper(discord.Client):
    def __init__(self, channels, servers, dqueue, aoqueue):
        super().__init__()
        self.logger = Logger("discord_wrapper")
        self.relay_to = {}
        self.dqueue = dqueue
        self.aoqueue = aoqueue
        self.channels = channels
        self.available_servers = servers

    def register(self, registry):
        self.db = registry.get_instance("db")
        self.event_manager = registry.get_instance("event_manager")

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
                except Forbidden as e:
                    self.dqueue.append(("discord_exception", "Insufficient permissions"))
                except NotFound as e:
                    self.dqueue.append(("discord_exception", "Not found error"))
                except:
                    self.dqueue.append(("discord_exception", "Exception raised during Discord event (%s, %s)" % (str(dtype), str(message))))

            await asyncio.sleep(1)
