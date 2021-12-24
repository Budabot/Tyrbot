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
      "is_main": True
    }
  ],

  # do not modify below this line unless you know what you are doing
  "server": {
    "dimension": 5,
    "host": "chat.d1.funcom.com",
    "port": 7105
  },

  "features": {
    "text_formatting_v2": False,
    "use_tower_api": True,
    "force_large_messages_from_slaves": True
  },

  "module_paths": [
    "modules/core",
    "modules/standard",
    "modules/custom"
  ]
})
