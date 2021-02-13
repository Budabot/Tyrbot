from core.db import DB
from core.logger import Logger
from core.decorators import instance, command, setting
from core.command_param_types import Any, Options
from core.setting_types import TextSettingType
from core.text import Text
from core.tyrbot import Tyrbot

import requests
import json

@instance()
class TranslateController:

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.setting_service = registry.get_instance("setting_service")

    def start(self):
        self.setting_service.register(self.module_name, "setting_azure_token", "", TextSettingType(allow_empty=True), "Enter your Azure Translation Token here")
        self.setting_service.register(self.module_name, "setting_azure_region", "", TextSettingType(["westeurope"], allow_empty=True), "Enter your Azure Translation Region here")
        self.setting_service.register(self.module_name, "setting_translate_language", "en", TextSettingType(["de", "en", "es", "fr"]),
                                      "Enter your default output language",
                                      "See a full list of supported languages here: https://docs.microsoft.com/en-us/azure/cognitive-services/translator/language-support")

    def setting_azure_token(self):
        return self.setting_service.get("setting_azure_token")

    def setting_azure_region(self):
        return self.setting_service.get("setting_azure_region")

    def setting_translate_language(self):
        return self.setting_service.get("setting_translate_language")

    @command(command="translate", params=[Options(["en","de","fr","fi","es","nl","nb","ru","sv","el","da","et","it","hu","hr","id","bs","ko","ja","lt","lv","pt","pl","tlh-Lat"]),Any("text")], access_level="member", description="Translate text to a specific language")
    def translate_to_cmd(self, request, opt_language, query):
        opt_language = opt_language.lower()
        if self.setting_azure_region().get_value() == "None":
            return "Translation is not enabled, no region set"
        if self.setting_azure_token().get_value() == "None":
            return "Translation is not enabled, no token set"
        azure_url = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to=%s" % opt_language
        payload_data = [{'Text':query}]
        header_data = {'Ocp-Apim-Subscription-Key': self.setting_azure_token().get_value(), 'Ocp-Apim-Subscription-Region': self.setting_azure_region().get_value(), 'Content-Type': 'application/json'}

        r = requests.post(azure_url, headers=header_data, json=payload_data, timeout=2)
        response = json.loads(r.content)
        return "(%s) %s >> (%s) %s" % (response[0]['detectedLanguage']['language'], query, response[0]['translations'][0]['to'], response[0]['translations'][0]['text'])

    @command(command="translate", params=[Any("text")], access_level="member", description="Translate text")
    def translate_cmd(self, request, query):
        if self.setting_azure_region().get_value() == "None":
            return "Translation is not enabled, no region set"
        if self.setting_azure_token().get_value() == "None":
            return "Translation is not enabled, no token set"
        azure_url = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to=%s" % self.setting_translate_language().get_value()
        payload_data = [{'Text':query}]
        header_data = {'Ocp-Apim-Subscription-Key': self.setting_azure_token().get_value(), 'Ocp-Apim-Subscription-Region': self.setting_azure_region().get_value(), 'Content-Type': 'application/json'}

        r = requests.post(azure_url, headers=header_data, json=payload_data, timeout=2)
        response = json.loads(r.content)
        return "(%s) %s >> (%s) %s" % (response[0]['detectedLanguage']['language'], query, response[0]['translations'][0]['to'], response[0]['translations'][0]['text'])
