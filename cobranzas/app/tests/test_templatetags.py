from app.templatetags.lookup_dict import lookup_dict

from django.test import TestCase


class LookupDictTest(TestCase):

    def setUp(self):
        self.dictionary = {
            'key1': 1,
            'key2': 2
        }

    def test_lookupdict(self):
        self.assertTrue(lookup_dict(self.dictionary, 'key1'), 1)
        self.assertIsNone(lookup_dict(self.dictionary, 'key3'))
