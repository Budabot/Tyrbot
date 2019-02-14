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

from .protocol import Protocol
from .errors import HandshakeError

import asyncio
import binascii
import hashlib
import hmac
import os

class Client(Protocol):
    def __init__(self, *, host: str, port: int, secret: str, id: str, **kwargs):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.id = str(id)
        self.secret = secret

    @asyncio.coroutine
    def handshake(self):
        self.reader, self.writer = yield from asyncio.open_connection(self.host, self.port, loop=self.loop)

        # this code here is just proving who we are
        nonce = binascii.hexlify(os.urandom(32))
        nonce_str = nonce.decode('utf-8')
        secret_as_bytes = self.secret.encode('utf-8')
        payload = self.id.encode('utf-8') + b':' + nonce
        hmac_hex = hmac.new(secret_as_bytes, payload, digestmod=hashlib.sha256).hexdigest()


        yield from self.send('auth_login', {
            'client_id': self.id,
            'client_nonce': nonce_str,
            'digest': hmac_hex
        }, drain=True)

        op, data = yield from self.expect_any_of('auth_pass', 'auth_fail')

        # server doesn't recognise us for some reason
        if op == 'auth_fail':
            raise HandshakeError(data['reason'])


        # the server gives us back our PSK as proof that it knows who we are
        server_digest = data['digest']
        server_payload = payload + b':' + hmac_hex.encode('utf-8')

        # we must verify that the PSK matches what we expect
        expected_digest = hmac.new(secret_as_bytes, server_payload, digestmod=hashlib.sha256).hexdigest()
        if not hmac.compare_digest(server_digest, expected_digest):
            yield from self.send('auth_fail', { 'reason': 'Server digest does not match' }, drain=True)
            raise HandshakeError('Server digest does not match.')

        # since we have successfully logged on, we should send the server our info (if we have any)
        yield from self.send('auth_pass', { 'info': self.get_info() }, drain=True)

        # and then return the server's info
        return data['info']

    def get_info(self):
        return {}
