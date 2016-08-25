import re

from selenium.webdriver.common.by import By

from .util import Condition, Result

from .tables import Table

info_re = re.compile(ur"^Showing (\d+) to (\d+) of (\d+) entries")

_REDRAW_SETUP_FUNCTION = """
function redrawSetup(cssid, done) {
    window.__selenium_test_redrawn = false;
    var processing = document.getElementById(cssid + "_processing");
    var table = document.getElementById(cssid);
    function check() {
        // We do this to make sure that the table is not currently
        // refreshing when we put in our event handler.
        if (processing.style.display !== "none") {
            setTimeout(check, 100);
            return;
        }
        jQuery(table).one("draw.dt", function () {
            window.__selenium_test_redrawn = true;
        });
        done();
    }
    check();
};
"""

_REDRAW_SETUP_SNIPPET = _REDRAW_SETUP_FUNCTION + """
redrawSetup(arguments[0], arguments[1]);
"""

_REDRAW_CHECK_SNIPPET = """
var cb = arguments[0];
function test() {
    if (window.__selenium_test_redrawn) {
        cb();
        return;
    }
    setTimeout(test, 1000);
}
test();
"""

class Datatable(Table):

    def __init__(self, *args, **kwargs):
        super(Datatable, self).__init__(*args, **kwargs)
        self.field_selectors.append("#" + self.cssid + "_filter")
        # Waiting for the existence of a .dataTable element is not
        # reliable. We wait for the existence of the "next" button
        # instead.
        self.initialized_locator = (
            By.CSS_SELECTOR, "#" + self.cssid + "_next")

    def setup_redraw_check(self):
        self.util.driver.execute_async_script(_REDRAW_SETUP_SNIPPET,
                                              self.cssid)

    def wait_for_redraw(self):
        self.util.driver.execute_async_script(_REDRAW_CHECK_SNIPPET)

    def wait_for_results(self, expected_total):
        def check(driver):
            text = driver.find_element_by_id(self.cssid + "_info").text
            match = info_re.match(text)
            if not match:
                return False

            total = int(match.group(3))
            return Result(total == expected_total, total)

        result = Condition(self.util, check).wait()

        return result.payload

    def get_result(self, number):
        return self.util.find_elements((By.CSS_SELECTOR,
                                        "#" + self.cssid + ">tbody>tr"))[number]
