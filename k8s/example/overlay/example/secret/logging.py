import logging
import logging.config
import logging.handlers
import sys


class FilterInfo:
    def filter(self, rec):
        return rec.levelno <= logging.INFO


formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

console_out = logging.StreamHandler(sys.stdout)
console_out.setFormatter(formatter)
console_out.addFilter(FilterInfo())

console_err = logging.StreamHandler(sys.stderr)
console_err.setFormatter(formatter)
console_err.setLevel(logging.WARN)

# reduce discord spam
logging.getLogger("websockets").setLevel(logging.INFO)
