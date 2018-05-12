from core.decorators import instance
import re
import math


@instance()
class Util:
    budatime_full_regex = re.compile("^([0-9]+[a-z]+)+$")
    budatime_unit_regex = re.compile("([0-9]+)([a-z]+)")

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

    def parse_time(self, budatime, default=0):
        unixtime = 0

        if not self.budatime_full_regex.search(budatime):
            return default

        matches = self.budatime_unit_regex.finditer(budatime)

        for match in matches:
            for time_unit in self.time_units:
                if match.group(2) in time_unit["units"]:
                    unixtime += int(match.group(1)) * time_unit["conversion_factor"]
                    continue

        return unixtime

    def time_to_readable(self, unixtime, min_unit="sec", max_unit="day", max_levels=2):
        if unixtime == 0:
            return "0 secs"

        # handle negative as positive, and add negative sign at the end
        is_negative = False
        if unixtime < 0:
            is_negative = True
            unixtime *= -1

        found_max_unit = False
        time_shift = ""
        levels = 0
        for time_unit in self.time_units:
            unit = time_unit["units"][0]

            if max_unit in time_unit["units"]:
                found_max_unit = True

            # continue to skip until we have found the max unit
            if not found_max_unit:
                continue

            unit_value = math.floor(unixtime / time_unit["conversion_factor"])

            if unit_value == 0:
                # do not show units where unit_value is 0
                pass
            elif unit_value == 1:
                # show singular where unit_value is 1
                time_shift += str(unit_value) + " " + unit + " "
            else:
                # show plural where unit_value is greater than 1
                time_shift += str(unit_value) + " " + unit + "s "

            unixtime = unixtime % time_unit["conversion_factor"]

            # record level after the first a unit has a length
            if levels or unit_value >= 1:
                levels += 1

            if levels == max_levels:
                break

            # if we have reached the min unit, then break, unless we have no output, in which case we continue
            if time_shift and min_unit in time_unit["units"]:
                break

        return ("-" if is_negative else "") + time_shift.strip()
