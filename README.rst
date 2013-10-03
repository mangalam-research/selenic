Selenic is a collection of Python code which is used for testing
browser-based software through Selenium. It is tailored for the
projects at Mangalam Research.

If you want to run tests in Chrome, you only need
chromedriver. Chromedriver is `here
<https://code.google.com/p/chromedriver/downloads/list>`__. The
documentation for its use is `here
<http://code.google.com/p/selenium/wiki/ChromeDriver>`__.

Please look at the examples in `<examples>`_ and read the source code
to know how this all works.

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
