import re
import os
import subprocess
import types
from distutils.version import StrictVersion

import selenium
from selenium import webdriver
from selenium.webdriver.firefox.webdriver import FirefoxProfile, FirefoxBinary
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from . import remote, outil
from .capabilities import NormalizedCapabilities

CHROMEDRIVER_ELEMENT_CENTER_PATCH_FLAG = \
    "_selenic_chromedriver_element_center_patch"

class Builder(object):

    def __init__(self, config_path, options):
        """
        Initializes a configuration.

        :param config_path: The configuration file to use. Must be a valid
                            Python file.
        :type config_path: :class:`basestring`
        :param options: A dictionary of key/value pairs with which the
                        global variable ``builder_args`` will be initialized
                        before the configuration is read.
        """
        self.config_path = config_path

        self.local_conf = {
            'builder_args': options
        }
        exec(compile(open(self.config_path).read(), self.config_path, 'exec'),
             self.local_conf)

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
        self.remote_service = None

        if self.remote:
            remote_service = self.local_conf["REMOTE_SERVICE"]
            self.remote_service = \
                remote.get_service_cls(remote_service)(self.local_conf)

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

        chromedriver_version = None
        if self.remote:
            driver = self.remote_service.build_driver(desired_capabilities)
        else:
            if browser_string == "CHROME":
                chromedriver_path = self.local_conf["CHROMEDRIVER_PATH"]
                driver = webdriver.Chrome(
                    chromedriver_path,
                    chrome_options=self.local_conf.get("CHROME_OPTIONS"),
                    desired_capabilities=desired_capabilities,
                    service_log_path=self.local_conf["SERVICE_LOG_PATH"],
                    service_args=self.local_conf.get("SERVICE_ARGS"))
                version_line = subprocess.check_output(
                    [chromedriver_path, "--version"]).decode("utf8")
                version_str = re.match(r"^ChromeDriver (\d+\.\d+)",
                                       version_line).group(1)
                chromedriver_version = StrictVersion(version_str)
            elif browser_string == "FIREFOX":
                profile = self.local_conf.get("FIREFOX_PROFILE") or \
                    FirefoxProfile()
                binary = self.local_conf.get("FIREFOX_BINARY") or \
                    FirefoxBinary()
                driver = webdriver.Firefox(profile, binary,
                                           capabilities=desired_capabilities)
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
            driver_caps = NormalizedCapabilities(driver.desired_capabilities)
            browser_version = \
                re.sub(r"\..*$", "", driver_caps["browserVersion"])

            if driver_caps["platformName"].upper() != self.config.platform:
                raise ValueError("the platform you want is not the one "
                                 "you are running selenic on")

            if browser_version != self.config.version:
                raise ValueError("the version installed is not the one "
                                 "you wanted")

        # On BrowserStack we cannot set the version of chromedriver or
        # query it. So we make the reasonable assuption that the
        # version of chromedriver is greater than 2.13. (There have
        # been at least 7 releases after 2.13 at the time of writing.)
        if (self.remote_service and
            self.remote_service.name == "browserstack") or \
           (chromedriver_version is not None and
                chromedriver_version > StrictVersion("2.13")):
            # We patch ActionChains.
            chromedriver_element_center_patch()
            # We need to mark the driver as needing the patch.
            setattr(driver, CHROMEDRIVER_ELEMENT_CENTER_PATCH_FLAG, True)

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

    def set_test_status(self, passed=True):
        if not self.remote_service:
            return

        self.remote_service.set_test_status(passed)

    def get_unused_port(self):
        return outil.get_unused_port() if not self.remote_service else \
            self.remote_service.get_unused_port()

    def start_tunnel(self):
        if not self.remote_service:
            return None

        return self.remote_service.start_tunnel()

    def set_tunnel_id(self, tunnel_id):
        if not self.remote_service:
            return None

        self.remote_service.set_tunnel_id(tunnel_id)

    def stop_tunnel(self):
        if not self.remote_service:
            return None

        return self.remote_service.stop_tunnel()

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

        if original.__self__:
            return original(by, value)
        else:
            return original(self, by, value)
    return method


def chromedriver_element_center_patch():
    """
    Patch move_to_element on ActionChains to work around a bug present
    in Chromedriver 2.14 to 2.20.

    Calling this function multiple times in the same process will
    install the patch once, and just once.
    """

    patch_name = "_selenic_chromedriver_element_center_patched"
    if getattr(ActionChains, patch_name, None):
        return  # We've patched ActionChains already!!

    # This is the patched method, which uses getBoundingClientRect
    # to get the location of the center.
    def move_to_element(self, el):
        pos = self._driver.execute_script("""
        var rect = arguments[0].getBoundingClientRect();
        return { x: rect.width / 2, y: rect.height / 2};
        """, el)
        self.move_to_element_with_offset(el, pos["x"], pos["y"])
        return self

    old_init = ActionChains.__init__

    def init(self, driver):
        old_init(self, driver)

        # Patch the instance, only if the driver needs it.
        if getattr(driver, CHROMEDRIVER_ELEMENT_CENTER_PATCH_FLAG, None):
            self.move_to_element = types.MethodType(move_to_element, self)

    ActionChains.__init__ = init

    # Mark ActionChains as patched!
    setattr(ActionChains, patch_name, True)
