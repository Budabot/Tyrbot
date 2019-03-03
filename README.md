# Tyrbot

This is a rewrite of the original [Budabot](https://github.com/Budabot/Budabot) in Python3.  

Budabot is an in-game chat-bot for the MMORPG Anarchy Online released by Funcom in 2001.  

## Installation
In its current state, this project is not meant to be used, other than during development.  

To install dependencies: `pip install -U -r requirements.txt`.

## Start
To start the bot, run either `start.bat` or `start.sh`.

If it is your first time running the bot, or if the config.json file does not exist, it will take you through the configuration wizard to configure the bot. You will need to have a character name that you you want to run the bot as along with the username and password for the account that has that character. If you want to run this bot as an org bot, you will also need the EXACT org name of the org and the character that the bot runs as will need to already be a member of that org.

## Discord setup
This section is supposed to work as a guide to how you setup the **Discord module**.
The Discord module enables relaying between AO and one or more Discord servers.

### Prerequisites:
- Must be server owner of the Discord server(s) that you want to relay to/from
- Must be superadmin of the Tyrbot to alter the bot token

### Setup a Discord app
1. Login to your Discord web profile and navigate to your [developers/applications](https://discordapp.com/developers/applications/) section
2. Click the blue "New Application" button in top-right corner
3. Name your application something (this can be changed)
4. Click your newly created application, if it hasn't opened up the overview of it already. You can rename the application here (this is not the bot, however, so it's just for you to keep track of). You can change the application picture (again, this is not for the bot that will show up in Discord's online listings)
5. Note the **Client ID** on the page "General Information" page, and do not forget it - we'll need it later!
6. Navigate to the "Bot" section of your application
7. Convert your application to a "bot user". Discord will warn you that this is not reversable, which is fine
8. The Bot overview will now show you the actual bot user, that will also show up on the Discord's online listings. You can rename the bot (this is the name that will show in the online list). You can add a profile picture, and this will be seen on Discord as well in the online list
9. Clicking the "Click to Reveal Token" will reveal some gibberish - **this is your _secret_ bot token, and you should never share it with anyone**. If you ever suspect anyone to have picked up your bot's _secret_ token, you can navigate to this site again, and click the "Regenerate"-button to invalidate the old token and create a new. **Remember this token**, as we'll need it for later when setting up the Discord module's settings
10. Leave everything as default unless you know what you're doing - you can specify certain permissions you want to give to your bot, by adding a mark in the "Bot Permissions" list. If you choose to make your own, do so now **and remember the number it generates**, we'll need it later
11. Open up your Discord app, or use the browser, and make sure you've selected your Discord server
12. Click the server's name, in the channel's listings
13. Click "Server Settings"
14. Navigate to "Roles"
15. Click the tiny "+"-sign with a circle around it
16. Name your new role (e.g. "Relay"), and setup its permissions, with the following settings enabled as a minimum: `Read Text Channels & See Voice Channals`,  `Send messages`
17. Now we need to invite our new bot to our server - this can only be done by the Discord server owner. We need the bot's **Client ID** and the **permissions number** - if you _did not_ create your own, you need to use **68608** as the permissions number. Navigate to the following site: `https://discordapp.com/oauth2/authorize?client_id=BOT_CLIENT_ID&scope=bot&permissions=PERMISSIONS_NUMBER`, _remember to replace **BOT_CLIENT_ID** and **PERMISSIONS_NUMBER** in the URL with the client ID and the permissions number you have **before you open up the URL in a browser**._
18. Pick your server from the list on the site, and make sure everything checks out regarding permissions (minimum should be `View Channels`, `Send Messages` and `Read Message History`, which is the permission number equal to 68608 mentioned earlier)
19. Click "Authorize", and wait a few moments, and you should be able to see your new bot join your server (it'll be listed as offline in the server's online listing - and will stay offline 'till we startup Tyrbot)

### Setup Tyrbot's Discord Module
1. Ingame, write `/tell <botname> config mod standard.discord`
2. You'll see `Discord bot token: <hidden> (change)` at the top
3. If you click "change", you'll be told how you can change this setting, but for good measure, the command is always: `/tell <botname> config setting discord_bot_token set YOUR_SECRET_BOT_TOKEN_HERE`. This setting will always stay "hidden", as in invisible, so no one can actually read/copy the token. Be aware, a superadmin can query the DB for the bot token, as it is stored as plain text - if you're not the superadmin, make sure you trust the superadmin, as they might be able to take advantage of the bot token
3. After setting the bot token restart your Tyrbot
4. In the logs, you should be able to see the following:

```python
WARNING - discord.client - PyNaCl is not installed, voice will NOT be supported
# you can ignore this, as we do not support any voice-related features anyway

INFO - discord.client - logging in using static token
# bot token was correctly saved before your restart

INFO - discord.gateway - Created websocket connected to wss://gateway.discord.gg?encoding=json&v=6 
# this means an initial connection to the Discord API has been established

INFO - discord.gateway - sent the identify payload to create the websocket 
# this means that the initial handshake and "authentication" was successful

INFO - discord.gateway - Unhandled event PRESENCES_REPLACE
# ignore this 

# By now, we should be connected
```

There are three ways the messages relayed from AO to Discord can be formatted:
- "plain", plain text, unformatted
- "color", using "Apache" markup, colored, single lines
- "embed", using embedded messages, each message is boxed

This can be chosen in the config for the Discord module (ingame), via 
`Format of message relayed to Discord: <setting chosen> (change)`.

If the "embed" setting is chosen for the formatting, the color of the embedded message on Discord can be chosen with
`Discord embedded message color: <color chosen> (change)`

The remaining settings are coloring for messages ingame, and should be straight forward.

In general, disabling any event might have consequences that'll leave the module not working as intended.

### Setup relaying to/from AO and the connected Discord bot
After successfully having the bot connect, and it's a member of a certain server, you can write `/tell <botname> discord` ingame, and it'll give you an overview of the current situation.

Relaying won't start before you've actually enabled the relaying to a specific channel. Remember, the bot **must be allowed to access the text channel in question** to be able to read/write to it. This means, that if you have a text channel which is only visible to certain roles on your Discord server, you must make the bot's role a part of this list as well, otherwise it won't be able to relay to/from the channel in question.

To bring up the relay setup, you simply write `/tell <botname> discord relay`, and a list of channels visible to your bot will be available.
All the available channels will be listed, and have 2 settings available:
- "Relay from AO", means that text written ingame in either the org- or private channel will be relayed to the text channel on Discord
- "Relay from Discord", means that text written in this text channel on Discord, will be relayed to the private- and org channel in AO

### The module is still in "beta" mode
The module was written with little to no knowledge of Python to begin with, let alone Python's take on async-await. The module is thus in a state of "working as intended, but could definitely be improved". If you have any ideas, or see any goofs in the code, you are welcome to submit changes to it via a pull request.

- The library used to build the module can be found [here](https://discordpy.readthedocs.io/en/latest/index.html).
- The official Discord API documentation can be found [here](https://discordapp.com/developers/docs/intro).
- The official Discord API server can be joined [here](https://discord.gg/discord-api).
