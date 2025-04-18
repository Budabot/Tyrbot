# Tyrbot

Tyrbot is an in-game chatbot for the MMORPG Anarchy Online released by Funcom in 2001.

This is a rewrite of [Budabot](https://github.com/Budabot/Budabot) in Python 3.

## Quickstart

1. Download the bot: https://github.com/Budabot/Tyrbot/archive/master.zip
1. Unzip the bot to a location on your computer
1. Run `start.bat`
1. The first time you run the bot it will ask some questions. You will need four pieces of information: username, password, character name, and superadmin. For any other question you can simply press &lt;Enter&gt; to use the default value. 

## Requirements

Tyrbot has been tested on Python 3.12. You may run into issues with other versions of Python.

## Installation

Currently there are no releases for Tyrbot but you can download the bot from here which will always have the very latest changes: https://github.com/Budabot/Tyrbot/archive/master.zip

Then simply unzip the bot somewhere before starting it.

## Upgrade

If you are already running Tyrbot and simply want to upgrade to the latest version, follow these steps:

1. Download the latest version from here: https://github.com/Budabot/Tyrbot/archive/master.zip
1. Unzip the bot to a new location (do not just unzip it over the top of the old installation)
1. From the old installation, copy the `./conf`, `./data`, and optionally, the `./logs` directories to the new installation
1. If you have any custom modules, copy the `./modules/custom/` directory over as well
1. Start the bot and verify that everything works and that all of your data has carried over
1. In a few rare cases, the bot may not start because the config file format changed between versions and you may need to compare your `conf/config.py` file to the template version (`conf/config_template.py`) and make changes accordingly
1. You can now delete the old installation

## Starting Tyrbot

To start the bot, run either `start.bat` (Windows) or `start.sh` (Linux).

If it is your first time running the bot, or if the config.py file does not exist, it will take you through the configuration wizard to configure the bot. You will need to have a character that the bot will run as along with the username and password for the account that has that character. If you want to run this bot as an org bot, that character will need to already be a member of that org.

## Support

If you need help or support with Tyrbot, join our discord channel: https://discord.gg/2x9WesJ

## Discord Module Setup

If you would like to connect your bot to your Discord server, follow this guide: https://github.com/Budabot/Tyrbot/wiki/Discord-Setup

- The library used to build the module can be found https://discordpy.readthedocs.io/en/latest/index.html.
- The official Discord API documentation can be found https://discordapp.com/developers/docs/intro.
- The official Discord API server can be joined at https://discord.gg/discord-api.

## Writing Custom Modules

See the Wiki page: https://github.com/Budabot/Tyrbot/wiki/Writing-Custom-Modules

## Running in Docker

See the Wiki page: https://github.com/Budabot/Tyrbot/wiki/Docker
