# Tyrbot

This is a rewrite of the original [Budabot](https://github.com/Budabot/Budabot) in Python3.  

Budabot is an in-game chat-bot for the MMORPG Anarchy Online released by Funcom in 2001.

## Requirements
Tyrbot requires Python 3.6.  Neither Python 3.5 or Python 3.7 will work.  We are working on adding support for Python 3.7.

## Installation
Tyrbot is now ready for general use and is recommended over Budabot or any other bot for all new installations.

Currently there are no releases for Tyrbot but you can download the bot from here which will always have the very latest changes: [https://github.com/Budabot/Tyrbot/archive/master.zip](https://github.com/Budabot/Tyrbot/archive/master.zip)

Then simply unzip the bot somewhere before starting it.

## Upgrade
If you are running a version of Tyrbot and simply want to upgrade to the latest version, follow these steps:

1. Download the latest version from here: [https://github.com/Budabot/Tyrbot/archive/master.zip](https://github.com/Budabot/Tyrbot/archive/master.zip)
1. Unzip the bot to a new location (do not just unzip it over the top of the old installation)
1. From the old installation, copy the `./conf`, `./data`, and optionally, the `./logs` directories to the new installation
1. If you have any custom modules, copy the `./modules/custom/` directory over as well
1. Start the bot and verify everything works and that all of your data has carried over
1. In a few rare cases, the bot may not start because the config file format changed between versions and you may need to compare your config.hjson to the template version and make changes accordingly
1. You can now delete the old installation

## Starting Tyrbot
To start the bot, run either `start.bat` or `start.sh`.

If it is your first time running the bot, or if the config.json file does not exist, it will take you through the configuration wizard to configure the bot. You will need to have a character name that you you want to run the bot as along with the username and password for the account that has that character. If you want to run this bot as an org bot, the character that the bot runs as will need to already be a member of that org.

## Support
If you need help or support with Tyrbot, join our discord channel: [https://discord.gg/2x9WesJ](https://discord.gg/2x9WesJ)

## Discord Module Setup
If you would like to connect your bot to your Discord server, follow this guide:
[https://github.com/Budabot/Tyrbot/wiki/Discord-Setup](https://github.com/Budabot/Tyrbot/wiki/Discord-Setup)
- The library used to build the module can be found [here](https://discordpy.readthedocs.io/en/latest/index.html).
- The official Discord API documentation can be found [here](https://discordapp.com/developers/docs/intro).
- The official Discord API server can be joined [here](https://discord.gg/discord-api).

## Writing Custom Modules
See the Wiki page: [https://github.com/Budabot/Tyrbot/wiki/Writing-Custom-Modules](https://github.com/Budabot/Tyrbot/wiki/Writing-Custom-Modules)
