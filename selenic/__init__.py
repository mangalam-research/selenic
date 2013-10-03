from selenium.webdriver.common.action_chains import ActionChains
import selenium

from config import *

if selenium.__version__ == "2.35.0":
    # Work around bug in 2.35.0
    def send_keys(self, *keys_to_send):
        """
        Sends keys to current focused element.

        :Args:
        - keys_to_send: The keys to send.
        """
        self.key_down(keys_to_send)
        return self

    ActionChains.send_keys = send_keys
