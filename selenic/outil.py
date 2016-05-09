import socket

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
