import os

import requests

from spry.db import Section, Session, RWLock
from spry.io import FileAdapter, HTTPAdapter
from spry.sessions import FileSync, Session, Streamer
from spry.utils import (
    calc_section_data, create_null_file, get_timestamp, parse_fname_from_headers
)

# Until GUI, this will mainly be for developers so no warnings
requests.packages.urllib3.disable_warnings()


class HTTPReader(Streamer):
    def __init__(self, url, local_path, section, tracker, limiter, counter, timeout, session=None, **kwargs):
        super(HTTPReader, self).__init__(url, local_path, section, tracker, limiter, counter, timeout)
        self.session = session
        self.kwargs = kwargs

    def _setup(self):
        if not self.section.end:
            headers = {}
        else:
            headers = {'range': 'bytes={}-{}'.format(self.section.start, self.section.end)}

        self.reader = HTTPAdapter(self.remote_path, self.session, headers=headers, stream=True, **self.kwargs)
        self.writer = FileAdapter(self.local_path, 'r+b')
        self.writer.seek(self.section.start)


class HTTPWriter(Streamer):
    def __init__(self, url, local_path, section, tracker, limiter, counter, timeout, session=None, **kwargs):
        super(HTTPWriter, self).__init__(url, local_path, section, tracker, limiter, counter, timeout)
        self.session = session
        self.kwargs = kwargs

    def _setup(self):
        if not self.section.end:
            headers = {}
        else:
            headers = {'range': 'bytes={}-{}'.format(self.section.start, self.section.end)}

        # self.reader = HTTPAdapter(self.remote_path, self.session, headers=headers, stream=True, **self.kwargs)
        # self.writer = FileAdapter(self.local_path, 'r+b')


class HTTPFileSync(FileSync):
    def __init__(self, method, url, path, session=None, persist=True, keep=False, parts=4,
                 speed_limit=None, timeout=20, restart=False, tracker=None, limiter=None, **kwargs):
        super(HTTPFileSync, self).__init__(method, url, path, keep=keep, parts=parts, speed_limit=speed_limit,
                                           timeout=timeout, restart=restart, tracker=tracker, limiter=limiter)
        self.session = session or requests.Session() if persist else None
        self.kwargs = kwargs

    def _spawn(self, restart=False):
        if self.method.lower() == 'get':

            session_saved = False

            if restart or self.restart or not session_saved:
                self._reset()

                if self.session:
                    inspection = self.session.get(self.remote_path, stream=True, **self.kwargs)
                else:
                    inspection = requests.get(self.remote_path, stream=True, **self.kwargs)
                inspection.close()

                remote_size = int(inspection.headers.get('content-length', 0))
                if not remote_size or self.parts >= remote_size:
                    self.parts = 1

                if os.path.isdir(self.local_path):
                    self.local_path = os.path.join(self.local_path, get_timestamp())

                parent_dir, filename = os.path.split(self.local_path)
                remote_name = parse_fname_from_headers(inspection.headers) if self.keep else None

                self.local_path = os.path.join(parent_dir, remote_name or filename or get_timestamp())
                create_null_file(self.local_path, remote_size or 1)

                self.tracker.grow(remote_size)
                sections = [Section(**data) for data in calc_section_data(remote_size, self.parts)]

                for section in sections:
                    self.streamers.append(
                        HTTPReader(url=self.remote_path, local_path=self.local_path, section=section,
                                   tracker=self.tracker, limiter=self.limiter, counter=self.counter,
                                   timeout=self.timeout, session=self.session, **self.kwargs)
                    )
                for worker in self.streamers:
                    worker.start()

        elif self.method.lower() == 'send':
            pass


class HTTPSession(Session):
    """An HTTP connection manager. This class provides a way to handle the
    transfer of more than one file at a time.

    :param concurrent: The maximum number of simultaneous transfers. Default: 4
    :type concurrent: int
    :param session: The :class:`requests.Session` instance used for persistent
                    connections. If no session is provided, a new one will be
                    created. Default: ``None``
    :type session: :class:`requests.Session` or ``None``
    :param persist: Whether or not to use a single persistent connection for
                    each transfer. This does not affect performance and can be
                    overridden for each transfer request. Default: ``True``
    :type persist: bool
    :param keep: Whether or not to use successfully inferred file names. This can
                 be overridden for each transfer request. Default: ``False``
    :type keep: bool
    :param parts: The number of parts to split transfers into. This can be
                  overridden for each transfer request. Default: 4
    :type parts: int
    :param speed_limit: The global speed limit as a tuple of arity 2 in the form
                        (float, binary_prefix) i.e. (1.23, 'MiB'). Valid prefixes
                        are: B, KiB, MiB, GiB, TiB, PiB, EiB, ZiB, YiB. This will
                        only have an effect if
                        This can be overridden for each transfer request.
                        Default: ``None``
    :type speed_limit: tuple(float, binary_prefix) or ``None``
    :param timeout: The allowed number of seconds transfers will wait on a
                    connection before quitting. This can be overridden for
                    each transfer request. Default: 20
    :type timeout: int
    :param restart: Whether or not to start transfers anew. This can be
                    overridden for each transfer request. Default: ``False``
    :type restart: bool
    """

    def __init__(self, concurrent=4, session=None, persist=True, keep=False,
                 parts=4, speed_limit=None, timeout=20, restart=False):
        super(HTTPSession, self).__init__(concurrent=concurrent, parts=parts, speed_limit=speed_limit,
                                          timeout=timeout, restart=restart)
        self.session = session or requests.Session()
        self.persist = persist
        self.keep = keep

    def get(self, url, path, session=None, persist=True, keep=False, parts=4,
            speed_limit=None, timeout=20, restart=False, use_defaults=False, **kwargs):
        if use_defaults:
            session = self.session
            persist = self.persist
            keep = self.keep
            parts = self.parts
            speed_limit = self.speed_limit
            timeout = self.timeout
            restart = self.restart

        self.unfinished.append(
            HTTPFileSync(
                'get', url=url, path=path, session=session, persist=persist, keep=keep,
                parts=parts, speed_limit=speed_limit, timeout=timeout, restart=restart,
                tracker=self.tracker, limiter=self.limiter, **kwargs
            )
        )


























