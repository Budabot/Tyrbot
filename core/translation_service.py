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
    language = "en_US"
    lang_codes = ["en_US", "de_DE"]

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.event_service: EventService = registry.get_instance("event_service")
        self.util: Util = registry.get_instance("util")
        self.bot: Tyrbot = registry.get_instance("bot")

    def pre_start(self):
        self.language = self.setting_service.get_value("language") or self.language
        self.event_service.register_event_type("reload_translation")

    def start(self):
        self.setting_service.register("language", "en_US", "Language of the Bot",
                                      TextSettingType(self.lang_codes), "core.system")
        self.register_translation("global", self.load_global_msg)

    def register_translation(self, category, callback):
        if self.translation_callbacks.get(category) is None:
            self.translation_callbacks[category] = []
        self.translation_callbacks[category].append(callback)
        self.update_msg(category, callback)

    def load_global_msg(self):
        with open("core/global.msg", mode="r", encoding="UTF-8") as f:
            return hjson.load(f)

    # This method will load another language, defined in the param 'lang'
    def reload_translation(self, lang):
        self.bot.send_private_channel_message("My language got changed. reloading translations...",
                                              fire_outgoing_event=False)
        self.bot.send_org_message("My language got changed. reloading translations...",
                                  fire_outgoing_event=False)
        self.event_service.fire_event("reload_translation")
        self.language = lang
        self.setting_service.set_value("language", lang)
        for k1 in self.strings:
            for callback in self.translation_callbacks.get(k1):
                self.update_msg(k1, callback)

    #updates the msg's
    def update_msg(self, category, callback):
        data = callback()
        for k in data:
            if self.strings.get(category):
                self.strings[category][k] = data[k].get(self.language) or data[k].get("en_US")
            else:
                self.strings[category] = {k: data[k].get(self.language) or data[k].get("en_US")}

    #
    # the param 'variables' accepts dictionary's ONLY.
    #
    def get_response(self, category, key, variables=None):
        if variables is None:
            variables = {}
        msg = ""
        try:
            if self.strings.get(category):
                if self.strings.get(category).get(key):
                    if isinstance(self.strings.get(category).get(key), list):
                        for line in self.strings.get(category).get(key):
                            msg += line.format(**variables)
                    else:
                        msg = self.strings.get(category).get(key).format(**variables)
                else:
                    self.logger.error("translating key '{key}' in category '{category}' not found"
                                      .format(key=key, category=category))
                    msg = "Error: message for translation key <highlight>'{key}'<end> not found." \
                        .format(key=key)
            else:
                self.logger.error("translation category '{category}' was not found".format(category=category))

                msg = "Error: translating category <highlight>'{category}'<end> not found." \
                    .format(category=category)
        except KeyError as e:
            self.logger.error(
                "translating error category: {mod} key: {key} with params: {params}\n Error: {stcktr}"
                .format(mod=category, key=key, params=variables, stcktr=e))
            msg = "Error: translating error category: <highlight>{mod}<end> key: <highlight>{key}<end>" \
                  " with params: <highlight>{params}<end>".format(mod=category, key=key, params=variables)
        finally:
            return msg
