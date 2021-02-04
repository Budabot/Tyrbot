from enum import Enum


class BotStatus(Enum):
    SHUTDOWN = 0
    RUN = 1
    RESTART = 2
    ERROR = 4
