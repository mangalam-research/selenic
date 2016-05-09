
from .saucelabs import SauceLabs
from .browserstack import BrowserStack

NAME_TO_CLASS={cls.name: cls for cls in (SauceLabs, BrowserStack)}

def get_service_cls(name):
    try:
        return NAME_TO_CLASS[name]
    except IndexError:
        raise ValueError("the service named '{0}' is unknown".format(name))
