#  Relevant parts of original copyright notice of AOChat.php:

# Copyright (C) 2005 by Jürgen A. Erhard
# Copyright (C) 2002-2004  Oskari Saarenmaa <auno@auno.org>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA


import random
import struct
import socket

# This is 'half' Diffie-Hellman key exchange.
# 'Half' as in we already have the server's key ($dhY)
# $dhN is a prime and $dhG is generator for it.
#
# http://en.wikipedia.org/wiki/Diffie-Hellman_key_exchange


def generate_login_key(server_key, username, password):
    dhY = 0x9c32cc23d559ca90fc31be72df817d0e124769e809f936bc14360ff4bed758f260a0d596584eacbbc2b88bdd410416163e11dbf62173393fbc0c6fefb2d855f1a03dec8e9f105bbad91b3437d8eb73fe2f44159597aa4053cf788d2f9d7012fb8d7c4ce3876f7d6cd5d0c31754f4cd96166708641958de54a6def5657b9f2e92
    dhN = 0xeca2e8c85d863dcdc26a429a71a9815ad052f6139669dd659f98ae159d313d13c6bf2838e10a69b6478b64a24bd054ba8248e8fa778703b418408249440b2c1edd28853e240d8a7e49540b76d120d3b1ad2878b1b99490eb4a2a5e84caa8a91cecbdb1aa7c816e8be343246f80c637abc653b893fd91686cf8d32d6cfe5f2a6f
    dhG = 0x5
    dhx = random.randrange(0, 2**256)

    dhX = pow(dhG, dhx, dhN)
    dhK = pow(dhY, dhx, dhN)

    dhK = "%x" % dhK
    if len(dhK) > 32:
        dhK = dhK[:32]

    dhK = eval("0x" + dhK)

    challenge = "%s|%s|%s" % (username, server_key, password)

    # prefix is an 8 bytes of randomness
    prefix_bytes = random.randrange(0, 2**64)
    prefix = struct.pack(">Q", prefix_bytes)

    length = 8 + 4 + len(challenge)  # prefix, int, ...
    pad = " " * ((8 - length % 8) % 8)
    challenge_len = struct.pack(">I", len(challenge))

    plain = prefix + challenge_len + challenge.encode('ascii') + pad.encode('ascii')
    crypted = aochat_crypt(dhK, plain)

    if not crypted:
        raise Exception("encryption failed")

    return ("%0x" % dhX) + "-" + crypted


def aochat_crypt(key, data):
    if len(data) % 8 != 0:
        raise Exception(f"length expected % 8 = 0, actual length: {len(data)}")

    cycle = [0, 0]
    result = [0, 0]
    ret = ""

    key_arr = [socket.ntohl(int(s, 16)) for s in struct.unpack("8s" * (len("%s" % key) // 8), ("%x" % key).encode('ascii'))]
    data_arr = struct.unpack("I" * (len(data) // 4), data)

    i = 0
    while i < len(data_arr):
        cycle[0] = data_arr[i] ^ result[0]
        cycle[1] = data_arr[i+1] ^ result[1]
        result = aochat_tea_encrypt(cycle, key_arr)

        p = "%08x%08x" % (socket.htonl(result[0]) & 0xffffffff, socket.htonl(result[1]) & 0xffffffff)

        ret += p

        i += 2

    return ret


def aochat_tea_encrypt(cycle, key):
    a, b = cycle
    total = 0
    delta = 0x9e3779b9
    i = 32

    while i:
        total = (total + delta) & 0xffffffff
        a += (((b << 4 & 0xfffffff0) + key[0]) ^ (b + total) ^ ((b >> 5 & 0x7ffffff) + key[1])) & 0xffffffff
        a &= 0xffffffff
        b += (((a << 4 & 0xfffffff0) + key[2]) ^ (a + total) ^ ((a >> 5 & 0x7ffffff) + key[3])) & 0xffffffff
        b &= 0xffffffff
        i -= 1

    return a, b
