import contextlib
import math

from selenium.webdriver.support.ui import WebDriverWait
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import TimeoutException

from .capabilities import NormalizedCapabilities

class Util(object):

    def __init__(self, driver, default_timeout=2):
        self.driver = driver
        self.timeouts = [default_timeout]
        self.driver.set_script_timeout(default_timeout)
        self.capabilities = NormalizedCapabilities(driver.desired_capabilities)

        platform = self.capabilities["platformName"]
        # "Mac OS X" on Sauce Labs, "MAC" on Browser Stack
        self.osx = platform.startswith("Mac OS X") or platform == "MAC"

        # Saucelabs sets this inconsistently. When requiring FF on
        # Windows 8.1, we get "XP". When requiring IE on Windows 8.1,
        # we get "WINDOWS". Yuck!
        self.windows = platform in ("XP", "WINDOWS")
        self.linux = platform == "Linux"

        self.firefox = driver.name == "firefox"
        self.ie = driver.name == "internet explorer"
        self.chrome = driver.name == "chrome"
        self.edge = driver.name == "MicrosoftEdge"

        # Only IE 9 or earlier has a problem with setting cookies...
        self._can_set_cookies = not (
            self.ie and int(self.capabilities["browserVersion"]) <= 9)

        self.ctrl_equivalent_x = self.command_x if self.osx else self.ctrl_x
        """
        When controlling a browser running in a platform other than OS X,
        equivalent to `:func:Util.ctrl_x`. Otherwise, equivalent to
        `:func:Util.command_x:`.
        """

    @property
    def can_set_cookies(self):
        """
        ``True`` if the driver we are using is able to set cookies. Bugs in
        selenium sometimes prevent this from being true.
        """
        return self._can_set_cookies

    @property
    def timeout(self):
        return self.timeouts[0]

    @contextlib.contextmanager
    def local_timeout(self, value):
        self.push_timeout(value)
        try:
            yield
        finally:
            self.pop_timeout()

    def push_timeout(self, new):
        self.timeouts[0:0] = [new]

    def pop_timeout(self):
        if len(self.timeouts) == 1:
            raise Exception("can't pop when there is only one element on "
                            "the stack")
        return self.timeouts.pop(0)

    def find_element(self, locator):
        return WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located(locator))

    def find_elements(self, locator):
        return WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_all_elements_located(locator))

    def find_clickable_element(self, locator):
        return WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(locator))

    def find_descendants_by_text_re(self, parent, re, immediate=False):
        """
        :param parent: The parent element into which to search.
        :type parent:
                      :class:`selenium.webdriver.remote.webelement.WebElement`
                      or :class:`str`. When a string is specified, it
                      is interpreted as a CSS selector.
        :param re: A regular expression in JavaScript syntax.
        :type re: :class:`str`
        :param immediate: Whether or not the function should return
                          immediately. If ``False``, the function will
                          wait until there **are** descendants to
                          return. If ``True`` it will return immediately.
        :type immediate: :class:`bool`
        :returns: The descendants whose text (as returned by
                  ``jQuery().text()``) match the regular expression.

        """

        def cond(*_):
            return self.driver.execute_script("""
            var parent = arguments[0];
            if (typeof parent === "string")
                parent = document.querySelector(parent);
            var re = new RegExp(arguments[1]);
            var ret = [];
            var nodes = parent.querySelectorAll("*");
            for(var i = 0, node; (node = nodes[i]) !== undefined; ++i)
                if (re.test(node.textContent.trim()))
                    ret.push(node);
            return ret;
            """, parent, re)

        return self.wait(cond) if not immediate else cond()

    #
    # The key sending methods are here as a sort of insurance policy
    # against possible issues with the various drivers that Selenium
    # uses.  We used to emit sequences like Ctrl-X or Shift-Q as
    # key_down, send_keys, key_up sequences. However, these sequence
    # are **really** expensive when using a remote setup. So the
    # following methods use a single send_keys instead. If this turns
    # out to be a problem eventually, we can still revert to the
    # key_down, send_keys, key_up sequence if we ever need to do this.
    #
    def ctrl_x(self, x, to=None):
        """
        Sends a character to the currently active element with Ctrl
        pressed. This method takes care of pressing and releasing
        Ctrl.
        """
        seq = [Keys.CONTROL, x, Keys.CONTROL]

        # This works around a bug in Selenium that happens in FF on
        # Windows, and in Chrome on Linux.
        #
        # The bug was reported here:
        #
        # https://code.google.com/p/selenium/issues/detail?id=7303
        #
        if (self.firefox and self.windows) or (self.linux and self.chrome):
            seq.append(Keys.PAUSE)

        if to is None:
            ActionChains(self.driver) \
                .send_keys(seq) \
                .perform()
        else:
            self.send_keys(to, seq)

    #
    # The key sending methods are here as a sort of insurance policy
    # against possible issues with the various drivers that Selenium
    # uses.  We used to emit sequences like Ctrl-X or Shift-Q as
    # key_down, send_keys, key_up sequences. However, these sequence
    # are **really** expensive when using a remote setup. So the
    # following methods use a single send_keys instead. If this turns
    # out to be a problem eventually, we can still revert to the
    # key_down, send_keys, key_up sequence if we ever need to do this.
    #
    def command_x(self, x, to=None):
        """
        Sends a character to the currently active element with Command
        pressed. This method takes care of pressing and releasing
        Command.
        """
        if to is None:
            ActionChains(self.driver) \
                .send_keys([Keys.COMMAND, x, Keys.COMMAND]) \
                .perform()
        else:
            self.send_keys(to, [Keys.COMMAND, x, Keys.COMMAND])

    def send_keys(self, element, x):
        """
        Sends keys to the element. This method takes care of handling
        modifiers keys. To press and release a modifier key you must
        include it twice: once to press, once to release.
        """
        ActionChains(self.driver) \
            .send_keys_to_element(element, x) \
            .perform()

    def get_text_excluding_children(self, element):
        return self.driver.execute_script("""
        var parent = arguments[0];
        var child = parent.firstChild;
        var ret = "";
        while(child) {
            if (child.nodeType === Node.TEXT_NODE)
                ret += child.textContent;
            child = child.nextSibling;
        }
        return ret;
        """, element)

    def element_screen_position(self, element):
        return self.driver.execute_script("""
        var rect = arguments[0].getBoundingClientRect();
        return {left: rect.left, top: rect.top};
        """, element)

    def element_screen_center(self, element):
        """
        :returns: The center point of the element.
        :rtype: class:`dict` with the field "left" set to the X
                coordinate and the field "top" set to the Y
                coordinate.

        """
        pos = self.element_screen_position(element)
        size = element.size
        pos["top"] += int(size["height"] / 2)
        pos["left"] += int(size["width"] / 2)
        return pos

    def element_screen_coordinates(self, element):
        return self.driver.execute_script("""
        var rect = arguments[0].getBoundingClientRect();
        return {
        top: rect.top,
        left: rect.left,
        bottom: rect.bottom,
        right: rect.right,
        width: rect.width,
        height: rect.height,
        };
        """, element)

    def element_page_coordinates(self, element):
        return self.driver.execute_script("""
        var rect = arguments[0].getBoundingClientRect();
        return {
          top: rect.top + document.body.scrollTop,
          left: rect.left + document.body.scrollLeft,
          bottom: rect.bottom + document.body.scrollTop,
          right: rect.right + document.body.srollLeft,
          width: rect.width,
          height: rect.height,
        };
        """, element)

    def visible_to_user(self, element, *ignorable):
        """
        Determines whether an element is visible to the user. A list of
        ignorable elements can be passed to this function. These would
        typically be things like invisible layers sitting atop other
        elements. This function ignores these elements by setting
        their CSS ``display`` parameter to ``none`` before checking,
        and restoring them to their initial value after checking. The
        list of ignorable elements should not contain elements that
        would disturb the position of the element to check if their
        ``display`` parameter is set to ``none``. Otherwise, the
        algorithm is likely to fail.

        :param element: The element to check.
        :type element: :class:`selenium.webdriver.remote.webelement.WebElement`
        :param ignorable: The elements that can be ignored.
        :type ignorable: :class:`list` of :strings that are CSS selectors.

        """
        if not element.is_displayed():
            return False
        return self.driver.execute_script("""
        var el = arguments[0];
        var ignorable = arguments[1];

        var old_displays = ignorable.map(function (x) {
            var old = x.style.display;
            x.style.display = "none";
            return old;
        });
        try {
            var rect = el.getBoundingClientRect();
            // Sigh... we need to round the numbers to avoid running into
            // factional pixels causing the following test to fail.
            rect = {
              left: Math.ceil(rect.left),
              right: Math.floor(rect.right),
              top: Math.ceil(rect.top),
              bottom: Math.floor(rect.bottom)
            }
            var ret = false;

            var efp = document.elementFromPoint.bind(document);
            var at_corner;
            ret = ((at_corner = efp(rect.left, rect.top)) === el) ||
                   el.contains(at_corner) ||
                  ((at_corner = efp(rect.left, rect.bottom)) === el) ||
                   el.contains(at_corner) ||
                  ((at_corner = efp(rect.right, rect.top)) === el) ||
                   el.contains(at_corner) ||
                  ((at_corner = efp(rect.right, rect.bottom)) === el) ||
                   el.contains(at_corner);
        }
        finally {
            var ix = 0;
            ignorable.forEach(function (x) {
                x.style.display = old_displays[ix];
                ix++;
            });
        }
        return ret;
        """, element, ignorable)

    def get_window_inner_size(self):
        return self.driver.execute_script("""
        return {height: window.innerHeight, width: window.innerWidth};
        """)

    def completely_visible_to_user(self, element):
        if not element.is_displayed():
            return False
        # We floor all dimensions to avoid issues caused by
        # fractions of pixels. (Sigh...)
        pos = {k: math.floor(v) for (k, v) in
               self.element_screen_position(element).items()}
        size = {k: math.floor(v)
                for (k, v) in element.size.items()}
        window_size = self.driver.get_window_size()
        return (pos["top"] >= 0 and
                pos["left"] >= 0 and
                pos["top"] + size["height"] <= window_size["height"] and
                pos["left"] + size["width"] <= window_size["width"])

    def get_selection_text(self):
        """
        Gets the text of the current selection.

        :returns: The text.
        :rtype: class:`basestring`
        """
        return self.driver.execute_script("""
        var texts = [];
        var sel = window.getSelection();
        var limit = sel.rangeCount;
        for (var i = 0; i < limit; ++i) {
           texts.push(sel.getRangeAt(i).toString());
        }
        return texts.join("");
        """)

    def is_something_selected(self):
        """
        :returns: Whether something is selected.
        :rtype: class:`bool`
        """
        return self.driver.execute_script("""
        var sel = window.getSelection();
        return sel.rangeCount && !sel.getRangeAt(0).collapsed;
        """)

    def scroll_top(self, element):
        """
        Gets the top of the scrolling area of the element.

        :param element: An element on the page.
        :type element: :class:`selenium.webdriver.remote.webelement.WebElement`
        :returns: The top of the scrolling area.
        """
        return self.driver.execute_script("""
        return arguments[0].scrollTop;
        """, element)

    def window_scroll_top(self):
        """
        Gets the top of the scrolling area for ``window``.

        :returns: The top of the scrolling area.
        """
        return self.driver.execute_script("""
        return window.scrollY;
        """)

    def window_scroll_left(self):
        """
        Gets the left of the scrolling area for ``window``.

        :returns: The left of the scrolling area.
        """
        return self.driver.execute_script("""
        return window.scrollX;
        """)

    def wait(self, condition):
        """
        Waits for a condition to be true.

        :param condition: Should be a callable that operates in the
                          same way ``WebDriverWait.until`` expects.
        :returns: Whatever ``WebDriverWait.until`` returns.
        """
        return WebDriverWait(self.driver, self.timeout).until(condition)

    def wait_until_not(self, condition):
        """
        Waits for a condition to be false.

        :param condition: Should be a callable that operates in the
                          same way ``WebDriverWait.until_not`` expects.
        :returns: Whatever ``WebDriverWait.until_not`` returns.
        """
        return WebDriverWait(self.driver, self.timeout).until_not(condition)

    def get_html(self, element):
        """
        :param element: The element.
        :type element: :class:`selenium.webdriver.remote.webelement.WebElement`
        :returns: The HTML of an element.
        :rtype: :class:`str`
        """
        return self.driver.execute_script("""
        return arguments[0].outerHTML;
        """, element)

    def number_of_siblings(self, element):
        """
        :param element: The element.
        :type element: :class:`selenium.webdriver.remote.webelement.WebElement`
        :returns: The number of siblings.
        :rtype: :class:`int`
        """
        return self.driver.execute_script("""
        return arguments[0].parentNode.childNodes.length;
        """, element)

    def assert_same(self, first, second):
        """
        Compares two items for identity. The items can be either single
        values or lists of values. When comparing lists, identity
        obtains when the two lists have the same number of elements
        and that the element at position in one list is identical to
        the element at the same position in the other list.

        This method is meant to be used for comparing lists of DOM
        nodes. It would also work with lists of booleans, integers,
        and similar primitive types, but is pointless in such
        cases. Also note that this method cannot meaningfully compare
        lists of lists or lists of dictionaries since the objects that
        would be part of the list would be created anew by Selenium's
        marshalling procedure. Hence, in these cases, the assertion
        would always fail.

        :param first: The first item to compare.
        :type first:
                     :class:`selenium.webdriver.remote.webelement.WebElement`
                     or array of
                     :class:`selenium.webdriver.remote.webelement.WebElement`.
        :param second: The second item to compare.
        :type second:
           :class:`selenium.webdriver.remote.webelement.WebElement` or
           :array of
           :class:`selenium.webdriver.remote.webelement.WebElement`.
        :raises: :class:`AssertionError` when unequal.
        """
        if not isinstance(first, list):
            first = [first]
        if not isinstance(second, list):
            second = [second]
        if not self.driver.execute_script("""
        var first = arguments[0];
        var second = arguments[1];
        if (first.length != second.length)
            return false;
        for(var i = 0; i < first.length; ++i)
            if (first[i] !== second[i])
                return false;
        return true;
        """, first, second):
            raise AssertionError("unequal")


def locations_within(a, b, tolerance):
    """
    Verifies whether two positions are the same. A tolerance value
    determines how close the two positions must be to be considered
    "same".

    The two locations must be dictionaries that have the same keys. If
    a key is pesent in one but not in the other, this is an error. The
    values must be integers or anything that can be converted to an
    integer through ``int``. (If somehow you need floating point
    precision, this is not the function for you.)

    Do not rely on this function to determine whether two object have
    the same keys. If the function finds the locations to be within
    tolerances, then the two objects have the same keys. Otherwise,
    you cannot infer anything regarding the keys because the function
    will return as soon as it knows that the two locations are **not**
    within tolerance.

    :param a: First position.
    :type a: :class:`dict`
    :param b: Second position.
    :type b: :class:`dict`
    :param tolerance: The tolerance within which the two positions
                      must be.
    :return: An empty string if the comparison is successful. Otherwise,
             the string contains a description of the differences.
    :rtype: :class:`str`
    :raises ValueError: When a key is present in one object but not
                        the other.
    """
    ret = ''
    # Clone b so that we can destroy it.
    b = dict(b)

    for (key, value) in a.items():
        if key not in b:
            raise ValueError("b does not have the key: " + key)
        if abs(int(value) - int(b[key])) > tolerance:
            ret += 'key {0} differs: {1} {2}'.format(key, int(value),
                                                     int(b[key]))
        del b[key]

    if b:
        raise ValueError("keys in b not seen in a: " + ", ".join(b.keys()))

    return ret


class Condition(object):

    """
    ``Condition`` objects are used for waiting on conditions where
    failing to attain the desired condition should not result in a
    ``TimeoutException``. This object allows obtaining the last return
    value of the condition check rather than dealing with a
    ``TimeoutException`` that does not provide any useful information.
    """

    def __init__(self, util, check):
        """
        :param util: The ``Util`` object to use to perform the wait.
        :type util: :class:`Util`
        :param check: The check to perform.
        :type check: A callable.
        """
        self.util = util
        self.check = check
        self.last_return = None
        self.called = False

    def __call__(self, *args, **kwargs):
        self.last_return = self.check(*args, **kwargs)
        self.called = True
        return self.last_return

    def wait(self):
        """
        Wait until the check performed by ``self.check`` is true, or the
        timeout occurs.

        :returns: Whatever ``self.check`` last returned, whether there
                  was a timeout or not.
        """
        try:
            self.util.wait(self)
        except TimeoutException:
            pass
        return self.last_return


class Result(object):

    """
    ``Result`` objects are meant to be used with
    :class:``Condition``. They evaluate to a boolean value according
    to the boolean value of their ``result`` property.
    """

    def __init__(self, result, payload):
        """
        :param result: The result that this object should contain.
        :param payload: Some additional payload.
        """
        self.result = result
        self.payload = payload

    def __bool__(self, *args, **kwargs):
        return bool(self.result)
