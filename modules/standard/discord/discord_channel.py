
class DiscordChannel(object):
    def __init__(self, channelid, servername, channelname, relay_ao, relay_dc):
        self._channelid = channelid
        self._servername = servername
        self._channelname = channelname
        self._relay_ao = relay_ao
        self._relay_dc = relay_dc

    @property
    def channelid(self):
        return self._channelid
    @channelid.setter
    def channelid(self, value):
        self._channelid = value
    @property
    def servername(self):
        return self._servername
    @servername.setter
    def servername(self, value):
        self._servername = value
    @property
    def channelname(self):
        return self._channelname
    @channelname.setter
    def channelname(self, value):
        self._channelname = value
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