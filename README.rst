otpl-service-check
==================
Basic Nagios/Sensu checks for OpenTable Discovery services.
Something Odd
------------
This is the space for something odd. 

Distribution
------------
`<https://pypi.python.org/pypi/otpl-service-check>`_

Dependencies
------------
See ``requirements.txt``.

Arguments
---------
Run with ``-h`` or ``--help`` to see command-line argument
documentation.

Interface
---------
If there is an error parsing command-line arguments, we return with exit
code 3 (``UNKNOWN``) and print the invocation error.

If there is an error reaching Discovery and parsing the announcements
for your service, we return with exit code 3 (``UNKNOWN``).

We log critical and warning statuses related to announcement, and return
with exit codes 2 (``CRITICAL``) and 1 (``WARNING``)
respectively.

Healthcheck Endpoint Checking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
By default, ``otpl-service-check`` checks your service for health.

If your healthcheck endpoint returns with status code ``2xx``, this is
considered a success.  If it returns with ``4xx``, this is considered a
warning (exit code 1).  ``5xx`` is considered critical (exit code 2).
In the latter two cases, in addition to logging the service status,
based on the ``Content-Type`` of the response, we log a parsed version
of the response body.

- Approximately the first kilobyte of pretty-formatted ``applicaton/json`` responses will be printed.
- ``text/html`` responses are elided; a message saying as much is printed.
- The first 128 bytes of ``text/plain`` responses will be printed.
- Otherwise, responses will be treated as ``text/plain``.

*All* critical statuses, warnings, and successes are logged, and the
exit status of the whole process is the worst of the set.

Race Avoidance
~~~~~~~~~~~~~~
Pulling all announcements from Discovery and then checking each one is
inherently racy.  If ``otpl-service-check`` finds critical errors, it
double-checks your service's announcements.  If any of the critical
errors are for an announcement that no longer exists, they are
downgraded to warnings, and a further warning is emitted indicating that
this circumstance occurred.

Note that this does not avoid all race conditions, just a particular
class of them.

Endpoint Response Codes
-----------------------
* ``2xx``: ``0``, ``OK``
* ``4xx``: ``1``, ``WARNING``
* ``5xx``: ``2``, ``CRITICAL``

This is *a bit of an abuse* of HTTP response codes, but our policy is
that this is the simplest and most flexible way to get rich status
responses from health check endpoints.

Releasing
---------
Set up PyPI RC file, ``.pypirc``.  E.g.::

    [distutils]
    index-servers =
      pypi
      pypitest

    [pypitest]
    repository = https://testpypi.python.org/pypi
    username = cpennello_opentable

    [pypi]
    repository = https://pypi.python.org/pypi
    username = cpennello_opentable

Suppose the version being released is ``a.b.c``.

Create distributions: ``python setup.py sdist bdist_wheel``

Sign distribution files::

  for x in dist/*a.b.c*;do
    gpg --detach-sign -a $x
  done

Use Twine_, uploading to the test repo first.
``twine upload -r pypitest dist/*a.b.c*``

Then to the real repo.
``twine upload -r pypi dist/*a.b.c*``

Notes
-----
Nagios and Sensu plugin API documentation:

* `<https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/3/en/pluginapi.html>`_
* `<https://sensuapp.org/docs/latest/reference/plugins>`_

.. _Twine: https://github.com/pypa/twine
