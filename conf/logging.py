import logging
import logging.config
import logging.handlers
import sys


class FilterInfo:
    def filter(self, rec):
        return rec.levelno <= logging.INFO


formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

file_handler = logging.handlers.RotatingFileHandler("./logs/bot.log", maxBytes=5 * 1024 * 1024 * 1024, backupCount=1000, encoding="utf-8")
file_handler.setFormatter(formatter)

console_out = logging.StreamHandler(sys.stdout)
console_out.setFormatter(formatter)
console_out.addFilter(FilterInfo())

console_err = logging.StreamHandler(sys.stderr)
console_err.setFormatter(formatter)
console_err.setLevel(logging.WARN)

logging.root.setLevel(logging.DEBUG)
logging.root.addHandler(file_handler)
logging.root.addHandler(console_out)
logging.root.addHandler(console_err)

# reduce discord spam
logging.getLogger("websockets").setLevel(logging.INFO)
