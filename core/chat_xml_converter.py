import re
from xml.dom import minidom, Node

from core.chat_blob import ChatBlob


# https://github.com/Nadybot/Nadybot/blob/api-endpoint-for-messages/src/Modules/WEBSERVER_MODULE/WebChatConverter.php
class ChatXmlConverter:
    ao_namespace = "ao:bot:common"

    aoml_to_xml_regexes = [
        (re.compile(r"/\r?\n/"), "<br />"),
        (re.compile(r"<br>"), "<br />"),

        (re.compile(r"<header>(.+?)<end>"), r"<h1>\1</h1>"),
        (re.compile(r"<header2>(.+?)<end>"), r"<h2>\1</h2>"),
        (re.compile(r"<highlight>(.+?)<end>"), r"<strong>\1</strong>"),
        (re.compile(r"<notice>(.+?)<end>"), r"<strong>\1</strong>"),

        (re.compile(r"<omni>(.+?)<end>"), r"<omni>\1</omni>"),
        (re.compile(r"<clan>(.+?)<end>"), r"<clan>\1</clan>"),
        (re.compile(r"<neutral>(.+?)<end>"), r"<neutral>\1</neutral>"),
        (re.compile(r"<unknown>(.+?)<end>"), r"<unknown>\1</unknown>"),

        (re.compile(r"<green>(.+?)<end>"), r"<black>\1</black>"),
        (re.compile(r"<white>(.+?)<end>"), r"<white>\1</white>"),
        (re.compile(r"<yellow>(.+?)<end>"), r"<yellow>\1</yellow>"),
        (re.compile(r"<blue>(.+?)<end>"), r"<blue>\1</blue>"),
        (re.compile(r"<green>(.+?)<end>"), r"<green>\1</green>"),
        (re.compile(r"<red>(.+?)<end>"), r"<red>\1</red>"),
        (re.compile(r"<orange>(.+?)<end>"), r"<orange>\1</orange>"),
        (re.compile(r"<grey>(.+?)<end>"), r"<grey>\1</grey>"),
        (re.compile(r"<cyan>(.+?)<end>"), r"<cyan>\1</cyan>"),
        (re.compile(r"<violet>(.+?)<end>"), r"<violet>\1</violet>"),
    ]

    xml_to_aoml_replacements = {
        "br": ("\n",),
        "h1": ("<header", "<end>"),
        "h2": ("<header2", "<end>"),
        "strong": ("<highlight>", "<end>"),
    }


    def convert_to_aoml(self, s):
        dom = minidom.parseString(s)
        root = dom.documentElement

        # parse text and data nodes
        text = None
        data = None
        for child in list(root.childNodes):
            if child.tagName == "text":
                text = child
            elif child.tagName == "data":
                data = child
            else:
                raise Exception("Unknown tag '%s'" % child.tagName)

        # populate dict for popup ref lookup
        data_dict = {}
        for child in list(data.childNodes):
            data_dict[child.getAttribute("id")] = child

        return self.combine_strs_in_list(self.element_to_aoml(text, data_dict))

    def convert_to_xml(self, items):
        doc = minidom.Document()
        root = doc.createElement("message")

        root.setAttribute("xmlns:ao", self.ao_namespace)
        doc.appendChild(root)

        text = doc.createElement("text")
        root.appendChild(text)

        data = doc.createElement("data")
        root.appendChild(data)

        section_id_counter = 1
        for item in items:
            if isinstance(item, ChatBlob):
                popup_id = "ao-" + str(section_id_counter)

                popup = doc.createElement("popup")
                popup.setAttribute("ref", popup_id)
                self.append_to_child(popup, item.title)
                text.appendChild(popup)

                section = doc.createElement("section")
                section.setAttribute("id", popup_id)
                self.append_to_child(section, item.msg)
                data.appendChild(section)

                section_id_counter += 1
            elif isinstance(item, str):
                self.append_to_child(text, item)
            else:
                raise Exception("Cannot convert to chat xml from '%s'" + str(item))

        return doc.toxml()

    def append_to_child(self, elem, s):
        for child in list(self.string_to_xml_element(s).childNodes):
            elem.appendChild(child)

    def string_to_xml_element(self, s: str):
        xml = self.aoml_to_xml_str(s)
        dom = minidom.parseString("<root>" + xml + "</root>")
        return dom.documentElement

    def aoml_to_xml_str(self, s: str):
        for r, replacement in self.aoml_to_xml_regexes:
            s = r.sub(replacement, s)

        return s

    def element_to_aoml(self, elem, data_dict):
        results = []
        for child in list(elem.childNodes):
            if child.nodeType == Node.TEXT_NODE:
                results.append(child.nodeValue)
            else:
                if child.tagName == "popup":
                    ref = child.getAttribute("ref")
                    chat_blob = ChatBlob("".join(self.element_to_aoml(child, data_dict)),
                                         "".join(self.element_to_aoml(data_dict[ref], data_dict)))
                    results.append(chat_blob)
                else:
                    pre, post = self.xml_to_aoml_replacements[child.tagName]
                    results.append(pre)
                    results.extend(self.element_to_aoml(child, data_dict))
                    results.append(post)

        return results

    def combine_strs_in_list(self, arr):
        results = []
        current_string = ""
        for item in arr:
            if isinstance(item, str):
                current_string += item
            else:
                if current_string:
                    results.append(current_string)
                    current_string = ""
                results.append(item)

        if current_string:
            results.append(current_string)

        return results
