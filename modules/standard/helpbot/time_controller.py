from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any
from datetime import datetime
import pytz
import time


@instance()
class TimeController:
    def __init__(self):
        self.time_format = "%Y-%m-%d %H:%M:%S %Z%z"

    @command(command="time", params=[], access_level="all",
             description="Show the current time in every timezone")
    def time_cmd(self, request):
        blob = "Unixtime => %d\n\n" % int(time.time())
        current_region = ""
        dt = datetime.now()
        for tz in pytz.common_timezones:
            result = tz.split("/", 2)
            if len(result) == 2:
                region, city = result
            else:
                region = result[0]
                city = result[0]

            if current_region != region:
                blob += "\n<pagebreak><header2>%s<end>\n" % region
                current_region = region

            blob += "%s => %s\n" % (city, dt.astimezone(pytz.timezone(tz)).strftime(self.time_format))

        return ChatBlob("Timezones", blob)

    @command(command="time", params=[Any("timezone")], access_level="all",
             description="Show time for the specified timezone")
    def time_zone_cmd(self, request, timezone_str):
        timezone_str = timezone_str.lower()
        for tz in pytz.common_timezones:
            if tz.lower() == timezone_str:
                reply("%s => %s" % (tz, datetime.now(tz=pytz.timezone(tz)).strftime(self.time_format)))
                return
        return "Unknown timezone."
