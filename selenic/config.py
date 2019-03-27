from selenium import webdriver
import collections

class ConfigTuple(collections.namedtuple(
        'ConfigTuple',
        ('platform', 'browser', 'version'))):

    def as_parameter(self, separator=","):
        return self.platform + separator + self.browser + separator \
            + self.version

configs = collections.OrderedDict()
_configs_by_platform = {}
_configs_by_browser = {}
_configs_by_version = {}

_BROWSER_ABBRS = {
    "IE": "INTERNETEXPLORER",
    "FF": "FIREFOX",
    "CH": "CHROME"
}

def get_config(platform=None, browser=None, version=None):
    browser = browser.upper() if browser is not None else None
    platform = platform.upper() if platform is not None else None

    # Resolve abbreviation if it exists...
    browser = _BROWSER_ABBRS.get(browser, browser) \
        if browser is not None else None

    if platform is not None and browser is not None and version is not None:
        return configs[ConfigTuple(platform, browser, version)]

    ret = None
    if browser is not None:
        if browser not in _configs_by_browser:
            raise ValueError("no configuration for browser: " + browser)
        ret = _configs_by_browser[browser]

    if version is not None:
        if version not in _configs_by_version:
            raise ValueError("no configuration for version: " + version)
        by_version = _configs_by_version[version]
        ret = by_version if ret is None else ret & by_version

    if platform is not None:
        if platform not in _configs_by_platform:
            raise ValueError("no configuration for platform: " + platform)
        by_platform = _configs_by_platform[platform]
        ret = by_platform if ret is None else ret & by_platform

    if len(ret) == 0:
        raise ValueError("no configuration for the combination: {0}, {1}, {2}"
                         .format(platform, browser, version))
    elif len(ret) > 1:
        raise ValueError("the combination {0}, {1}, {2} is ambiguous"
                         .format(platform, browser, version))

    return ret.pop()


def forget():
    # pylint: disable=global-statement
    global configs, _configs_by_platform, _configs_by_browser, \
        _configs_by_version
    configs = {}
    _configs_by_platform = {}
    _configs_by_browser = {}
    _configs_by_version = {}


class Config(object):

    def __init__(self, platform, browser, version, desired_capabilities=None,
                 remote=False):

        if desired_capabilities is None:
            desired_capabilities = {}

        browser = browser.upper() if browser is not None else None
        platform = platform.upper() if platform is not None else None

        # Resolve abbreviation if it exists...
        browser = _BROWSER_ABBRS.get(browser, browser)

        self.platform = platform
        self.browser = browser
        self.version = version
        self.remote = remote
        self.desired_capabilities = desired_capabilities

        key = ConfigTuple(platform, browser, version)
        old = configs.get(key, None)
        configs[key] = self

        ps = _configs_by_platform.setdefault(platform, set())
        ps.add(self)

        bs = _configs_by_browser.setdefault(browser, set())
        bs.add(self)

        vs = _configs_by_version.setdefault(version, set())
        vs.add(self)

        if old:
            ps.remove(old)
            bs.remove(old)
            vs.remove(old)

    def make_selenium_desired_capabilities(self):
        ret = dict(getattr(webdriver.DesiredCapabilities, self.browser))

        ret.update(self.desired_capabilities)
        ret["platform"] = self.platform
        ret["version"] = self.version
        return ret

    def __str__(self):
        return "Selenic configured for " + \
            ", ".join((self.platform, self.browser, self.version,
                       "Remote" if self.remote else "Local"))
