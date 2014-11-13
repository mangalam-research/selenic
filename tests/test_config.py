from unittest import TestCase

from selenic import Config, get_config, forget

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_raises

class ConfigTestCase(TestCase):

    def setUp(self):
        forget()

    def test_Config_records(self):
        created = Config("Linux", "Chrome", "30")
        obtained = get_config("Linux", "Chrome", "30")
        self.assertEqual(created, obtained)

    def test_Config_accepts_browser_abbreviations(self):
        table = {
            "ch": "CHROME",
            "ff": "FIREFOX",
            "ie": "INTERNETEXPLORER"
        }
        for br in table:
            # We set the platform to br so that we have a piece of data that
            # is not touched by the abbreviation resolution.
            Config(br, br, "30")

        # In this loop we get the configs by using the full names
        for (key, value) in table.iteritems():
            self.assertEqual(get_config(key, value, "30").platform,
                             key.upper())


class GetConfigTestCase(TestCase):

    def setUp(self):
        forget()

    def test_fails_on_full_spec(self):
        with self.assertRaises(KeyError):
            get_config("Linux", "Chrome", "30")

    def test_fails_to_infer_by_browser(self):
        with self.assertRaisesRegexp(ValueError,
                                     "^no configuration for browser: CHROME$"):
            get_config(None, "Chrome", None)

    def test_fails_to_infer_by_version(self):
        with self.assertRaisesRegexp(ValueError,
                                     "^no configuration for version: 30$"):
            get_config(None, None, "30")

    def test_fails_to_infer_by_platform(self):
        with self.assertRaisesRegexp(ValueError,
                                     "^no configuration for platform: LINUX$"):
            get_config("Linux", None, None)

    def test_no_combination(self):
        Config("Linux", "ch", "30")
        Config("Windows", "ff", "29")
        with self.assertRaisesRegexp(
                ValueError,
                "^no configuration for the combination: None, FIREFOX, 30$"):
            get_config(None, "ff", "30")

    def test_ambiguous(self):
        Config("Linux", "ch", "30")
        Config("Linux", "ch", "29")
        with self.assertRaisesRegexp(
                ValueError,
                "^the combination LINUX, CHROME, None is ambiguous$"):
            get_config("Linux", "ch", None)

    def test_can_infer(self):
        linux = Config("Linux", "chrome", "30")
        Config("Windows", "ch", "29")
        self.assertEqual(get_config(None, "ch", "30"), linux)

    def test_accepts_browser_abbreviations(self):
        table = {
            "ch": "CHROME",
            "ff": "FIREFOX",
            "ie": "INTERNETEXPLORER"
        }
        for br in table.itervalues():
            # We set the platform to br so that we have a piece of data that
            # is not touched by the abbreviation resolution.
            Config(br, br, "30")

        # In this loop we get the configs by using the full names
        for (key, value) in table.iteritems():
            self.assertEqual(get_config(value, key, "30").platform, value)
