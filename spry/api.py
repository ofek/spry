from spry.http import HTTPFileSync, HTTPSession


def httpget(url, path, persist=True, parts=4, limit=None, timeout=None, restart=False, **kwargs):
    session = HTTPFileSync('get', url, path, persist=persist, parts=parts, speed_limit=limit,
                           timeout=timeout, restart=restart, **kwargs)
    session.run()

    return session
