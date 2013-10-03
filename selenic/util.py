import contextlib

from selenium.webdriver.support.ui import WebDriverWait
import selenium.webdriver.support.expected_conditions as EC


class Util(object):
    def __init__(self, driver):
        self.driver = driver
        self.timeouts = [2]

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


    def get_text_excluding_children(self, element):
        return self.driver.execute_script("""
        return jQuery(arguments[0]).contents().filter(function() {
            return this.nodeType == Node.TEXT_NODE;
        }).text();
        """, element)


    def element_screen_position(self, element):
        return self.driver.execute_script("""
        var offset = jQuery(arguments[0]).offset();
        offset.top -= document.body.scrollTop;
        offset.left -= document.body.scrollLeft;
        return offset;
        """,
        element)


    def get_selection_text(self):
        """
        Gets the text of the current selection.

        .. node:: This function requires that ``rangy`` be installed.

        :returns: The text.
        :rtype: class:`basestring`
        """
        return self.driver.execute_script("""
        return rangy.getSelection(window).toString()
        """)


    def wait(self, condition):
        return WebDriverWait(self.driver, self.timeout).until(condition)


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
    the same keys. If the function returns ``True``, then the two
    objects have the same keys. If the function returns ``False``,
    then you cannot infer anything regarding the keys because the
    function will return ``False`` as soon as it knows that the two
    locations are **not** within tolerance.

    :param a: First position.
    :type a: :class:`dict`
    :param b: Second position.
    :type b: :class:`dict`
    :param tolerance: The tolerance within which the two positions
                      must be.
    :return: An empty string if the comparison is
             successful. Otherwise, the string contains a description
             of the differences.
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
