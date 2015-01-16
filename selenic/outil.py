import socket
import subprocess
import os
import tempfile
import time

def get_unused_port():
    """
    This returns an unused port from the OS. Note that there is no
    guarantee after the port is returned that the OS won't immediately
    reuse it for something else. This function does **not** lock the
    port! On a Linux system which is not starved for ports, there's a
    good chance that the port will still be free by the time the
    calling code uses it.

    The function here is *good enough* for test suites that use
    Selenic. Don't use this for production code.

    :returns: A free port.
    :rtype: int
    """
    # Obtain an unused port from the OS. Linux will assign a port and
    # won't reuse it for a while after we close it.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

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
                                           ":" + candidate_str])
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

def start_sc(path, user, key):
    tmpdir = tempfile.mkdtemp()
    pidfile_path = os.path.join(tmpdir, "pid")
    logfile_path = os.path.join(tmpdir, "log")
    readyfile_path = os.path.join(tmpdir, "ready")

    sc_tunnel_id = "sc-tunnel-for-" + str(os.getpid())
    sc_tunnel = subprocess.Popen(
        [path, "-u", user, "-k", key,
         "--se-port", "0", "--logfile", logfile_path,
         "--pidfile", pidfile_path, "--readyfile",
         readyfile_path, "--tunnel-identifier", sc_tunnel_id])
    while True:
        if os.path.exists(readyfile_path):
            break
        if sc_tunnel.poll():
            raise Exception("tunnel exited prematurely")
        time.sleep(0.2)

    return (sc_tunnel, sc_tunnel_id, tmpdir)
