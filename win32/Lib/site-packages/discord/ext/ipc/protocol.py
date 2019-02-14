# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2015-2017 Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import discord.compat
import logging
import asyncio
import struct
import json

log = logging.getLogger(__name__)

def json_dump(o):
    x = json.dumps(o)
    return bytes(x, encoding='utf-8')

def json_load(o):
    return json.loads(str(o, encoding='utf-8'))

class Protocol:
    handshake_timeout = 20

    PACKET_SIZE_STRUCT = struct.Struct('>I')

    def __init__(self, *, loop=None, reader=None, writer=None, loader=json_load, dumper=json_dump):
        self.loop = loop or asyncio.get_event_loop()

        # these could be initialized later
        self.reader = reader
        self.writer = writer

        self.loader = loader
        self.dumper = dumper

        self._runner_task = None

    @asyncio.coroutine
    def send(self, op, data, *, drain=False):
        dumped = self.dumper({ 'op': op, 'd': data })
        packet = self.PACKET_SIZE_STRUCT.pack(len(dumped)) + dumped
        self.writer.write(packet)

        if drain:
            yield from self.writer.drain()

    @asyncio.coroutine
    def recv(self):
        to_read = yield from self.reader.readexactly(self.PACKET_SIZE_STRUCT.size)
        packet_length, = self.PACKET_SIZE_STRUCT.unpack(to_read)
        packet = yield from self.reader.readexactly(packet_length)
        data = self.loader(packet)
        return data['op'], data['d']

    @asyncio.coroutine
    def expect_any_of(self, *opcodes):
        op, data = yield from self.recv()
        if opcodes and op not in opcodes:
            raise ValueError('Expected %r opcodes but received %r instead' % (opcodes, op))

        return op, data

    @asyncio.coroutine
    def handshake(self):
        raise NotImplementedError()

    def get_info(self):
        raise NotImplementedError()

    @asyncio.coroutine
    def _runner(self):
        close_reason = None

        try:
            yield from self.handle_ready(self.remote_info)

            while True:
                op, data = yield from self.recv()

                log.debug('Received opcode (%s) with %r', op, data)
                try:
                    handler = getattr(self, 'handle_' + op)
                except AttributeError:
                    log.info('unhandled upcode (%s) with %r', op, data)
                else:
                    yield from handler(data)

        except asyncio.IncompleteReadError:
            close_reason = 'Incomplete read'
        except asyncio.TimeoutError:
            close_reason = 'An operation timed out'
        except asyncio.CancelledError:
            close_reason = 'A future was cancelled'
        except Exception as e:
            close_reason = str(e)
        finally:
            self._runner_task.set_result(close_reason)
            yield from self.handle_close(close_reason)

    def _run(self):
        self._runner_task = discord.compat.create_task(self._runner(), loop=self.loop)
        return self._runner_task

    def is_running(self):
        t = self._runner_task
        return t is not None and not t.done()

    @asyncio.coroutine
    def handle_ready(self, remote_info):
        pass

    @asyncio.coroutine
    def handle_close(self, readon):
        pass

    @asyncio.coroutine
    def start(self):
        try:
            self.remote_info = yield from asyncio.wait_for(self.handshake(), self.handshake_timeout, loop=self.loop)
            yield from self._run()
        finally:
            self.writer.close()
