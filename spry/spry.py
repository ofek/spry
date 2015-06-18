__license__ = """
Copyright (c) 2015 Ofek Lev ofekmeister@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import requests
import threading
from .utils import get_chunk_data, create_null_file


class ChunkGetter(threading.Thread):
    def __init__(self, url, local_path, chunk_info):
        super(ChunkGetter, self).__init__()
        self._url = url
        self._local_path = local_path
        self._start = chunk_info['start']
        self._end = chunk_info['end']
        self._length = chunk_info['length']
        self._file = open(self._local_path, 'r+b')
        self._file.seek(self._start)

    def run(self):
        headers = {'range': 'bytes={}-{}'.format(self._start, self._end)}
        request = requests.get(self._url, headers=headers, stream=True)
        file = self._file

        request_size = 131072
        num_consumed = 0

        while True:
            chunk = request.raw.read(request_size)
            if not chunk:
                break
            chunk_length = len(chunk)

            if chunk_length + num_consumed > self._length:
                file.write(chunk[:self._length - num_consumed])
                break

            file.write(chunk)
            num_consumed += chunk_length


class Session:
    def __init__(self, url, local_path, num_threads=4):
        self.url = url
        self.local_path = local_path
        self.num_threads = num_threads

        self.request_length = None
        self.chunk_data = []
        self.workers = []

    def get_chunk_data(self):
        request = requests.get(self.url, stream=True)
        if request == 404:
            raise Exception

        self.request_length = int(request.headers['content-length'])
        self.chunk_data = get_chunk_data(self.request_length, self.num_threads)

    def create_local_file(self):
        create_null_file(self.local_path, self.request_length)

    def spawn_workers(self):

        for chunk_info in self.chunk_data:
            self.workers.append(ChunkGetter(self.url, self.local_path, chunk_info))

        for worker in self.workers:
            worker.start()

    def start(self):
        self.get_chunk_data()
        self.create_local_file()
        self.spawn_workers()
