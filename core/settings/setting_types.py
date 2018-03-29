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
    def __init__(self, name, value, description, options=None):
        self.name = name
        self.set_value(value)
        self.description = description
        self.options = options

    def get_name(self):
        return self.name

    def get_value(self):
        return self.value

    def get_description(self):
        return self.description

    def set_value(self, value):
        if len(str(value)) > 255:
            raise Exception("Your text can not be longer than 255 characters.")
        else:
            self.value = value

    def get_display(self):
        return """For this setting you can enter any text you want (max. 255 chararacters).
To change this setting:

<highlight>/tell <myname> config setting """ + self.name + """ <i>text</i><end>"""


class ColorSettingType(SettingType):
    def __init__(self, name, value, description):
        self.name = name
        self.set_value(value)
        self.description = description

    def get_name(self):
        return self.name

    def get_value(self):
        return self.value

    def get_description(self):
        return self.description

    def set_value(self, value):
        if re.match("^#([0-9a-fA-F]{6})$", str(value)):
            self.value = value
        else:
            raise Exception("You must enter a valid HTML color.")

    def get_display(self):
        return """For this setting you can set any Color in the HTML Hexadecimal Color Format.
You can change it manually with the command:

/tell <myname> config setting """ + self.name + """ <i>HTML-Color</i>

Or you can choose one of the following colors

<font color='#ff0000'>Red</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #ff0000'>Save it</a>)
<font color='#FFFFFF'>White</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #FFFFFF'>Save it</a>)
<font color='#808080'>Grey</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #808080'>Save it</a>)
<font color='#DDDDDD'>Light Grey</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #DDDDDD'>Save it</a>)
<font color='#9CC6E7'>Dark Grey</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #9CC6E7'>Save it</a>)
<font color='#000000'>Black</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #000000'>Save it</a>)
<font color='#FFFF00'>Yellow</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #FFFF00'>Save it</a>)
<font color='#8CB5FF'>Blue</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #8CB5FF'>Save it</a>)
<font color='#00BFFF'>Deep Sky Blue</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #00BFFF'>Save it</a>)
<font color='#00DE42'>Green</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #00DE42'>Save it</a>)
<font color='#FCA712'>Orange</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #FCA712'>Save it</a>)
<font color='#FFD700'>Gold</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #FFD700'>Save it</a>)
<font color='#FF1493'>Deep Pink</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #FF1493'>Save it</a>)
<font color='#EE82EE'>Violet</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #EE82EE'>Save it</a>)
<font color='#8B7355'>Brown</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #8B7355'>Save it</a>)
<font color='#00FFFF'>Cyan</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #00FFFF'>Save it</a>)
<font color='#000080'>Navy Blue</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #000080'>Save it</a>)
<font color='#FF8C00'>Dark Orange</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ #FF8C00'>Save it</a>)"""

    def get_font_color(self):
        return "<font color='%s'>" % self.value


class NumberSettingType(SettingType):
    def __init__(self, name, value, description, options=None):
        self.name = name
        self.set_value(value)
        self.description = description
        self.options = options

    def get_name(self):
        return self.name

    def get_value(self):
        return int(self.value)

    def get_description(self):
        return self.description

    def set_value(self, value):
        if re.match("^\d+$", str(value)):
            self.value = value
        else:
            raise Exception("You must enter a positive integer for this setting.")

    def get_display(self):
        return """For this setting you can set any positive integer.
To change this setting:

<highlight>/tell <myname> config setting """ + self.name + """ <i>number</i><end>"""


class TimeSettingType(SettingType):
    def __init__(self, name, value, description):
        self.name = name
        self.set_value(value)
        self.description = description

    def get_name(self):
        return self.name

    def get_value(self):
        return int(self.value)

    def get_description(self):
        return self.description

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

<highlight>/tell <myname> config setting """ + self.name + """ <i>time</i><end>"""
