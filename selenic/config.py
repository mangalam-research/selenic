import httplib
import base64
try:
    import json
except ImportError:
    import simplejson as json
import os
from distutils.version import StrictVersion

import selenium
from selenium import webdriver
from selenium.webdriver.firefox.webdriver import FirefoxProfile, FirefoxBinary
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class Config(object):

    def __init__(self, config_path):
        """
        Initializes a configuration.

        :param config_path: The configuration file to use. Must be a valid
                            Python file.
        :type config_path: :class:`basestring`
        """
        self.config_path = config_path

        self.local_conf = {}
        execfile(self.config_path, self.local_conf)

        # This effectively lets the user force colon handling on or
        # off if COLON_HANDLING is defined.
        colon_handling = self.local_conf.get("COLON_HANDLING", None)

        if colon_handling is None:
            self.colon_handling = self.local_conf["BROWSER"] == \
                "INTERNETEXPLORER" and \
                StrictVersion(
                    selenium.__version__) <= StrictVersion("2.40.0")
        elif colon_handling is True:
            self.colon_handling = True
        elif colon_handling is False:
            self.colon_handling = False
        else:
            raise Exception("bad value for COLON_HANDLING: " + colon_handling)

        self.remote = self.local_conf.get("SAUCELABS", False)

    def __getattr__(self, name):
        if name in self.local_conf:
            return self.local_conf[name]

        raise AttributeError("{!r} object has no attribute {!r}"
                             .format(self.__class__, name))

    def get_driver(self):
        """
        Creates a Selenium driver on the basis of the configuration file
        upon which this object was created.

        :returns: A driver.
        :raises ValueError: When it can't figure out how to create a
                            browser as specified by the BROWSER
                            configuration variable.
        """
        browser_string = self.local_conf["BROWSER"]
        desired_capabilities = dict(getattr(webdriver.DesiredCapabilities,
                                            browser_string))

        # Set the desired capabilities from DESIRED_CAPABILITIES
        dc_fields = self.local_conf["DESIRED_CAPABILITIES"]
        for field in dc_fields:
            desired_capabilities[field] = dc_fields[field]

        if self.remote:
            driver = webdriver.Remote(
                desired_capabilities=desired_capabilities,
                command_executor="http://" +
                self.local_conf["SAUCELABS_CREDENTIALS"] +
                "@ondemand.saucelabs.com:80/wd/hub")
        else:
            if browser_string == "CHROME":
                driver = webdriver.Chrome(
                    self.local_conf["CHROMEDRIVER_PATH"],
                    chrome_options=self.local_conf.get("CHROME_OPTIONS"),
                    desired_capabilities=desired_capabilities,
                    service_log_path=self.local_conf["SERVICE_LOG_PATH"])
            elif browser_string == "FIREFOX":
                profile = self.local_conf.get("FIREFOX_PROFILE") or \
                    FirefoxProfile()
                binary = self.local_conf.get("FIREFOX_BINARY") or \
                    FirefoxBinary()
                driver = webdriver.Firefox(profile, binary)
            elif browser_string == "INTERNETEXPLORER":
                driver = webdriver.Ie()
            elif browser_string == "OPERA":
                driver = webdriver.Opera()
            else:
                # SAFARI
                # HTMLUNIT
                # HTMLUNITWITHJS
                # IPHONE
                # IPAD
                # ANDROID
                # PHANTOMJS
                raise ValueError("can't start a local " + browser_string)

        driver = self.patch(driver)

        return driver

    def set_test_status(self, jobid, passed=True):
        """
        Sets the final status for test runs that are executed at
        SauceLabs. Can be called whether or not the tests are run at
        SauceLabs. It is a noop if the tests are *not* run on
        SauceLabs.

        :param jobid: The job id for which to set the status.
        :type jobid: :class:`basestring`
        :param passed: Whether or not the test run passed.
        :type passed: :class:`bool`
        :raises Exception: When it can't set the status.
        """
        if not self.remote:
            return

        (username, key) = self.local_conf["SAUCELABS_CREDENTIALS"].split(":")
        creds = base64.encodestring('%s:%s' % (username, key))[:-1]

        conn = httplib.HTTPConnection("saucelabs.com")
        conn.request('PUT', '/rest/v1/%s/jobs/%s' % (username, jobid),
                     json.dumps({"passed": passed}),
                     headers={"Authorization": "Basic " + creds})
        resp = conn.getresponse()
        if resp.status != 200:
            raise Exception("got response: " + resp.status)

    def patch(self, driver):
        if self.colon_handling:
            import types
            driver.find_element = types.MethodType(make_patched_find_element(
                driver.find_element), driver)
            driver.find_elements = types.MethodType(make_patched_find_element(
                driver.find_elements), driver)

            WebElement.find_element = \
                make_patched_find_element(WebElement.find_element)
            WebElement.find_elements = \
                make_patched_find_element(WebElement.find_elements)

        return driver


def make_patched_find_element(original):

    def method(self, by=By.ID, value=None):
        if By.is_valid(by) and by == By.CLASS_NAME:
            by = By.CSS_SELECTOR
            value = "." + value

        if original.im_self:
            return original(by, value)
        else:
            return original(self, by, value)
    return method
