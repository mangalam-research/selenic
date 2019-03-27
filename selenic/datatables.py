import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import TimeoutException

from .util import Condition, Result

from .tables import Table

info_re = re.compile(r"^Showing (\d+) to (\d+) of (\d+) entries")

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
    setTimeout(test, 100);
}
test();
"""

class Datatable(Table):

    def __init__(self, *args, **kwargs):
        super(Datatable, self).__init__(*args, **kwargs)
        self.field_selectors.append("#" + self.cssid + "_filter")

    def wait_for_initialized(self):
        try:
            self.util.driver.execute_async_script("""
            var cssid = arguments[0];
            var done = arguments[1];
            var $table = jQuery(document.getElementById(cssid));

            function check() {
              // When Datatables may be loaded by a module loader,
              // it is possible that Datatables has not been loaded
              // yet. Poll.
              if (!jQuery.fn.dataTable) {
                setTimeout(check, 100);
                return;
              }

              var settings = jQuery.fn.dataTable.isDataTable($table) &&
                $table.DataTable().settings()[0];
              if (settings && settings._bInitComplete) {
                // Already initialized.
                done();
                return;
              }
              // Not initialized: wait for the init event.
              $table.one("init.dt", function () {
                done();
              });
            }

            check();
            """, self.cssid)
            # If we did not timeout, then the table is initialized
            return True
        except TimeoutException:
            # If we did timeout, initialization did not happen.
            return False

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
