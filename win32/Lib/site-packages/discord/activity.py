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

from .enums import ActivityType, try_enum

__all__ = ('Activity', 'Streaming', 'Game')

"""If curious, this is the current schema for an activity.

It's fairly long so I will document it here:

All keys are optional.

state: str (max: 128),
details: str (max: 128)
timestamps: dict
    start: int (min: 1)
    end: int (min: 1)
assets: dict
    large_image: str (max: 32)
    large_text: str (max: 128)
    small_image: str (max: 32)
    small_text: str (max: 128)
party: dict
    id: str (max: 128),
    size: List[int] (max-length: 2)
        elem: int (min: 1)
secrets: dict
    match: str (max: 128)
    join: str (max: 128)
    spectate: str (max: 128)
instance: bool
application_id: str
name: str (max: 128)
url: str
type: int
"""

class _ActivityTag:
    __slots__ = ()

class Activity(_ActivityTag):
    """Represents an activity in Discord.

    This could be an activity such as streaming, playing, listening
    or watching.

    For memory optimisation purposes, some activities are offered in slimmed
    down versions:

    - :class:`Game`
    - :class:`Streaming`

    Attributes
    ------------
    state: str
        The user's current state. For example, "In Game".
    details: str
        The detail of the user's current activity.
    timestamps: dict
        A dictionary of timestamps.
    assets: dict
        large_image: str (max: 32)
        large_text: str (max: 128)
        small_image: str (max: 32)
        small_text: str (max: 128)
    party: dict
        id: str (max: 128),
        size: List[int] (max-length: 2)
            elem: int (min: 1)
    secrets: dict
        match: str (max: 128)
        join: str (max: 128)
        spectate: str (max: 128)
    instance: bool
    application_id: str
    name: str (max: 128)
    url: str
    type: int
    """

    __slots__ = ('state', 'details', 'timestamps', 'assets', 'party',
                 'secrets', 'instance', 'type', 'name', 'url', 'application_id')

    def __init__(self, **kwargs):
        self.state = kwargs.pop('state', None)
        self.details = kwargs.pop('details', None)
        self.timestamps = kwargs.pop('timestamps', {})
        self.assets = kwargs.pop('assets', {})
        self.party = kwargs.pop('party', {})
        self.secrets = kwargs.pop('secrets', {})
        self.instance = kwargs.pop('instance', None)
        self.application_id = kwargs.pop('application_id', None)
        self.name = kwargs.pop('name', None)
        self.url = kwargs.pop('url', None)
        self.type = try_enum(ActivityType, kwargs.pop('type', -1))

    def to_dict(self):
        ret = {}
        for attr in self.__slots__:
            value = getattr(self, attr, None)
            if value is None:
                continue

            if isinstance(value, dict) and len(value) == 0:
                continue

            ret[attr] = value
        return ret

class Game(_ActivityTag):
    """A slimmed down version of :class:`Activity` that represents a Discord game.

    This is typically displayed via **Playing** on the official Discord client.

    .. container:: operations

        .. describe:: x == y

            Checks if two games are equal.

        .. describe:: x != y

            Checks if two games are not equal.

        .. describe:: hash(x)

            Returns the game's hash.

        .. describe:: str(x)

            Returns the game's name.

    Attributes
    -----------
    name: str
        The game's name.
    """

    __slots__ = ('name')

    def __init__(self, name):
        self.name = name

    @property
    def type(self):
        """Returns the game's type. This is for compatibility with :class:`Activity`.

        It always returns :attr:`ActivityType.playing`.
        """
        return ActivityType.playing

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return '<Game name={0.name!r}>'.format(self)

    def to_dict(self):
        return {
            'type': ActivityType.playing.value,
            'name': str(self.name)
        }

    def __eq__(self, other):
        return isinstance(other, Game) and other.name == self.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.name)

class Streaming(_ActivityTag):
    """A slimmed down version of :class:`Activity` that represents a Discord streaming status.

    This is typically displayed via **Streaming** on the official Discord client.

    .. container:: operations

        .. describe:: x == y

            Checks if two streams are equal.

        .. describe:: x != y

            Checks if two streams are not equal.

        .. describe:: hash(x)

            Returns the stream's hash.

        .. describe:: str(x)

            Returns the stream's name.

    Attributes
    -----------
    name: str
        The stream's name.
    url: str
        The stream's URL. Currently only twitch.tv URLs are supported. Anything else is silently
        discarded.
    """

    __slots__ = ('name', 'url')

    def __init__(self, *, name, url):
        self.name = name
        self.url = url

    @property
    def type(self):
        """Returns the game's type. This is for compatibility with :class:`Activity`.

        It always returns :attr:`ActivityType.streaming`.
        """
        return ActivityType.streaming

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return '<Streaming name={0.name!r}>'.format(self)

    def to_dict(self):
        return {
            'type': ActivityType.streaming.value,
            'name': str(self.name),
            'url': str(self.url)
        }

    def __eq__(self, other):
        return isinstance(other, Streaming) and other.name == self.name and other.url == self.url

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.name)

def create_activity(data):
    if not data:
        return None

    game_type = try_enum(ActivityType, data.get('type', -1))
    if game_type is ActivityType.playing:
        try:
            name = data['name']
        except KeyError:
            return Activity(**data)
        else:
            return Game(name=name)
    elif game_type is ActivityType.streaming:
        try:
            name, url = data['name'], data['url']
        except KeyError:
            return Activity(**data)
        else:
            return Streaming(name=name, url=url)
    return Activity(**data)
