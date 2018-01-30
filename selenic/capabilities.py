"""
"""

class NormalizedCapabilities(dict):

    def __init__(self, caps):
        """
        Once upon a time it was possible to just query the capabilities
        returned from a ``WebDriver`` object without having to worry
        about which browser was being driven. The dictionary returned
        would have the same fields across browsers.

        The driver for Edge and geckodriver changed all this. For
        instance, they store the browser version under
        ``browserVersion`` instead of ``version`` everywhere else. And
        they store the platform name under ``platformName`` instead of
        ``platform``.

        The variations are very problematic for code that needs to
        query the capabilities but should work uniformly across
        browsers.

        Instances of this class present a normalized view of the
        capabilities. Instances should be treated as read-only. They
        contains the same fields as the capabilities passed in the
        constructor, with the following differences:

        * ``version`` is renamed ``browserVersion``

        * ``platform`` is renamed ``platformName``

        We normalize to what Edge and geckodriver present because
        going into that direction is safer due to the use of more
        precise names. Going the other way could cause name clashes in
        the future.

        Note that this class is meant to be used to normalize
        capabilities **read** from a ``WebDriver`` object. It is not
        meant to be used to normalize capabilities passed for creating
        such an object.

        :param caps: The original capabilities from which to create
                     a normalized capabilities dictionary.
        """
        # Keep a copy for debugging purposes.
        self.caps = caps

        newcaps = dict(caps)
        if "platformName" not in newcaps:
            newcaps["platformName"] = newcaps["platform"]
            del newcaps["platform"]
            newcaps["browserVersion"] = newcaps["version"]
            del newcaps["version"]

        super(NormalizedCapabilities, self).__init__(newcaps)
