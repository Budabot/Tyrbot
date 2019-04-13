from core.logger import Logger
from discord.errors import Forbidden, NotFound
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

    # discord custom text translations
    def translate_content(self, content):
        # online members table, only use if any chars online
        if content.title == "Online" and content.description != "\nNo characters online.":
            # split content into rows
            rowSplit = content.description.split("\n")

            # store maximum string lengths, these will be used to space the table
            maxLengths = [0, 0, 0, 0]

            # store online member string splits
            onlineMembers = []
            
            # iterate rows to calc table size
            for i in range(len(rowSplit)):
                # get column split
                columnSplit = rowSplit[i].split(" ")

                # if we don't have 4 items then skip
                if len(columnSplit) != 4:
                    continue

                # store split for use later
                onlineMembers.append(columnSplit)

                # iterate each element in split
                for j in range(len(columnSplit)):
                    # get length of element
                    length = len(columnSplit[j])

                    # if length of element 'wins' then set value in array
                    if length > maxLengths[j]:
                        maxLengths[j] = length

            # add an additional space to each length
            for i in range(len(maxLengths)):
                maxLengths[i] += 1

            # start monospace
            content.description = "```"

            # iterate rows to build table
            for i in range(len(onlineMembers)):
                # get online member
                onlineMember = onlineMembers[i]
                
                # iterate each item in array (assuming 4 should be safe at this point)
                for j in range(4):
                    # append text to content, padded
                    content.description += onlineMember[j].ljust(maxLengths[j]);

                # append newline
                content.description += "\n"                

            # end monospace
            content.description += "```"
    
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
                                    # do custom text translations
                                    self.translate_content(content)

                                    await self.send_message(discord.Object(id=cid), embed=content)
                                else:
                                    await self.send_message(discord.Object(id=cid), content)
                except Exception as e:
                    self.logger.error("Exception raised during Discord event (%s, %s)" % (str(dtype), str(message)), e)

            await asyncio.sleep(1)
