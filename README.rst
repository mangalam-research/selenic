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

Chromedriver and ``ActionChains.move_to_element``
-------------------------------------------------

The Changelog for Chromedriver 2.14 says:

 Getting the location of an element, and moving the mouse to an
 element, now uses the center of the first ClientRect, rather than the
 center of the bounding box.

This is in direct violation of the specifications of
``move_to_element``. The issue has been reported `here
<https://bugs.chromium.org/p/chromedriver/issues/detail?id=1069>`_ but
the people reponsible are in no hurry to fix it. (At the time of
writing, it's been 9 months between the submission of the issue.)

If Selenic is asked to create a driver for Chrome and it detects a
Chromedriver version greater than 2.13, it patches ``ActionChains`` so
that when an ``ActionChains`` object is created for a driver that
needs the patch, then ``move_to_element`` on the new instance is
patched to get the element's center with
``getBoundingClientRect``. Upshots:

1. Selenic won't patch ``ActionChains`` *at all* unless it is tasked
   with creating a driver that will work with a Chromedriver version
   greater than 2.13.

2. Once Selenic has patched ``ActionChains`` it is patched for
   good. This means that if if a driver instance for IE is then
   created it will use the patched ``ActionChains``. However, the new
   ``ActionChains`` constructor checks whether the driver for which it
   creates a new instance needs the ``move_to_element`` patch and
   patches accordingly.

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
