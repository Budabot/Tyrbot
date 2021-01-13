from discord import ChannelType, Forbidden

from core.logger import Logger
import discord
import asyncio


class DiscordWrapper(discord.Client):
    def __init__(self, channel_name, dqueue, aoqueue):
        super().__init__(intents=discord.Intents(guilds=True, invites=True, guild_messages=True, members=True))
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.logger = Logger(__name__)
        self.dqueue = dqueue
        self.aoqueue = aoqueue
        self.channel_name = channel_name
        self.channel = None

    async def logout_with_message(self, msg):
        if self.channel:
            await self.channel.send(msg)
        await super().logout()

    async def on_ready(self):
        self.set_channel_name(self.channel_name)
        self.dqueue.append(("discord_ready", "ready"))

    async def on_message(self, message):
        if not message.author.bot and self.channel and message.channel.id == self.channel.id:
            self.dqueue.append(("discord_message", message))

    async def relay_message(self):
        await self.wait_until_ready()
        while not self.is_closed():
            if self.aoqueue:
                dtype, message = self.aoqueue.pop(0)

                try:
                    if dtype == "get_invite":
                        name = message[0]
                        server = message[1]
                        # TODO handle insufficient permissions
                        invites = await self.get_guild(server.id).invites()
                        self.dqueue.append(("discord_invites", (name, invites)))

                    else:
                        content = message.get_message()

                        if self.channel:
                            if message.get_type() == "embed":
                                await self.channel.send(embed=content)
                            else:
                                await self.channel.send(content)
                except Exception as e:
                    self.logger.error("Exception raised during Discord event (%s, %s)" % (str(dtype), str(message)), e)

            await asyncio.sleep(1)

    def set_channel_name(self, channel_name):
        self.channel_name = channel_name
        for channel in self.get_text_channels():
            if channel.name == channel_name:
                self.channel = channel
                return True
        return False

    def get_text_channels(self):
        return list(filter(lambda x: x.type is ChannelType.text, self.get_all_channels()))
