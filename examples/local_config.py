from selenic import Config

#
# This file gives you an overview of what selenium-config is able to
# work with. Settings that are not documented ought to be evident to
# someone who knows how Selenium works.
#

SAUCELABS_CREDENTIALS = "userid:key"

caps = {
    "nativeEvents": True
}

# This config would execute on SauceLabs because it is remote.
CONFIG = Config("Windows 8.1", "CHROME", "36", caps, remote=True)

#
# CHROME settings
#

# Only useful when running Chrome locally.
CHROMEDRIVER_PATH = "/blah/blah/chromedriver"

# Only useful when running Chrome locally.
SERVICE_LOG_PATH = "/tmp/log"

from selenium.webdriver.chrome.options import Options
CHROME_OPTIONS = Options()
# Probably not something that makes sense remotely.
CHROME_OPTIONS.binary_location = "/blah"

#
# FIREFOX_SETTINGS
#

from selenium.webdriver.firefox.webdriver import FirefoxProfile, FirefoxBinary
FIREFOX_PROFILE = FirefoxProfile()
# Manipulate the profile as you wish...

# Useful if you want to use a binary other than the one which is on
# your PATH.
FIREFOX_BINARY = FirefoxBinary("/opt/blah/firefox")
