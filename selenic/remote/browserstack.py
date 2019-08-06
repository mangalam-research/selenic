import os
import tempfile
import subprocess
import signal
import base64
import http.client
import time
try:
    import json
except ImportError:
    import simplejson as json

from .base import Remote
from ..outil import get_unused_port

def set_test_status(jobid, credentials, passed=True):
    """
    Sets the final status for test runs that are executed at
    SauceLabs.

    :param jobid: The job id for which to set the status.
    :type jobid: :class:`basestring`
    :param credentials: The "user:key" string.
    :type credentials: :class:`basestring`
    :param passed: Whether or not the test run passed. Defaults to ``True``.
    :type passed: :class:`bool`
    :raises Exception: When it can't set the status.
    """

    # curl -u "user:key"
    #      -X PUT
    #      -H "Content-Type: application/json"
    #      -d "{\"status\":\"<new-status>\", \"reason\":\"<reason text>\"}"
    #      https://www.browserstack.com/automate/sessions/<session-id>.json

    (username, key) = credentials.split(":")
    creds = base64.encodestring(
        ('%s:%s' % (username, key)).encode("utf-8"))[:-1]

    conn = http.client.HTTPSConnection("www.browserstack.com")
    conn.request('PUT', '/automate/sessions/%s.json' % jobid,
                 json.dumps({"status": "completed" if passed else "error"}),
                 headers={"Content-Type": "application/json",
                          "Authorization": b"Basic " + creds})
    resp = conn.getresponse()
    if resp.status != 200:
        raise Exception("got response: " + resp.status)

class Tunnel(object):

    def __init__(self, path, key):
        self.path = path
        self.key = key
        self.process = None
        self.tunnel_id = "bslocal-for-" + str(os.getpid())
        self.tmpdir = None

    def start(self):
        self.tmpdir = tmpdir = tempfile.mkdtemp()
        stdout_path = os.path.join(tmpdir, "stdout")
        tunnel_id = self.tunnel_id
        #
        # We use os.setsid to create a new process group. We want this
        # because BrowserStackLocal creates children that won't die if
        # we just kill the parent.
        #
        self.process = subprocess.Popen(
            [self.path, "--key", self.key, "--only-automate",
             "--local-identifier", tunnel_id],
            stdin=open("/dev/null", 'r'),
            stdout=open(stdout_path, 'w'),
            preexec_fn=os.setsid)

        #
        # This is awful but less awful that other
        # alternatives. BrowserStackLocal does not have a well-defined mechanism
        # to know when it is ready so we have to periodically check its
        # stdout. We do not use a pipe due to the well-known issue with reading
        # pipes without allocating a thread to continually read it and prevent
        # the buffer being filled.
        #
        # For the longest time, this loop used to open the file once and
        # continually read from the end. However, a change in libc made it so
        # that EOF is now a sticky flag and if this code read the file before it
        # was written to, then it would read at EOF on the first read, and
        # forever after! (See https://bugs.python.org/issue34371). Opening the
        # file anew each time fixes the problem. Still ugly, but meh... It is
        # also backward compatible.
        #
        while True:
            with open(stdout_path, 'r') as stdout:
                if "Press Ctrl-C to exit" in stdout.read():
                    break
            time.sleep(0.2)

        return tunnel_id

    def stop(self):
        if self.process:
            # SIGTERM does not do it...
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            self.process = None


class BrowserStack(Remote):
    name = "browserstack"
    url_template = "http://{credentials}@hub.browserstack.com:80/wd/hub"

    def __init__(self, *args, **kwargs):
        super(BrowserStack, self).__init__(*args, **kwargs)
        self.tunnel = None

    @property
    def credentials(self):
        return self.conf["BROWSERSTACK_CREDENTIALS"]

    def build_driver(self, capabilities):
        caps = sanitize_capabilities(capabilities)

        if self.tunnel_id and self.tunnel:
            raise Exception("you have set a tunnel id and have "
                            "requested a tunnel; you should do one or the "
                            "other")

        if self.tunnel_id or self.tunnel:
            caps['browserstack.local'] = True
            caps['browserstack.localIdentifier'] = self.tunnel_id or self.tunnel.tunnel_id

        return super(BrowserStack, self).build_driver(capabilities)

    def get_unused_port(self):
        return get_unused_port()

    def start_tunnel(self):
        _, key = self.credentials.split(":")
        self.tunnel = Tunnel(self.conf["BSLOCAL_PATH"], key)
        return self.tunnel.start()

    def stop_tunnel(self):
        self.tunnel.stop()

    def set_test_status(self, passed=True):
        """
        Sets the final status for test runs that are executed at
        SauceLabs.

        :param passed: Whether or not the test run passed.
        :type passed: :class:`bool`
        :raises Exception: When it can't set the status.
        """
        set_test_status(self.driver.session_id, self.credentials, passed)


# We provide a version number in our configuration but BrowserStack wants a
# name.
OSX_VERSION_TO_NAME = {
    "10.6": "Snow Leopard",
    "10.7": "Lion",
    "10.8": "Mountain Lion",
    "10.9": "Mavericks",
    "10.10": "Yosemite",
    "10.11": "El Capitan",
    "10.12": "Sierra",
    "10.13": "High Sierra",
    "10.14": "Mojave",
}

def sanitize_capabilities(caps):
    """
    Sanitize the capabilities we pass to Selenic so that they can
    be consumed by Browserstack.

    :param caps: The capabilities passed to Selenic. This dictionary
    is modified.

    :returns: The sanitized capabilities.
    """
    platform = caps["platform"]

    upper_platform = platform.upper()

    if upper_platform.startswith("WINDOWS "):
        del caps["platform"]
        caps["os"] = "Windows"
        caps["os_version"] = upper_platform[8:]
    elif upper_platform.startswith("OS X "):
        del caps["platform"]
        caps["os"] = "OS X"
        caps["os_version"] = OSX_VERSION_TO_NAME[upper_platform[5:]]

    if caps["browserName"].upper() == "MICROSOFTEDGE":
        # Sauce Labs takes complete version numbers like
        # 15.1234. However, Browser Stack takes only .0 numbers like
        # 15.0.
        caps["version"] = caps["version"].split(".", 1)[0] + ".0"

    caps["browser_version"] = caps["version"]
    del caps["version"]

    return caps
