import time

from spry.http import HTTPSession


class TestHTTPSession:
    def test_defaults(self):
        url = 'http://google.com'
        session = HTTPSession(url)
        assert session.url == url
