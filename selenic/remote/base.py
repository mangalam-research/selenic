from selenium import webdriver

class Remote(object):
    name = None
    url_template = None

    def __init__(self, conf):
        self.conf = conf
        self.driver = None
        self.tunnel = None
        self.tunnel_id = None

    def build_driver(self, capabilities):
        self.driver = webdriver.Remote(
            desired_capabilities=capabilities,
            command_executor=self.url_template.format(
                credentials=self.credentials))
        return self.driver

    def sanitize_config(self, config):
        return config

    @property
    def credentials(self):
        raise NotImplementedError()

    def get_unused_port(self):
        raise NotImplementedError()

    def set_test_status(self, passed=True):
        raise NotImplementedError()

    def start_tunnel(self):
        raise NotImplementedError()

    def set_tunnel_id(self, tunnel_id):
        self.tunnel_id = tunnel_id

    def stop_tunnel(self):
        raise NotImplementedError()
