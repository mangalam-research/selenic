import subprocess
import os
import tempfile
import time
import http.client
import base64
import shutil
import signal
try:
    import json
except ImportError:
    import simplejson as json

from .base import Remote

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
    (username, key) = credentials.split(":")
    creds = base64.encodestring(
        ('%s:%s' % (username, key)).encode("utf-8"))[:-1]

    conn = http.client.HTTPConnection("saucelabs.com")
    conn.request('PUT', '/rest/v1/%s/jobs/%s' % (username, jobid),
                 json.dumps({"passed": passed}),
                 headers={"Authorization": b"Basic " + creds})
    resp = conn.getresponse()
    if resp.status != 200:
        raise Exception("got response: " + resp.status)

def get_unused_sauce_port():
    """
    This returns an unused port among those that Sauce Connect
    forwards. Note that this function does **not** lock the port!

    :returns: A presumably free port that Sauce Connect forwards.
    :rtype: int
    """
    #
    # We exclude 80, 443, 888 from the list since they are reserved.
    #
    sc_ports = [
        8000, 8001, 8003, 8031, 8080, 8081, 8765, 8777,
        8888, 9000, 9001, 9080, 9090, 9876, 9877, 9999,
        49221, 55001]

    for candidate in sc_ports:
        candidate_str = str(candidate)

        # lsof will report a hit whenever *either* the source *or*
        # the destination is using the port we are interested
        # in. There does not seem to be a reliable way to tell
        # lsof to just get ports used on the source side
        # (localhost). We'd have to get all addresses on which the
        # host can listen and list them all. Rather than do this,
        # we check the output to see whether the port is used
        # locally.
        try:
            out = subprocess.check_output(["lsof", "-n", "-P", "-i",
                                           ":" + candidate_str]).decode("utf8")
        except subprocess.CalledProcessError as ex:
            # When lsof returns an empty list, the exit code is 1,
            # even if there was no actual error. We handle this
            # here.
            if ex.returncode != 1:
                # returncode other than 1 is a real error...
                raise
            # else we swallow the exception...
            out = ""

        used = False
        # Slice in the next line to skip the header line.
        for line in out.splitlines(True)[1:]:
            # Grab the NAME column.
            name = line.split()[8]
            # The file is of the form ``source->destination``. We
            # only care about the source.
            src = name.split("->")[0]

            if src.endswith(":" + candidate_str):
                # We've found that we are actually using the port...
                used = True
                break

        if not used:
            port = candidate
            break

    return port

class Tunnel(object):

    def __init__(self, path, user, key):
        self.path = path
        self.user = user
        self.key = key
        self.process = None
        self.tmpdir = None
        self.tunnel_id = "sc-tunnel-for-" + str(os.getpid())

    def start(self):
        self.tmpdir = tmpdir = tempfile.mkdtemp()
        pidfile_path = os.path.join(tmpdir, "pid")
        logfile_path = os.path.join(tmpdir, "log")
        readyfile_path = os.path.join(tmpdir, "ready")

        tunnel = subprocess.Popen(
            [self.path, "-u", self.user, "-k", self.key,
             "--se-port", "0", "--logfile", logfile_path,
             "--pidfile", pidfile_path, "--readyfile",
             readyfile_path, "--tunnel-identifier", self.tunnel_id])
        while True:
            if os.path.exists(readyfile_path):
                break
            if tunnel.poll():
                raise Exception("tunnel exited prematurely")
            time.sleep(0.2)

        self.process = tunnel

        return self.tunnel_id

    def stop(self):
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            self.process = None
            shutil.rmtree(self.tmpdir, True)

class SauceLabs(Remote):
    name = "saucelabs"
    url_template = "http://{credentials}@ondemand.saucelabs.com:80/wd/hub"

    def __init__(self, *args, **kwargs):
        super(SauceLabs, self).__init__(*args, **kwargs)
        self.tunnel = None

    def build_driver(self, capabilities):
        caps = capabilities
        if self.tunnel_id and self.tunnel:
            raise Exception("you have set a tunnel id and have "
                            "requested a tunnel; you should do one or the "
                            "other")

        if self.tunnel_id or self.tunnel:
            caps['tunnel-identifier'] = self.tunnel_id or \
                self.tunnel.tunnel_id

        return super(SauceLabs, self).build_driver(capabilities)

    @property
    def credentials(self):
        return self.conf["SAUCELABS_CREDENTIALS"]

    def set_test_status(self, passed=True):
        """
        Sets the final status for test runs that are executed at
        SauceLabs.

        :param passed: Whether or not the test run passed.
        :type passed: :class:`bool`
        :raises Exception: When it can't set the status.
        """
        set_test_status(self.driver.session_id, self.credentials, passed)

    def get_unused_port(self):
        return get_unused_sauce_port()

    def start_tunnel(self):
        user, key = self.credentials.split(":")
        self.tunnel = Tunnel(self.conf["SC_TUNNEL_PATH"], user, key)
        return self.tunnel.start()

    def stop_tunnel(self):
        self.tunnel.stop()
