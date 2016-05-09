import os
import tempfile
import subprocess
import signal
import base64
import httplib
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
    creds = base64.encodestring('%s:%s' % (username, key))[:-1]

    conn = httplib.HTTPSConnection("www.browserstack.com")
    conn.request('PUT', '/automate/sessions/%s.json' % jobid,
                 json.dumps({"status": "completed" if passed else "error"}),
                 headers={"Content-Type": "application/json",
                          "Authorization": "Basic " + creds})
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
            [self.path, self.key, "-onlyAutomate",
             "-localIdentifier", tunnel_id],
            stdin=open("/dev/null", 'r'),
            stdout=open(stdout_path, 'w'),
            preexec_fn=os.setsid)

        # This is awful but less awful that other
        # alternatives. BrowserStackLocal does not have a well-defined
        # mechanism to know when it is ready so we have to
        # periodically check its stdout. We do not use a pipe due to
        # the well-known issue with reading pipes without allocating a
        # thread to continually read it and prevent the buffer being
        # filled.
        with open(stdout_path, 'r') as stdout:
            while True:
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
            caps['browserstack.localIdentifier'] = \
                self.tunnel_id or self.tunnel.tunnel_id

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


def sanitize_capabilities(caps):
    platform = caps["platform"]

    if platform.upper().startswith("WINDOWS 8"):
        platform = "WIN8"
    elif platform.upper().startswith("OS X "):
        platform = "MAC"

    caps["platform"] = platform

    return caps
