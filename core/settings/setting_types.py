from core.registry import Registry
import re


class SettingType:
    def get_name(self):
        pass

    def get_value(self):
        pass

    def get_description(self):
        pass

    def set_value(self, value):
        pass

    def get_display(self):
        pass


class TextSettingType(SettingType):
    def __init__(self, name, value, options=None):
        self.name = name
        self.set_value(value)
        self.options = options

    def get_name(self):
        return self.name

    def get_value(self):
        return self.value

    def set_value(self, value):
        if len(str(value)) > 255:
            raise Exception("Your text can not be longer than 255 characters.")
        else:
            self.value = value

    def get_display(self):
        return """For this setting you can enter any text you want (max. 255 chararacters).
To change this setting:

<highlight>/tell <myname> settings save """ + self.name + """ <i>text</i><end>"""


class ColorSettingType(SettingType):
    def __init__(self, name, value):
        self.name = name
        self.set_value(value)

    def get_name(self):
        return self.name

    def get_value(self):
        return self.value

    def set_value(self, value):
        if re.match("^#([0-9a-fA-F]{6})$", str(value)):
            self.value = value
        else:
            raise Exception("You must enter a valid HTML color.")

    def get_display(self):
        return """For this setting you can set any Color in the HTML Hexadecimal Color Format.
You can change it manually with the command:

/tell <myname> settings save {$this->row->name} <i>HTML-Color</i>

Or you can choose one of the following Colors

Red: <font color='#ff0000'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #ff0000'>Save it</a>)
White: <font color='#FFFFFF'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #FFFFFF'>Save it</a>)
Grey: <font color='#808080'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #808080'>Save it</a>)
Light Grey: <font color='#DDDDDD'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #DDDDDD'>Save it</a>)
Dark Grey: <font color='#9CC6E7'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #9CC6E7'>Save it</a>)
Black: <font color='#000000'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #000000'>Save it</a>)
Yellow: <font color='#FFFF00'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #FFFF00'>Save it</a>)
Blue: <font color='#8CB5FF'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #8CB5FF'>Save it</a>)
Deep Sky Blue: <font color='#00BFFF'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #00BFFF'>Save it</a>)
Green: <font color='#00DE42'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #00DE42'>Save it</a>)
Orange: <font color='#FCA712'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #FCA712'>Save it</a>)
Gold: <font color='#FFD700'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #FFD700'>Save it</a>)
Deep Pink: <font color='#FF1493'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save {$this->row->name} #FF1493'>Save it</a>)
Violet: <font color='#EE82EE'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #EE82EE'>Save it</a>)
Brown: <font color='#8B7355'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #8B7355'>Save it</a>)
Cyan: <font color='#00FFFF'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #00FFFF'>Save it</a>)
Navy Blue: <font color='#000080'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #000080'>Save it</a>)
Dark Orange: <font color='#FF8C00'>Example Text</font> (<a href='chatcmd:///tell <myname> settings save """ + self.name + """ #FF8C00'>Save it</a>)"""

    def get_font_color(self):
        return "<font color='%s'>" % self.value


class NumberSettingType(SettingType):
    def __init__(self, name, value, options=None):
        self.name = name
        self.set_value(value)
        self.options = options

    def get_name(self):
        return self.name

    def get_value(self):
        return int(self.value)

    def set_value(self, value):
        if re.match("^\d+$", str(value)):
            self.value = value
        else:
            raise Exception("You must enter a positive integer for this setting.")

    def get_display(self):
        return """For this setting you can set any positive integer.
To change this setting:

<highlight>/tell <myname> settings save """ + self.name + """ <i>number</i><end>"""


class TimeSettingType(SettingType):
    def __init__(self, name, value):
        self.name = name
        self.set_value(value)

    def get_name(self):
        return self.name

    def get_value(self):
        return int(self.value)

    def set_value(self, value):
        util = Registry.get_instance("util")
        time = util.parse_time(value)
        if time > 0:
            self.value = time
        else:
            raise Exception("You must enter time in a valid Budatime format")

    def get_display(self):
        return """For this setting you must enter a time value. See <a href='chatcmd:///tell <myname> help budatime'>budatime</a> for info on the format of the 'time' parameter.

To change this setting:

<highlight>/tell <myname> settings save """ + self.name + """ <i>time</i><end>"""
