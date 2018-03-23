from core.decorators import instance
import re


@instance()
class Util:
    def __init__(self):
        self.time_units = [
            {
                "units": ["y", "yr", "year", "years"],
                "conversion_factor": 31536000
            },
            {
                "units": ["mo", "month", "months"],
                "conversion_factor": 2592000
            },
            {
                "units": ["weeks", "week", "w"],
                "conversion_factor": 604800
            },
            {
                "units": ["d", "day", "days"],
                "conversion_factor": 86400
            },
            {
                "units": ["h", "hr", "hrs", "hour", "hours"],
                "conversion_factor": 3600
            },
            {
                "units": ["m", "min", "mins"],
                "conversion_factor": 60
            },
            {
                "units": ["s", "sec", "secs"],
                "conversion_factor": 1
            }
        ]

    def get_handler_name(self, handler):
        return handler.__module__ + "." + handler.__qualname__

    def get_module_name(self, handler):
        handler_name = self.get_handler_name(handler)
        parts = handler_name.split(".")
        return parts[0] + "." + parts[1]


    def parse_time(self, budatime):
        unixtime = 0

        pattern = "([0-9]+)([a-z]+)"
        matches = re.finditer(pattern, budatime)

        for match in matches:
            for time_unit in self.time_units:
                if match.group(2) in time_unit["units"]:
                    unixtime += int(match.group(1)) * time_unit["conversion_factor"]

        return unixtime
