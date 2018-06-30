from core.decorators import instance, command, event
from core.logger import Logger
from core.setting_types import HiddenSettingType
from core.command_param_types import Int, Options, Any
from discord import Member, User, ChannelType
import discord
import asyncio
import logging
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
    def register(self, registry):
        self.db = registry.get_instance("db")
        self.event_manager = registry.get_instance("event_manager")
        self.relay_to = {}

    @asyncio.coroutine
    def on_ready(self):  
        self.logger.info("Discord successfully logged on")
        self.event_manager.fire_event("discord_ready")
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
            self.logger.info("Channel: '%s', type: '%s'" % (channel.id, channel.type))
            if channel.type == ChannelType.text:
                # TODO Not working either; incoming channel.type is not comparable to ChannelType.text 
                channels.append(DiscordChannel(channel.id, False, False))

    @asyncio.coroutine
    def on_message(self, message):
        self.logger.info("On message event fired, firing discord_message event")
        self.event_manager.fire_event("discord_message", message)
        
    # TODO Not working...
    async def relay_message(self, message):
        async with self as client:
            await client.send_message(discord.Object(id="461198667026792460"), "Online list...")

    def get_relay(self):
        return self.relay_to

    def set_relay(self, relay):
        self.relay_to = relay

    def set_logger(self, logger):
        self.logger = logger

@instance()
class DiscordController:
    def __init__(self):
        self.relay_to = {}
        self.is_running = False
        self.dthread = None

        logHandler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
        logHandler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.dLogger = logging.getLogger("discord")
        self.dLogger.setLevel(logging.DEBUG)
        self.dLogger.addHandler(logHandler)
        self.logger = Logger("discord")

        self.client = DiscordWrapper()
        self.client.set_logger(self.logger)


    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.settings_manager = registry.get_instance("setting_manager")
        self.event_manager = registry.get_instance("event_manager")
        self.client.register(registry)

    def pre_start(self):
        if not self.event_manager.is_event_type("discord_ready"):
            self.event_manager.register_event_type("discord_ready")
        if not self.event_manager.is_event_type("discord_message"):
            self.event_manager.register_event_type("discord_message")

    def start(self):
        # self.settings_manager.register("discord_secret", "put_test_token_here", "Discord secret token", HiddenSettingType(), "modules.custom.discord")
        pass
        

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

        self.db.exec("UPDATE discord SET relay_channels = ? WHERE g_id = ?", [pickle.dump(relay_to), guild_id])
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

        self.db.exec("UPDATE discord SET relay_channels = ? WHERE g_id = ?", [pickle.dump(relay_to), guild_id])
        self.client.set_relay(relay_to)


    @command(command="donline", params=[], access_level="member", description="See who's online on Discord")
    def donline_cmd(self, channel, sender, reply, args):
        if self.client.is_logged_in:
            pass
        else:
            reply("Discord not connected")

    @command(command="dgetinvite", params=[Int("g_id")], access_level="member", description="Get invite for specified guild (Discord server)")
    def dgetinvite_cmd(self, channel, sender, reply, args):
        if self.client.is_logged_in:
            pass
        else:
            reply("Discord not connected")

    @command(command="dsendprivate", params=[Any("name"), Any("message")], access_level="member", description="Send a message to a Discord user")
    def dsendprivate_cmd(self, channel, sender, reply, args):
        if self.client.is_logged_in:
            pass
        else:
            reply("Discord not connected")

    @command(command="dclosecon", params=[], access_level="moderator", description="Close the current Discord connection (NB: it is NOT possible reconnect after this)")
    def dclosecon(self, channel, sender, reply, args):
        if self.client.is_logged_in:
            self.client.logout()
        else:
            reply("Discord is not connected")

    @event(event_type="connect", description="Connects the Discord client automatically on startup, if a token exists")
    def handle_connect_event(self, event_type, event_data):
        self.logger.info("Connect event fired, trying to connect Discord...")
        self.connect_discord_client()

    @event(event_type="org_message", description="Relay messages to Discord, if relaying is enabled")
    def handle_org_message_event(self, event_type, event_data):
        self.logger.info("Org message event fired, relaying...")
        asyncio.run_coroutine_threadsafe(self.client.send_message(discord.Object(id="461198667026792460"), event_data), self.client.loop).result()


    @event(event_type="discord_message", description="Relay messages to AO, if relaying is enabled")
    def handle_discord_message_event(self, event_type, message):
        self.logger.info("Discord message event fired, relaying...")
        self.logger.info(message.content)

        if message.content.startswith("!"):
            self.handle_discord_command(message)
        else:
            if isinstance(message.author, Member):
                name = message.author.nick
            else:
                name = message.author.name
                
            timestamp = datetime.datetime.fromtimestamp(time.time()).strftime("%H:%M:%S")

            self.logger.info("Message: [%s][%s]: %s" % (timestamp, name, message.content))

    def connect_discord_client(self):
        #token = self.settings_manager.get("discord_secret")
        #token = None if token.get_value() is "None" else token.get_value()
        token = "put_token_here"

        if token is not None:
            self.dthread = threading.Thread(target=self.client.run, args=(token,), daemon=True)
            self.dthread.start()
        else:
            self.logger.error("No token registered, can't connect Discord")

    def handle_discord_command():
        cmd = message.content[1:]

        # TODO Work out args...
        if(" " in cmd):
            pass

        if cmd == "online":
            asyncio.run_coroutine_threadsafe(self.client.relay_message("Online list"), asyncio.get_event_loop()).result()