from core.dict_object import DictObject

config = DictObject({
  "superadmin": "",

  "database": {
    "type": "sqlite",
    "username": "",
    "password": "",
    "host": "",
    "port": 3306,
    "name": "database.db",
  },

  "bots": [
    {
      "username": "",
      "password": "",
      "character": "",
      "is_main": True,
    }
  ],

  # do not modify below this line unless you know what you are doing
  "server": {
    "dimension": 5,  # 6 for RK2019
    "host": "chat.d1.funcom.com",
    "port": 7105,  # 7106 for RK2019
  },

  "features": {
    "text_formatting_v2": False,              # when enabled, uses an alternate text formatting implementation (not recommended)
    "use_tower_api": True,                    # when enabled, will use the Tower API configured in the bot rather than the bot's local database (recommended)
    "force_large_messages_from_slaves": True, # when enabled, the bot will send large tell messages from multiple slave bots rather than the main bot
    "ignore_failed_bots_on_login": False,     # when enabled, the bot will continue logging in even if some of the bots in the config fail, as long as the login for the first bot in the config succeeds
    "auto_unfreeze_accounts": True,           # when enabled, the bot will automatically unfreeze bot accounts by logging into the Funcom website
  },

  "module_paths": [
    "modules/core",     # core modules necessary for running/configuring/managing the bot
    "modules/standard", # standard modules for managing an org, and other common functions such as looking up items
    "modules/custom",   # custom, user-provided, or third-party modules should be put in this directory
  ]
})
