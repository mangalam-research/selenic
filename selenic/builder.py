import re
import os
import httplib
import base64
try:
    import json
except ImportError:
    import simplejson as json
from distutils.version import StrictVersion

import selenium
from selenium import webdriver
from selenium.webdriver.firefox.webdriver import FirefoxProfile, FirefoxBinary
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class Builder(object):

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

        self.config = self.local_conf.get("CONFIG")

        if colon_handling is None:
            self.colon_handling = self.config.browser == \
                "INTERNETEXPLORER" and \
                StrictVersion(
                    selenium.__version__) <= StrictVersion("2.40.0")
        elif colon_handling is True:
            self.colon_handling = True
        elif colon_handling is False:
            self.colon_handling = False
        else:
            raise Exception("bad value for COLON_HANDLING: " + colon_handling)

        self.remote = self.config.remote

    def __getattr__(self, name):
        if name in self.local_conf:
            return self.local_conf[name]

        raise AttributeError("{!r} object has no attribute {!r}"
                             .format(self.__class__, name))

    def get_driver(self, desired_capabilities=None):
        """
        Creates a Selenium driver on the basis of the configuration file
        upon which this object was created.

        :param desired_capabilities: Capabilities that the caller
            desires to override. This have priority over those
            capabilities that are set by the configuration file passed
            to the builder.
        :type desired_capabilities: class:`dict`
        :returns: A driver.
        :raises ValueError: When it can't figure out how to create a
                            browser as specified by the BROWSER
                            configuration variable.
        """
        override_caps = desired_capabilities or {}

        desired_capabilities = \
            self.config.make_selenium_desired_capabilities()
        desired_capabilities.update(override_caps)

        browser_string = self.config.browser

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
                    service_log_path=self.local_conf["SERVICE_LOG_PATH"],
                    service_args=self.local_conf.get("SERVICE_ARGS"))
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

            # Check that what we get is what the config wanted...
            if driver.desired_capabilities["platform"].upper() \
               != self.config.platform:
                raise ValueError("the platform you want is not the one "
                                 "you are running selenic on")
            if re.sub(r"\..*$", "", driver.desired_capabilities["version"]) != \
               self.config.version:
                raise ValueError("the version installed is not the one "
                                 "you wanted")

        driver = self.patch(driver)
        return driver

    def update_ff_binary_env(self, variable):
        """
        If a ``FIREFOX_BINARY`` was specified, this method updates an
        environment variable used by the ``FirefoxBinary`` instance to
        the current value of the variable in the environment.

        This method is a no-op if ``FIREFOX_BINARY`` has not been
        specified or if the configured browser is not Firefox.

        A common use-case for this method is updating ``DISPLAY`` once
        an Xvfb or Xephyr instance has been launched. Typically, by
        the time these displays are launched, the configuration file
        has already been loaded and whatever ``FirefoxBinary``
        instance was created for ``FIREFOX_BINARY`` has a stale
        ``DISPLAY`` value.

        :param variable: The name of the variable to update.
        :type variable: :class:`str`
        """
        if self.config.browser != 'FIREFOX':
            return

        binary = self.local_conf.get('FIREFOX_BINARY')
        if binary is None:
            return

        # pylint: disable=protected-access
        binary._firefox_env[variable] = os.environ[variable]

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
