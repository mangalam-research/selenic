Selenic is a collection of Python code which is used for testing
browser-based software through Selenium. It is currently tailored for
the projects at Mangalam Research but there is nothing preventing it
from being used for other projects.

If you want to run tests in Chrome, you only need
chromedriver. Chromedriver is `here
<https://code.google.com/p/chromedriver/downloads/list>`__. The
documentation for its use is `here
<http://code.google.com/p/selenium/wiki/ChromeDriver>`__.

Please look at the examples in the ``examples`` subdirectory and read
the source code to know how this all works.

Selenium Issues
===============

Native Events
-------------

It is very often the case that tests which work with native events
fail when using synthetic events. Keep this in mind.

Misc
----

* Selenium 2.35.0: ActionChains.send_keys is broken. Selenic patches
  ActionChains to fix this problem.

* Selenium 2.35.0: It is impossible to know whether a Firefox instance
  is able to handle native events or not. Firefox 22 with 2.35.0 is
  known to handle native events.

* Selenium <= 2.40.0: Handling of colon in locators that use class
  names in IE is completely broken. Selenic attempts to fix the
  issue. See below for some notes.

Colons in Class Names in IE
---------------------------

This is known to occur with Selenium <= 2.40.0. The normal way to
escape colons that appear as part of class names is to put a backslash
in front of the colon. This works without issue in Firefox and Chrome
but in IE there's a bug. The solution is to double up on the
backslashes. Where ``"foo\\:bar"`` would work everywhere else, for IE
we need ``"foo\\\\:bar"``. But there's a problem if we want our code
to work on multiple platforms.

Selenic attempts to work around the issue depending on how
``COLON_HANDLING`` is set:

* Not set, or set to ``NONE``: Selenic will check what broswer you are
  using and what version of Selenium you are using. If it determines
  that the combination is at risk for colons, it will act as if the
  setting was ``True``, otherwise it will act as if the setting was
  ``False``.

* ``True``: turn on the workaround.

* ``False``: turn off the workaround.

The workaround itself is pretty simple. Selenic patches the driver
created from ``selenic.config.Config`` and it patches ``WebElement``
so that every time Selenium searches for elements by class name, it
searches instead by a CSS selector which is equivalent.

Debugging the Firefox Driver
----------------------------

#. Download the version of Selenium that corresponds to whatever API
   you are using.

#. Unzip.

#. Edit ``javascript/firefox-driver/build.desc`` to eliminate the
   platform binaries you do not need. These look like paths of the
   form ``platform/Linux...``. Some are for Windows. (This saves a
   huge amount of build time and space).

#. Issue::

    $ bash ./go //javascript/firefox-driver:webdriver
