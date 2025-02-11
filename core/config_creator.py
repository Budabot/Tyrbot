def create_new_cfg(config_file, template_config):
    config = {
        "superadmin": validate_input("Enter the name of the character you wish to be superadmin"),
        "bots": [
            {
                "username": validate_input("Account username"),
                "password": validate_input("Account password"),
                "character": validate_input("Enter the name of the character the bot will run on"),
                "is_main": True
            }
        ],
        "database": {
            "type": validate_input("Database type (sqlite or mysql)", "sqlite"),
            "username": validate_input("Database username (leave default for SQLite)", ""),
            "password": validate_input("Database password (leave default for SQLite)", ""),
            "host": validate_input("Database host (leave default for SQLite)", "localhost"),
            "port": validate_input("Database port (leave default for SQLite)", 3306, formatter=int),
            "name": validate_input("Database name (leave default for SQLite)", "database.db")
        },
        "server": {
            "dimension": validate_input("Server Dimension (Enter '5' for Rubi-Ka, '6' for RK2019)", "5", formatter=int),
            "host": validate_input("Server Host (use default for both servers)", "chat.d1.funcom.com"),
            "port": validate_input("Server Port (enter 7105 for Rubi-Ka, and 7106 for RK2019)", 7105, formatter=int)
        }
    }

    template_config.update(config)

    with open(config_file, mode="wb") as f:
        f.write(b"from core.dict_object import DictObject\n\n")
        f.write(b"config = DictObject(")
        f.write(pretty_printer(template_config).encode("utf-8"))
        f.write(b")\n")


def validate_input(prompt, default=None, formatter=str):
    while True:
        if default is not None:
            value = input(prompt + " [%s]: " % default)
        else:
            value = input(prompt + ": ")

        if value:
            return formatter(value)
        elif default is not None:
            return default
        else:
            print("Invalid input!")


def pretty_printer(obj, indent=4):
    indent_progession = 4
    spaces = indent * " "
    end_spaces = (indent - indent_progession) * " "
    if isinstance(obj, dict):
        result = ",".join(map(lambda item: "\n" + spaces + pretty_printer(item[0], indent + indent_progession) + ": " + pretty_printer(item[1], indent + indent_progession), obj.items()))
        return "{" + result + f"\n{end_spaces}}}"
    elif isinstance(obj, list):
        result = ",".join(map(lambda item: "\n" + spaces + pretty_printer(item, indent + indent_progession), obj))
        return "[" + result + f"\n{end_spaces}]"
    elif isinstance(obj, str):
        return f"\"{obj}\""
    else:
        return str(obj)
