from core.decorators import instance, command, event, timerevent
from core.logger import Logger
from core.setting_types import HiddenSettingType
from core.command_param_types import Int, Options, Any
from discord import Member, ChannelType
import discord
import asyncio
import pickle
import threading
import time
import datetime


class DiscordChannel:
    def __init__(self, channel_id, relay_ao, relay_dc):
        self.channel_id = channel_id
        self.relay_ao = relay_ao
        self.relay_dc = relay_dc


class DiscordWrapper(discord.Client):
    def __init__(self, queue):
        super().__init__()
        self.logger = Logger("discord_wrapper")
        self.relay_to = {}
        self.queue = queue

    def register(self, registry):
        self.db = registry.get_instance("db")
        self.event_manager = registry.get_instance("event_manager")

    @asyncio.coroutine
    def on_ready(self):  
        self.logger.info("Discord successfully logged on")
        #self.event_manager.fire_event("discord_ready")
        self.running = True

        channels = []

        # mmmeehh...
        '''for server in self.servers:
            self.logger.info("Retrieving channels for %s" % (server.name))
            row = self.db.query_single("SELECT relay_channels FROM discord WHERE g_id = ?", [server.id])

            if row is not None:
                self.relay_to[server.id] = pickle.loads(row.relay_channels)
            else:
                channels = []

                for channel in server.channels:
                    self.logger.info("Channel: '%s', type: '%s'" % (channel.id, channel.type))
                    if channel.type is ChannelType.text:
                        channels.append(DiscordChannel(channel.id, False, False))
                
                self.db.exec("INSERT INTO discord (g_id, relay_channels) VALUES (?,?)", [server.id, pickle.dumps(channels)])'''
        
        # Using this for now...
        for channel in self.get_all_channels():
            self.logger.info("Channel: '%s', type: '%s', name: '%s'" % (channel.id, channel.type, channel.name))
            if channel.type == ChannelType.text:
                # TODO Not working either; incoming channel.type is not comparable to ChannelType.text 
                channels.append(DiscordChannel(channel.id, False, False))

    @asyncio.coroutine
    def on_message(self, message):
        self.logger.info("On message event fired, firing discord_message event")
        self.queue.append(("discord_message", message))

    # TODO Not working...
    async def relay_message(self, message):
        async with self as client:
            await client.send_message(discord.Object(id="461198667026792460"), "Online list...")

    def get_relay(self):
        return self.relay_to

    def set_relay(self, relay):
        self.relay_to = relay


@instance()
class DiscordController:
    def __init__(self):
        self.relay_to = {}
        self.is_running = False
        self.dthread = None
        self.queue = []

        self.logger = Logger("discord")

        self.client = DiscordWrapper(self.queue)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.settings_manager = registry.get_instance("setting_manager")
        self.event_manager = registry.get_instance("event_manager")
        self.client.register(registry)

    def pre_start(self):
        self.event_manager.register_event_type("discord_ready")
        self.event_manager.register_event_type("discord_message")

    def start(self):
        self.settings_manager.register("discord_secret", "", "Discord secret token", HiddenSettingType(), "modules.custom.discord")

    @command(command="dsendmsg", params=[Any("message")], access_level="moderator", description="Send message to Discord")
    def dsendmsg_cmd(self, channel, sender, reply, args):
        asyncio.run_coroutine_threadsafe(self.client.send_message(discord.Object(id="437551368195014659"), args[0]), self.client.loop).result()

    @command(command="dconnect", params=[], access_level="moderator", description="Manually connect to Discord, if not already connected")
    def dconnect_cmd(self, channel, sender, reply, args):
        if self.client.is_logged_in:
            reply("Already connected to Discord")
        else:
            self.logger.info("Manual Discord connect attempt...")
            self.connect_discord_client()

    @command(command="enable_relay_ao", params=[Int("g_id"), Int("c_id"), Options(["on", "off"])], access_level="moderator", description="Enable relaying of channel messages from AO to Discord channel")
    def enable_relay_ao_cmd(self, channel, sender, reply, args):
        if not self.client.is_logged_in:
            reply("Discord client is not connected")
            return

        guild_id = args[0]
        channel_id = args[1]
        relay = args[2]

        relay_to = self.client.get_relay()

        if guild_id in relay_to:
            for channel in relay_to[guild_id]:
                channel.relay_ao = True if channel.channel_id is channel_id and relay is "on" else False

        self.db.exec("UPDATE discord SET relay_channels = ? WHERE g_id = ?", [pickle.dumps(relay_to), guild_id])
        self.client.set_relay(relay_to)

    @command(command="enable_relay_dc", params=[Int("g_id"), Int("c_id"), Options(["on", "off"])], access_level="moderator", description="Enable relaying of channel messages from Discord channel to AO")
    def enable_relay_dc_cmd(self, channel, sender, reply, args):
        if not self.client.is_logged_in:
            reply("Discord client is not connected")
            return

        guild_id = args[0]
        channel_id = args[1]
        relay = args[2]

        relay_to = self.client.get_relay()

        if guild_id in relay_to:
            for channel in relay_to[guild_id]:
                channel.relay_dc = True if channel.channel_id is channel_id and relay is "on" else False

        self.db.exec("UPDATE discord SET relay_channels = ? WHERE g_id = ?", [pickle.dumps(relay_to), guild_id])
        self.client.set_relay(relay_to)

    @event(event_type="connect", description="Connects the Discord client automatically on startup, if a token exists")
    def handle_connect_event(self, event_type, event_data):
        self.logger.info("Connect event fired, trying to connect Discord...")
        self.connect_discord_client()

    @event(event_type="org_message", description="Relay messages to Discord, if relaying is enabled")
    def handle_org_message_event(self, event_type, event_data):
        self.logger.info("Org message event fired, relaying...")
        asyncio.run_coroutine_threadsafe(self.client.send_message(discord.Object(id="437551368195014659"), event_data), self.client.loop).result()

    @timerevent(budatime="1s", description="Relay messages to AO, if relaying is enabled")
    def handle_discord_message_event(self, event_type, event_data):
        if self.queue:
            _, message = self.queue.pop(0)

            if isinstance(message.author, Member):
                name = message.author.nick or message.author.name
            else:
                name = message.author.name

            timestamp = datetime.datetime.fromtimestamp(time.time()).strftime("%H:%M:%S")

            self.logger.info("Message: [%s][%s]: %s" % (timestamp, name, message.content))
            self.bot.send_private_channel_message("[Discord] %s: %s" % (name, message.content))

    def connect_discord_client(self):
        token = self.settings_manager.get("discord_secret")

        if token is not None:
            self.dthread = threading.Thread(target=self.client.run, args=(token,), daemon=True)
            self.dthread.start()
        else:
            self.logger.error("No token registered, can't connect Discord")
