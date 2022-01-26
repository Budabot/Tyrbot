import logging
import logging.handlers
import traceback
import re


class Logger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)

    def warning(self, msg, exc_info: Exception = None):
        self.logger.warning(msg, exc_info=exc_info)

    def info(self, msg, exc_info: Exception = None):
        self.logger.info(msg, exc_info=exc_info)

    def error(self, msg, exc_info: Exception = None):
        self.logger.error(msg, exc_info=exc_info)

    def debug(self, msg, exc_info: Exception = None):
        self.logger.debug(msg, exc_info=exc_info)

    def log_chat(self, conn, channel, sender, msg):
        if sender:
            self.info("(%s) [%s] %s: %s" % (conn.id, channel, sender, self.format_chat_message(msg)))
        else:
            self.info("(%s) [%s] %s" % (conn.id, channel, self.format_chat_message(msg)))

    def log_tell(self, conn, direction, sender, msg):
        self.info("(%s) %s %s: %s" % (conn.id, direction.capitalize(), sender, self.format_chat_message(msg)))

    def format_chat_message(self, msg):
        msg = re.sub(r"<a\s+href=\".+?[^\\]\">", "[link]", msg, 0, re.UNICODE | re.DOTALL)
        msg = re.sub(r"<a\s+href='.+?'>", "[link]", msg, 0, re.UNICODE | re.DOTALL)
        msg = re.sub(r"<font\s+.+?>", "", msg, 0, re.UNICODE)
        msg = re.sub("</font>", "", msg, 0, re.UNICODE)
        msg = re.sub("</a>", "[/link]", msg, 0, re.UNICODE)
        return msg

    def format_message(self, msg, obj):
        if obj:
            return msg + "\n" + traceback.format_exc()
        else:
            return msg
