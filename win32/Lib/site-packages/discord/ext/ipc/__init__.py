# -*- coding: utf-8 -*-

"""
discord.ext.ipc
~~~~~~~~~~~~~~~~~~~~~

An extension module to help with Interprocess Communication (IPC)

:copyright: (c) 2017 Rapptz
:license: MIT, see LICENSE for more details.
"""

from .errors import *
from .client import Client
from .server import Handler, Server
from .protocol import Protocol
