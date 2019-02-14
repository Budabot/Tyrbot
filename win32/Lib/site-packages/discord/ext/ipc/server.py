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
import asyncio
import hashlib
import hmac

from .protocol import Protocol
from .errors import HandshakeError

class Handler(Protocol):
    def __init__(self, server, reader, writer, **kwargs):
        super().__init__(loop=server.loop, reader=reader, writer=writer, **kwargs)
        self.server = server
        self.id = None
        self.addr = self.writer.get_extra_info('peername')

    @asyncio.coroutine
    def handshake(self):
        # wait for login success
        _, data = yield from self.expect_any_of('auth_login')

        # clients are identified by a secret PSK and an ID.
        self.id = client_id = data['client_id']
        client_secret = self.server.get_client_secret(client_id)

        if client_secret is None:
            reason = 'Unknown Client ID: ' + client_id
            yield from self.send('auth_fail', { 'reason': reason }, drain=True)
            raise HandshakeError(reason)

        client_secret = client_secret.encode('utf-8')
        client_nonce = data['client_nonce'].encode('utf-8')
        client_digest = data['digest']
        payload = client_id.encode('utf-8') + b':' + client_nonce

        expected_digest = hmac.new(client_secret, payload, digestmod=hashlib.sha256).hexdigest()

        if not hmac.compare_digest(client_digest, expected_digest):
            reason = 'Bad secret for client ID ' + client_id
            yield from self.send('auth_fail', { 'reason': reason }, drain=True)
            raise HandshakeError(reason)

        server_payload = payload + b':' + client_digest.encode('utf-8')
        server_digest = hmac.new(client_secret, server_payload, digestmod=hashlib.sha256).hexdigest()

        to_send = { 'digest': server_digest, 'info': self.server.get_server_info(self) }
        yield from self.send('auth_pass', to_send, drain=True)

        # Ensure the client accepted our secret
        op, data = yield from self.expect_any_of('auth_pass', 'auth_fail')
        if op == 'auth_fail':
            raise HandshakeError(data['reason'])

        return data['info']

    @asyncio.coroutine
    def start(self):
        try:
            self.remote_info = yield from asyncio.wait_for(self.handshake(), self.handshake_timeout, loop=self.loop)
            yield from self.server.connect_client(self)
            yield from self._run()
        finally:
            self.writer.close()
            yield from self.server.disconnect_client(self)

class Server:
    handler = Handler

    def __init__(self, host='127.0.0.1', port=3000, *, loop=None, **kwargs):
        self.clients = set()
        self.host = host
        self.port = port
        self.server = None
        self.loop = loop or asyncio.get_event_loop()
        self._tasks = {}
        self._kwargs = kwargs

    @asyncio.coroutine
    def _accept(self, reader, writer):
        client = self.handler(self, reader=reader, writer=writer, **self._kwargs)
        self._tasks[client] = discord.compat.create_task(client.start(), loop=self.loop)

    @asyncio.coroutine
    def start(self):
        self.server = yield from asyncio.start_server(self._accept, host=self.host, port=self.port, loop=self.loop)

    def get_server_info(self, client):
        return {}

    def get_client_secret(self, client_id):
        raise NotImplementedError()

    @asyncio.coroutine
    def disconnect_client(self, client):
        try:
            self.clients.remove(client)
        except KeyError:
            pass
        else:
            t = self._tasks.pop(client, None)
            if t:
                t.cancel()

            yield from self.on_client_disconnect(client)

    @asyncio.coroutine
    def connect_client(self, client):
        self.clients.add(client)
        yield from self.on_client_connect(client)

    @asyncio.coroutine
    def on_client_connect(self, client):
        pass

    @asyncio.coroutine
    def on_client_disconnect(self, client):
        pass
