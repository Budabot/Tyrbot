
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
    modules = {}
    language = "en_US"
    last_file = None
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
        self.registerTranslation("global", self.read_translations_from_file("core/global.msg"))

    def registerTranslation(self, category, translations):
        self.logger.info("Registering category {cat}".format(cat=category))
        for k in translations:
            if self.strings.get(category):
                self.strings[category][k] = translations[k].get(self.language) or translations[k].get("en_US")
            else:
                self.strings[category] = {k: translations[k].get(self.language) or translations[k].get("en_US")}
        if self.last_file is not None:
            if self.modules.get(category) is None:
                self.modules[category] = []
            self.modules[category].append(self.last_file)

        self.last_file = None

    #This method will load another language, defined in the param 'lang'
    def reload_translation(self, lang):
        self.bot.send_private_channel_message("<orange>My language got changed. reloading translations...<end>",
                                              fire_outgoing_event=False)
        self.bot.send_org_message("<orange>My language got changed. reloading translations...<end>",
                                  fire_outgoing_event=False)

        self.event_service.fire_event("reload_translation")
        self.language = lang
        self.setting_service.set_value("language", lang)
        for k1 in self.strings:
            for k2 in self.strings.get(k1):
                category_link = self.modules.get(k1)
                if isinstance(category_link, list):
                    index = len(category_link) - 1
                    while index >= 0:
                        transl = self.read_translations_from_file(category_link[index])
                        if transl.get(k2):
                            self.strings[k1][k2] = transl.get(k2).get(self.language) or transl.get(k2).get("en_US")
                        index -= 1
        self.last_file = None

    def read_translations_from_file(self, file):
        with open(file, mode="r", encoding="utf-8") as f:
            data = hjson.load(f)
        self.last_file = file
        return data

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
                    msg = "<red>Error: message for translation key <orange>'{key}'<end> not found.<end>" \
                        .format(key=key)
            else:
                self.logger.error("translation category '{category}' was not found".format(category=category))

                msg = "<red>Error: translating category <orange>'{category}'<end> not found.<end>" \
                    .format(category=category)
        except KeyError as e:
            self.logger.error(
                "translating error category: {mod} key: {key} with params: {params}\n Stracktrace: {stcktr}"
                .format(mod=category, key=key, params=variables, stcktr=e))
            msg = "<red>Error: translating error category: <orange>{mod}<end> key: <orange>{key}<end>" \
                  " with params: <orange>{params}<end>".format(mod=category, key=key, params=variables)
        finally:
            return msg
