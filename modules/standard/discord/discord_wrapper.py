from discord import ChannelType

from core.logger import Logger
import discord
import asyncio


class DiscordWrapper(discord.Client):
    def __init__(self, channel_id, dqueue, aoqueue):
        super().__init__(intents=discord.Intents(guilds=True, invites=True, guild_messages=True, dm_messages=True, members=True))
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.logger = Logger(__name__)
        self.dqueue = dqueue
        self.aoqueue = aoqueue
        self.channel_id = channel_id
        self.default_channel = None

    async def logout_with_message(self, msg):
        if self.default_channel:
            await self.default_channel.send(msg)
        await super().logout()

    async def on_ready(self):
        self.set_channel_id(self.channel_id)
        self.dqueue.append(("discord_ready", "ready"))

    async def on_message(self, message):
        if not message.author.bot and (self.default_channel and message.channel.id == self.default_channel.id or message.channel.type == ChannelType.private):
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
                        channel = message.channel or self.default_channel

                        if channel:
                            if message.get_type() == "embed":
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
