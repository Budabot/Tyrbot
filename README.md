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
1. From the old installation, copy the `/conf`, `/data`, and optionally, the `/logs` directories to the new installation
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


## Writing custom modules
You put all your own modules in the `/modules/custom/` folder, this way they don't conflict with the built in ones and it makes upgrading them easy.


### Example of creating a custom module
- Create a the folder `/modules/custom/my_services/`
- In `/modules/custom/my_services/` create a file called `my_services_controller.py` with the following code:

```
from core.chat_blob import ChatBlob
from core.command_param_types import Character
from core.decorators import instance, command


@instance()
class MyServicesController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.text = registry.get_instance("text")
        self.info_controller = registry.get_instance("info_controller")

    @command(command="ad", params=[Character("name")], access_level="admin",
             description="Send my services to a character")
    def ad_cmd(self, request, char):
        if not char.char_id:
            return "Could not find <highlight>%s<end>." % char.name
        else:
            services_info = self.info_controller.get_topic_info("services")
            if not services_info:
                return "Error retrieving services info."

            blob = ChatBlob("services", services_info)
            msg = "Thanks for visiting <myname>. I provide other " + self.text.paginate(blob, 10000, 1)[0]
            self.bot.send_private_message(char.char_id, msg)
```

- Restart the server and the module should work (the command could be called with `/tell bot !ad SomeName`)
