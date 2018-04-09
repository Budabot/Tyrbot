from core.decorators import instance
import re
import math


@instance()
class Util:
    def __init__(self):
        self.time_units = [
            {
                "units": ["yr", "years", "year", "y"],
                "conversion_factor": 31536000
            },
            {
                "units": ["month", "months", "mo"],
                "conversion_factor": 2592000
            },
            {
                "units": ["week", "weeks", "w"],
                "conversion_factor": 604800
            },
            {
                "units": ["day", "days", "d"],
                "conversion_factor": 86400
            },
            {
                "units": ["hr", "hours", "hour", "hrs", "h"],
                "conversion_factor": 3600
            },
            {
                "units": ["min", "mins", "m"],
                "conversion_factor": 60
            },
            {
                "units": ["sec", "secs", "s"],
                "conversion_factor": 1
            }
        ]

    def get_handler_name(self, handler):
        return handler.__module__ + "." + handler.__qualname__

    def get_module_name(self, handler):
        handler_name = self.get_handler_name(handler)
        parts = handler_name.split(".")
        return parts[1] + "." + parts[2]

    def parse_time(self, budatime):
        unixtime = 0

        pattern = "([0-9]+)([a-z]+)"
        matches = re.finditer(pattern, budatime)

        for match in matches:
            for time_unit in self.time_units:
                if match.group(2) in time_unit["units"]:
                    unixtime += int(match.group(1)) * time_unit["conversion_factor"]

        return unixtime

    def time_to_readable(self, unixtime, show_seconds=False):
        if unixtime == 0:
            return "0 secs"

        time_shift = ""
        for time_unit in self.time_units:
            unit = time_unit["units"][0]
            if unixtime > 0:
                length = math.floor(unixtime / time_unit["conversion_factor"])
            else:
                length = math.ceil(unixtime / time_unit["conversion_factor"])

            if unit != "secs" or show_seconds or time_shift == "":
                if length > 1:
                    time_shift += str(length) + " " + unit + "s "
                elif length == 1:
                    time_shift += str(length) + " " + unit + " "

            unixtime = unixtime % time_unit["conversion_factor"]

        return time_shift.strip()
