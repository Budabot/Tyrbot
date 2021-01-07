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

    @setting(name="setting_azure_token", value="None", description="Enter your Azure Translation Token here")
    def setting_azure_token(self):
        return TextSettingType(["None"])

    @setting(name="setting_azure_region", value="None", description="Enter your Azure Translation Region here")
    def setting_azure_region(self):
        return TextSettingType(["None","westeurope"])

    @setting(name="setting_translate_language", value="en", description="Enter your default output language",
             extended_description="See a full list of supported languages here: https://docs.microsoft.com/en-us/azure/cognitive-services/translator/language-support")
    def setting_translate_language(self):
        return TextSettingType(["de", "en", "es", "fr"])

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
        try:
            r = requests.post(azure_url, headers=header_data, json=payload_data, timeout=2)
            response = json.loads(r.content)
            return "(%s) %s >> (%s) %s" % (response[0]['detectedLanguage']['language'], query, response[0]['translations'][0]['to'], response[0]['translations'][0]['text'])
        except Exception as e:
            self.logger.warning('Exception occured: '+e)
            self.logger.warning(r.content)
            return "Something went wrong, try again later."

    @command(command="translate", params=[Any("text")], access_level="member", description="Translate text")
    def translate_cmd(self, request, query):
        if self.setting_azure_region().get_value() == "None":
            return "Translation is not enabled, no region set"
        if self.setting_azure_token().get_value() == "None":
            return "Translation is not enabled, no token set"
        azure_url = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to=%s" % self.setting_translate_language().get_value()
        payload_data = [{'Text':query}]
        header_data = {'Ocp-Apim-Subscription-Key': self.setting_azure_token().get_value(), 'Ocp-Apim-Subscription-Region': self.setting_azure_region().get_value(), 'Content-Type': 'application/json'}
        try:
            r = requests.post(azure_url, headers=header_data, json=payload_data, timeout=2)
            response = json.loads(r.content)
            return "(%s) %s >> (%s) %s" % (response[0]['detectedLanguage']['language'], query, response[0]['translations'][0]['to'], response[0]['translations'][0]['text'])
        except Exception as e:
            self.logger.warning('Exception occured: '+e)
            self.logger.warning(r.content)
            return "Something went wrong, try again later."
