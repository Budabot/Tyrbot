import discord
from discord import ChannelType

from core.dict_object import DictObject
from core.logger import Logger
from modules.standard.discord.discord_message import DiscordEmbedMessage


class DiscordWrapper(discord.Client):
    # Note: every method on this class runs on the Discord client's own thread. Nothing here may
    # touch bot state directly; `fire_event` is the hand-off back to the bot's main thread.
    def __init__(self, channel_id, fire_event, aoqueue):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.invites = True
        super().__init__(intents=intents)

        self.logger = Logger(__name__)
        self.fire_event = fire_event
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
        self.fire_event("discord_connected", None)

    async def on_message(self, message):
        if not message.author.bot and (self.default_channel and message.channel.id == self.default_channel.id or message.channel.type == ChannelType.private):
            self.fire_event("discord_message", message)

    async def relay_message(self):
        await self.wait_until_ready()
        while not self.is_closed():
            # pushed, not polled: this wakes the moment the bot queues something. The task is
            # cancelled by run_discord_client() when the client shuts down.
            dtype, message = await self.aoqueue.get()

            try:
                if dtype == "get_invite":
                    name, server_id = message
                    guild = self.get_guild(server_id)
                    invites = await guild.invites() if guild else []
                    self.fire_event("discord_invites", (name, invites))

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

    async def get_channel_snapshot(self):
        """
        Runs on the loop. Returns plain data rather than live discord.py channels: walking
        `guilds`/`channels` is only safe here, since those are lazy views over dicts that this
        loop mutates as guild and channel events arrive.
        """

        return [DictObject({"id": channel.id, "name": channel.name, "guild_name": channel.guild.name})
                for channel in self.get_text_channels()]

    async def get_server_snapshot(self):
        """Runs on the loop. See get_channel_snapshot()."""

        servers = []
        for guild in self.guilds:
            owner = guild.owner
            servers.append(DictObject({"id": guild.id,
                                       "name": guild.name,
                                       "member_count": len(guild.members),
                                       # owner is not always cached; the caller formats it
                                       "owner_nick": owner.nick if owner else None,
                                       "owner_str": str(owner) if owner else ""}))
        return servers

    async def set_default_channel(self, channel_id):
        """Runs on the loop, since set_channel_id() walks the channel list and writes state
        that on_message() reads."""

        return self.set_channel_id(channel_id)

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
