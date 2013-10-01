#
# This file gives you an overview of what selenium-config is able to
# work with. Settings that are not documented ought to be evident to
# someone who knows how Selenium works.
#

SAUCELABS_CREDENTIALS = "userid:key"

# Must be the name of a set of desired capabilities present in
# selenium.webdriver.common.desired_capabilities.
BROWSER = "FIREFOX"

#
# CHROME settings
#

CHROMEDRIVER_PATH = "/blah/blah/chromedriver"

# Only useful when running Chrome locally
SERVICE_LOG_PATH = "/tmp/log"

#
# FIREFOX_SETTINGS
#

from selenium.webdriver.firefox.webdriver import FirefoxProfile, FirefoxBinary
FIREFOX_PROFILE = FirefoxProfile()
# Manipulate the profile as you wish...

# Useful if you want to use a binary other than the one which is on
# your PATH.
FIREFOX_BINARY = FirefoxBinary("/opt/blah/firefox")
