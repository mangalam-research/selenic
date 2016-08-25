from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import StaleElementReferenceException

class Table(object):
    name = None
    cssid = None
    initialized_locator = None
    field_selectors = None

    def __init__(self, util, name=None, cssid=None,
                 initialized_locator=None, field_selectors=None):
        """
        :param util: The util object to use to access Selenium.

        :type util: :class:`selenic.util.Util`

        :param name: The user-friendly name to give to the table.

        :param cssid: The CSS id to use to find the table.

        :param initialized_locator: A selector to use to detect
        whether the table is ready.

        :type initialized_locator: This should be a ``(By..., string)`` pair.

        :param field_selectors: A list of CSS selectors to scope the
        field searches. When the class searches for fields, it will
        search in each of the CSS selectors passed here. We do not
        verify that these selectors are within the table selected by
        ``cssid``. The fields may thus be *outside* the table.

        :type field_selectors: A list of strings.
        """
        self.util = util

        if cssid:
            self.cssid = cssid

        if name:
            self.name = name

        if initialized_locator:
            self.initialized_locator = None

        if field_selectors:
            self.field_selectors = field_selectors

        if self.field_selectors is None:
            self.field_selectors = []

        self._found_fields = None

    def add_field_selector(self, selector):
        self.field_selectors.append(selector)

    @property
    def _search_fields(self):
        if not self._found_fields:
            self._find_search_fields()

        return self._found_fields

    def _find_search_fields(self):
        self.wait_for_initialized()

        found = self.util.driver.execute_script("""
        var cssid = arguments[0];
        var selectors = arguments[1];
        var found = {};

        function search_selector(selector) {
          var scope = document.querySelector(selector);
          var types = ["input", "select"];
          for (var type_ix = 0, type; (type = types[type_ix]); ++type_ix) {
            var els = scope.getElementsByTagName(type);
            for (var el_ix = 0, el; (el = els[el_ix]); ++el_ix) {
              var label = el.closest("label");
              if (!label)
                throw new Error("no label for " + el);

              // We clone the label, and clean out the form controls.
              // ``select`` elements in particular will produce text
              // due to the  ``option`` elements.

              var clone = label.cloneNode(true);
              var child = clone.firstElementChild;
              while (child) {
                var next = child.nextElementSibling;
                if (types.indexOf(child.localName) > -1) {
                  child.parentNode.removeChild(child);
                }
                child = next;
              }

              label = clone.textContent.trim().replace(/:$/, '');
              found[label] = el;
            }
          }
        }

        for (var selector_ix = 0, selector; (selector = selectors[selector_ix]);
          ++selector_ix) {
            search_selector(selector);
        }

        // We cannot just return the dictionary we populated, because Selenium
        // won't convert the values to proper WebElements. Flattening
        // the dictionary like this does the trick.

        var ret = [];
        var keys = Object.keys(found);
        for (var key_ix = 0, key; (key = keys[key_ix]); ++key_ix) {
            ret.push(key, found[key]);
        }
        return ret;
        """, self.cssid, self.field_selectors)
        # Reconstitute the dictionary
        self._found_fields = dict(zip(found[::2], found[1::2]))

    def call_with_search_field(self, name, callback):
        """
        Calls a piece of code with the DOM element that corresponds to
        a search field of the table.

        If the callback causes a ``StaleElementReferenceException``,
        this method will refetch the search fields and try
        again. Consequently **the callback should be designed to be
        callable multiple times and should only interact with the
        search field passed to it.** It should not fetch or interact
        with other DOM elements.

        :param name: The name of the field to use.
        :param callback: The callback to call. The first parameter
        will be the Selenium ``WebElement`` that is the search field.
        """
        done = False
        while not done:
            def check(*_):
                if name in self._search_fields:
                    return True

                # Force a refetch
                self._found_fields = None
                return False

            self.util.wait(check)
            field = self._search_fields[name]
            try:
                callback(field)
                done = True
            except StaleElementReferenceException:
                # We force a refetch of the fields
                self._found_fields = None

    def wait_for_initialized(self):
        """
        This code will wait using the currently active timeout set on
        the ``Util`` object that was passsed when this instance was
        created.
        """

        # Waiting for the existence of a .dataTable element is not
        # reliable. We wait for the existence of the "next" button
        # instead.
        return len(self.util.find_elements(self.initialized_locator)) > 0

    def fill_field(self, name, value):
        driver = self.util.driver

        def fill(el):
            driver.execute_script("arguments[0].value = arguments[1];",
                                  el, value[:-1])
            self.setup_redraw_check()
            el.send_keys(value[-1])
            self.wait_for_redraw()

        self.call_with_search_field(name, fill)

    def set_select_option(self, name, value):
        def select(el):
            select = Select(el)
            self.setup_redraw_check()
            select.select_by_visible_text(value)
            self.wait_for_redraw()

        self.call_with_search_field(name, select)

    def setup_redraw_check(self):
        raise NotImplementedError()

    def wait_for_redraw(self):
        raise NotImplementedError()

    def wait_for_results(self, expected_total):
        raise NotImplementedError()

    def get_result(self, number):
        raise NotImplementedError()
