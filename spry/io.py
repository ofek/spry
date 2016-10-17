from io import open

import requests


class HTTPAdapter:
    def __init__(self, url, session=None, **kwargs):
        if session:
            self.resource = session.get(url, **kwargs)
        else:
            self.resource = requests.get(url, **kwargs)

    def read(self, nbytes):
        return self.resource.raw.read(nbytes)

    def close(self):
        self.resource.close()


class FileAdapter:
    def __init__(self, local_path, mode='rb', **kwargs):
        self.resource = open(local_path, mode, **kwargs)

    def read(self, nbytes):
        return self.resource.read(nbytes)

    def write(self, bytes_):
        self.resource.write(bytes_)

    def seek(self, offset):
        self.resource.seek(offset)

    def close(self):
        self.resource.close()
