import logging
import sys


class Logger:
    console_logger = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    console_logger.setFormatter(formatter)

    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel("DEBUG")
        self.logger.addHandler(Logger.console_logger)

    def warning(self, msg):
        self.logger.warning(msg)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.logger.error(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def log_chat(self, channel, sender, msg):
        self.info("[%s] %s: %s" % (channel, sender, msg))

    def log_tell(self, direction, sender, msg):
        self.info("%s %s: %s" % (direction.capitalize(), sender, msg))
