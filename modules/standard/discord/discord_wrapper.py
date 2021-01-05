from asyncio.base_events import BaseEventLoop

from discord import Guild

from core.logger import Logger
import discord
import asyncio

from modules.standard.discord.discord_message import DiscordMessage


class DiscordWrapper(discord.Client):
    def __init__(self, channel_id, dqueue, aoqueue):
        super().__init__(intents=discord.Intents(guilds=True, invites=True, guild_messages=True, members=True))
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.logger = Logger(__name__)
        self.dqueue = dqueue
        self.aoqueue = aoqueue
        self.channel_id = channel_id

    async def on_ready(self):
        self.dqueue.append(("discord_ready", "ready"))

    async def on_message(self, message):
        # TODO use bot command symbol
        if message.content.startswith("!") and len(message.content) > 1:
            command = message.content[1:]
            self.dqueue.append(("discord_command", command))
        elif not message.author.bot and message.channel.id == self.channel_id:
            self.dqueue.append(("discord_message", message))

    async def relay_message(self):
        await self.wait_until_ready()
        while not self.is_closed():
            if self.aoqueue:
                try:
                    dtype, message = self.aoqueue.pop(0)

                    if dtype == "get_invite":
                        name = message[0]
                        server = message[1]
                        invites = await self.get_guild(server.id).invites()
                        self.dqueue.append(("discord_invites", (name, invites)))

                    else:
                        content = message.get_message()

                        if self.channel_id:
                            if message.get_type() == "embed":
                                await self.get_channel(self.channel_id).send(embed=content)
                            else:
                                await self.get_channel(self.channel_id).send(content)
                except Exception as e:
                    self.logger.error("Exception raised during Discord event (%s, %s)" % (str(dtype), str(message)), e)

            await asyncio.sleep(1)
