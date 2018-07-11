class DiscordChannel(object):
    def __init__(self, channel_id, server_name, channel_name, relay_ao, relay_dc):
        self._channel_id = channel_id
        self._server_name = server_name
        self._channel_name = channel_name
        self._relay_ao = relay_ao
        self._relay_dc = relay_dc

    @property
    def channel_id(self):
        return self._channel_id

    @channel_id.setter
    def channel_id(self, value):
        self._channel_id = value

    @property
    def server_name(self):
        return self._server_name

    @server_name.setter
    def server_name(self, value):
        self._server_name = value

    @property
    def channel_name(self):
        return self._channel_name

    @channel_name.setter
    def channel_name(self, value):
        self._channel_name = value

    @property
    def relay_ao(self):
        return self._relay_ao

    @relay_ao.setter
    def relay_ao(self, value):
        self._relay_ao = value

    @property
    def relay_dc(self):
        return self._relay_dc

    @relay_dc.setter
    def relay_dc(self, value):
        self._relay_dc = value
