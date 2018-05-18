import json
import codecs


def create_new_cfg(config_file):
    config = {"username": validate_input("Account username"),
              "password": validate_input("Account password"),
              "character": validate_input("Enter the character name the bot will run on"),
              "superadmin": validate_input("Enter the name of the character you wish to be super-admin"),
              "database": {
                  "type": validate_input("Database type (sqlite or mysql)", "sqlite"),
                  "username": validate_input("Database username"),
                  "password": validate_input("Database password"),
                  "host": validate_input("Database host", "localhost"),
                  "name": validate_input("Database name", "database.db")
              },
              "server": {
                  "host": validate_input("Server Host", "chat.d1.funcom.com"),
                  "port": validate_input("Server Port", 7105, formatter=int)
              }}

    with open(config_file, "wb") as f:
        json.dump(config, codecs.getwriter("utf-8")(f), ensure_ascii=False, indent=2, sort_keys=False)


def validate_input(prompt, default=None, formatter=str):
    while True:
        if default:
            value = input(prompt + " [%s]: " % default)
        else:
            value = input(prompt + ": ")

        if value:
            return formatter(value)
        elif default:
            return default
        else:
            print("Invalid input, try again!")
