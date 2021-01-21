import hjson

from core.decorators import instance
from core.event_service import EventService
from core.logger import Logger
from core.setting_service import SettingService
from core.setting_types import TextSettingType
from core.tyrbot import Tyrbot
from core.util import Util


@instance()
class TranslationService:
    strings = {}
    translation_callbacks = {}
    language = None
    lang_codes = ["en_US", "de_DE"]
    LANGUAGE_SETTING = "language"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.event_service: EventService = registry.get_instance("event_service")
        self.util: Util = registry.get_instance("util")
        self.bot: Tyrbot = registry.get_instance("bot")

    def pre_start(self):
        self.event_service.register_event_type("reload_translation")

    def start(self):
        self.setting_service.register_new("core.system", self.LANGUAGE_SETTING, "en_US", TextSettingType(self.lang_codes), "Language of the Bot")

        self.language = self.setting_service.get_value(self.LANGUAGE_SETTING)
        self.register_translation("global", self.load_global_msg)
        self.setting_service.register_change_listener(self.LANGUAGE_SETTING, self.language_setting_changed)

    def register_translation(self, category, callback):
        """Call during start"""
        if self.translation_callbacks.get(category) is None:
            self.translation_callbacks[category] = []
        self.translation_callbacks[category].append(callback)
        self.update_msg(category, callback)

    def load_global_msg(self):
        with open("core/global.msg", mode="r", encoding="UTF-8") as f:
            return hjson.load(f)

    def language_setting_changed(self, name, old_value, new_value):
        if name == self.LANGUAGE_SETTING and new_value != old_value:
            self.reload_translation(new_value)

    # This method will load another language, defined in the param 'lang'
    def reload_translation(self, lang):
        self.event_service.fire_event("reload_translation")
        self.language = lang
        for k1 in self.strings:
            for callback in self.translation_callbacks.get(k1):
                self.update_msg(k1, callback)

    #updates the msgs
    def update_msg(self, category, callback):
        data = callback()
        for k in data:
            if not category in self.strings:
                self.strings[category] = {}
            self.strings[category][k] = data[k].get(self.language) or data[k].get("en_US")

    #
    # the param 'variables' accepts dictionaries ONLY.
    #
    def get_response(self, category, key, variables={}):
        msg = ""
        try:
            val = self.strings[category][key]
            if isinstance(val, list):
                for line in val:
                    msg += line.format(**variables)
            else:
                msg = val.format(**variables)
        except KeyError as e:
            self.logger.error(f"translating error category '{category}' and key '{key}' with params: {variables}", e)
            msg = "Error translating category: <highlight>{mod}</highlight> key: <highlight>{key}</highlight>" \
                  " with params: <highlight>{params}</highlight>".format(mod=category, key=key, params=variables)
        finally:
            return msg
