from distutils.version import StrictVersion

from selenium.webdriver.common.action_chains import ActionChains
import selenium

# To re-export here.
from .config import *
from .builder import *

sel_ver = StrictVersion(selenium.__version__)
v2_35_0 = StrictVersion("2.35.0")

if sel_ver < v2_35_0:
    raise Exception("please ascertain whether the ActionChains.send_keys "
                    "patch is required for Selenium version: " +
                    selenium.__version__)

if sel_ver >= v2_35_0 and sel_ver <= StrictVersion("2.37.2"):
    # Work around bug
    def send_keys(self, *keys_to_send):
        """
        Sends keys to current focused element.

        :Args:
        - keys_to_send: The keys to send.
        """
        self.key_down(keys_to_send)
        return self

    ActionChains.send_keys = send_keys
