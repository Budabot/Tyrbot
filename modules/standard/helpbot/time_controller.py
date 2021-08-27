from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any, NamedFlagParameters
from datetime import datetime
import pytz
import time


@instance()
class TimeController:
    def __init__(self):
        self.time_format = "%Y-%m-%d %H:%M:%S %Z%z"

    @command(command="time", params=[NamedFlagParameters(["all_timezones"])], access_level="all",
             description="Show the current time")
    def time_cmd(self, request, flag_params):
        dt = datetime.now()
        t = int(time.time())

        if not flag_params.all_timezones:
            return "The current time is <highlight>%s</highlight> [%d]." % (dt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S %Z"), t)
        else:
            blob = "Unixtime => %d\n\n" % t
            current_region = ""
            for tz in pytz.common_timezones:
                result = tz.split("/", 2)
                if len(result) == 2:
                    region, city = result
                else:
                    region = result[0]
                    city = result[0]

                if current_region != region:
                    blob += "\n<pagebreak><header2>%s</header2>\n" % region
                    current_region = region

                blob += "%s => %s\n" % (city, dt.astimezone(pytz.timezone(tz)).strftime(self.time_format))

            return ChatBlob("Timezones", blob)

    @command(command="time", params=[Any("timezone")], access_level="all",
             description="Show time for the specified timezone")
    def time_zone_cmd(self, request, timezone_str):
        timezone_str = timezone_str.lower()
        for tz in pytz.common_timezones:
            if tz.lower() == timezone_str:
                return "%s => %s" % (tz, datetime.now(tz=pytz.timezone(tz)).strftime(self.time_format))

        return f"Unknown timezone <highlight>{timezone_str}</highlight>. Use <highlight><symbol>time --all_timezones</highlight> to see a list of timezones."
