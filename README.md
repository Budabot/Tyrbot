# Tyrbot

Tyrbot is an in-game chatbot for the MMORPG Anarchy Online released by Funcom in 2001.

This is a rewrite of [Budabot](https://github.com/Budabot/Budabot) in Python 3.

# Experimental Features
1. Running on Python 3.9.1 (when run with Docker)
2. Threading support (command handling is now scheduled on a thread pool instead of the main thread)

## Requirements

Tyrbot requires Python 3.6.  Neither Python 3.5 or Python 3.7 will work.  We are working on adding support for Python 3.7.

## Installation

Tyrbot is now ready for general use and is recommended over Budabot or any other bot for all new installations.

Currently there are no releases for Tyrbot but you can download the bot from here which will always have the very latest changes: https://github.com/Budabot/Tyrbot/archive/master.zip

Then simply unzip the bot somewhere before starting it.

## Upgrade

If you are running a version of Tyrbot and simply want to upgrade to the latest version, follow these steps:

1. Download the latest version from here: https://github.com/Budabot/Tyrbot/archive/master.zip
1. Unzip the bot to a new location (do not just unzip it over the top of the old installation)
1. From the old installation, copy the `./conf`, `./data`, and optionally, the `./logs` directories to the new installation
1. If you have any custom modules, copy the `./modules/custom/` directory over as well
1. Start the bot and verify everything works and that all of your data has carried over
1. In a few rare cases, the bot may not start because the config file format changed between versions and you may need to compare your config.hjson to the template version and make changes accordingly
1. You can now delete the old installation

If you want to upgrade from Budabot, follow the instructions here: https://github.com/Budabot/Tyrbot/wiki/Migrating-From-Budabot

## Starting Tyrbot

To start the bot, run either `start.bat` or `start.sh`.

If it is your first time running the bot, or if the config.json file does not exist, it will take you through the configuration wizard to configure the bot. You will need to have a character name that you you want to run the bot as along with the username and password for the account that has that character. If you want to run this bot as an org bot, the character that the bot runs as will need to already be a member of that org.

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

Example:
```bash
docker run -d --restart=always -v /path/on/host/data:/app/data -e TYRBOT_USERNAME="username" -e TYRBOT_PASSWORD="password" -e TYRBOT_CHARACTER="bot_character" -e TYRBOT_SUPERADMIN="your_character" tyrbot:latest
```
Note: The container puts the Tyrbot files in /app

Other mounts you may want:
`-v /path/on/host/logs:/app/logs` for capturing logs
`-v /path/on/host/conf:/app/conf` for specifying a config file or overriding logging configuration

You can choose to mount a config file into the container, or set the config values through ENV vars. All ENV vars should start with "TYRBOT_", be in all capital letters, and use underscore (`_`) to denote a sub category in the config (ex: TYRBOT_DATABASE_TYPE=sqlite).  The bot will ignore your config file if any "TYRBOT_*" ENV vars have been set. If you need to override the `module_paths` value then you must mount a `conf/config.hjson` file as there is no way to set that via ENV vars.

You may also wish to disable logging to the file system by mounting a custom `conf/logging.py` file.

You can also look at our guide for using docker-compose to manage a Docker container running Tyrbot: https://github.com/Budabot/Tyrbot/wiki/Running-Tyrbot-with-Docker-Compose
