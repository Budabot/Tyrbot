import asyncio
import discord
from discord import ChannelType

from core.logger import Logger
from modules.standard.discord.discord_message import DiscordEmbedMessage


class DiscordWrapper(discord.Client):
    def __init__(self, channel_id, event_service, aoqueue):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.invites = True
        super().__init__(intents=intents)

        self.logger = Logger(__name__)
        self.event_service = event_service
        self.aoqueue = aoqueue
        self.channel_id = channel_id
        self.default_channel = None

    async def logout_with_message(self, msg):
        if self.default_channel:
            try:
                await self.default_channel.send(msg)
            except Exception:
                pass
        await self.close()

    async def on_ready(self):
        self.set_channel_id(self.channel_id)
        self.event_service.fire_event("discord_connected", None)

    async def on_message(self, message):
        if not message.author.bot and (self.default_channel and message.channel.id == self.default_channel.id or message.channel.type == ChannelType.private):
            self.event_service.fire_event("discord_message", message)

    async def relay_message(self):
        await self.wait_until_ready()
        while not self.is_closed():
            if self.aoqueue:
                dtype, message = self.aoqueue.pop(0)

                try:
                    if dtype == "get_invite":
                        name = message[0]
                        server = message[1]
                        guild = self.get_guild(server.id)
                        invites = await guild.invites() if guild else []
                        self.event_service.fire_event("discord_invites", (name, invites))

                    else:
                        content = message.get_message()
                        channel = message.channel or self.default_channel

                        if channel:
                            if isinstance(message, DiscordEmbedMessage):
                                await channel.send(embed=content)
                            else:
                                await channel.send(content)
                except Exception as e:
                    self.logger.error("Exception raised during Discord event (%s, %s)" % (str(dtype), str(message)), e)

            await asyncio.sleep(0.1)

    def set_channel_id(self, channel_id):
        if not channel_id:
            return False

        self.channel_id = int(channel_id)
        for channel in self.get_text_channels():
            if channel.id == self.channel_id:
                self.default_channel = channel
                return True
        return False

    def get_text_channels(self):
        return list(filter(lambda x: x.type is ChannelType.text, self.get_all_channels()))
