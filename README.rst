Spry - The protocols you know, made better.
===========================================

Spry provides a cross-platform API, and corresponding CLI, for getting & sending
files over HTTP(S) & SFTP. Building on top of 'Requests'_ and 'Paramiko'_, it adds many
convenient features such as accelerated and parallel transfers, speed limiting,
and session management allowing pause/resume functionally and the ability to
continue incomplete or previously stopped transfers.

Why?
----

* **Sessions:** *The web is fragile and wire time is precious.* Anything can happen
  during file transfers, especially when dealing with large files or directories.
  Therefore, it is useful to continue a failed transfer from right where it left off.
  This saves the redundant transfer of data and, in many cases, money.

* **Acceleration:** *Your time is also precious.* Due to such things as the bandwidth-delay
  product, latency, server imposed connection limits, etc., you are unlikely to be utilizing
  the majority of your bandwidth. There are some hacky remedies such as manipulating the TCP
  window scale option, but those are complicated and generally do more harm than good. It
  turns out the optimal solution is simply leveraging server's 'byte serving'_ capabilities
  and request parts concurrently. The same holds true for SFTP via seeking.

Quickstart
----------

Let's see how we would get the latest Ubuntu desktop release:

API
^^^

.. code-block:: python
    >>> from spry import HTTPSession
    >>> http = HTTPSession()
    >>> ubuntu_iso = http.get(
            'http://releases.ubuntu.com/16.04.1/ubuntu-16.04.1-desktop-amd64.iso',
            './ubuntu.iso'
        )
    >>> http.run()

.. _Requests: https://github.com/kennethreitz/requests
.. _Paramiko: https://github.com/paramiko/paramiko/
.. _byte serving: https://en.wikipedia.org/wiki/Byte_serving









