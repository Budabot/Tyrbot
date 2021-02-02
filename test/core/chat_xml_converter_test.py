import unittest

from core.chat_blob import ChatBlob
from core.chat_xml_converter import ChatXmlConverter


class ChatXmlConverterTest(unittest.TestCase):
    items = ["message: <highlight>hey<end>!", ChatBlob("Title", "some content"), "bye"]

    def test_convert_to_xml(self):
        converter = ChatXmlConverter()
        self.assertEqual("""<?xml version="1.0" ?><message xmlns:ao="ao:bot:common"><text>message: <strong>hey</strong>!<popup ref="ao-1">Title</popup>bye</text><data><section id="ao-1">some content</section></data></message>""",
                         converter.convert_to_xml(self.items))

    def test_convert_to_aoml1(self):
        converter = ChatXmlConverter()

        xml = """<?xml version="1.0" ?><message xmlns:ao="ao:bot:common"><text>message: <strong>hey</strong>!<popup ref="ao-1">Title</popup>bye</text><data><section id="ao-1">some content</section></data></message>"""
        self.assertEqual(self.items, converter.convert_to_aoml(xml))

    def test_round_trip_convert(self):
        converter = ChatXmlConverter()

        xml = converter.convert_to_xml(self.items)
        items2 = converter.convert_to_aoml(xml)
        self.assertEqual(self.items, items2)

    def test_aoml_to_xml(self):
        converter = ChatXmlConverter()

        s = "message: <highlight>hey<end>!"

        self.assertEqual("message: <strong>hey</strong>!", converter.aoml_to_xml_str(s))

    def test_combine_strs_in_list(self):
        converter = ChatXmlConverter()

        only_obj = [None, None]
        only_str = ["a", "b", "c", "d"]
        before = ["a", "b", None]
        after = [None, "c", "d"]
        before_and_after = ["a", "b", None, None, "c", "d"]
        in_between = [None, "a", "b", None]
        every_other = ["a", None, "b", None, "c"]

        self.assertEqual([None, None], converter.combine_strs_in_list(only_obj))
        self.assertEqual(["abcd"], converter.combine_strs_in_list(only_str))
        self.assertEqual(["ab", None], converter.combine_strs_in_list(before))
        self.assertEqual([None, "cd"], converter.combine_strs_in_list(after))
        self.assertEqual(["ab", None, None, "cd"], converter.combine_strs_in_list(before_and_after))
        self.assertEqual([None, "ab", None], converter.combine_strs_in_list(in_between))
        self.assertEqual(["a", None, "b", None, "c"], converter.combine_strs_in_list(every_other))
