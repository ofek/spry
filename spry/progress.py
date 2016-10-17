from __future__ import division

from collections import defaultdict, deque
from threading import Lock
from time import sleep, time

from spry.utils import CHUNK_SIZE


class SpeedLimiter:
    def __init__(self, limit=None, request_size=CHUNK_SIZE, parent=None):
        self.limit = limit
        self.request_size = request_size
        self.parent = parent
        self.priority = False
        self.lock = Lock()

        self.requested = 0
        self.start_time = time()

    def get(self):

        if self.parent:
            return self.parent.get()

        with self.lock:
            request_size = self.request_size

            if self.limit:

                if self.requested + request_size >= self.limit:
                    request_size = self.limit - self.requested

                    if request_size <= 0:
                        self.requested = 0
                        time_elapsed = time() - self.start_time

                        if time_elapsed < 1:
                            sleep(1 - time_elapsed)
                        self.start_time = time()

                        if self.limit and self.requested + self.request_size >= self.limit:
                            request_size = self.limit - self.requested
                        else:
                            request_size = self.request_size

                self.requested += request_size

            return request_size

    def set_limit(self, limit):
        with self.lock:
            self.limit = limit

    def set_request_size(self, size):
        with self.lock:
            self.request_size = size

    def promote(self):
        self.priority = True

    def demote(self):
        self.priority = False

    def reset(self):
        with self.lock:
            self.requested = 0
            self.start_time = time()

    def __bool__(self):
        return self.priority


class ProgressTracker:
    def __init__(self, size=0, window=10, parent=None):
        self._size = size
        self._window = window
        self.parent = parent
        self.total = 0
        self.is_finished = False

        self.lock = Lock()
        self.times = deque()
        self.time_total = defaultdict(int)

    def add(self, units):

        if self.parent:
            self.parent.add(units)

        with self.lock:
            now = time()

            # Ensure no duplicates
            if now not in self.time_total:
                self.times.append(now)

            self.time_total[now] += units
            self.total += units

    def remove(self, units):

        if self.parent:
            self.parent.remove(units)

        with self.lock:
            self.total -= units

    def grow(self, size):

        if self.parent:
            self.parent.grow(size)

        with self.lock:
            self._size += size

    def shrink(self, size):

        if self.parent:
            self.parent.shrink(size)

        with self.lock:
            self._size -= size

    def get_progress(self):
        with self.lock:
            now = time()
            times = self.times

            try:
                # Account only for recent activity. The larger the window,
                # the more unresponsive the units/second calculations.
                while now - times[0] > self._window:
                    del self.time_total[times.popleft()]
            except IndexError:
                return 0, 0, self.total, self._size

            ups = sum(self.time_total.values()) / self._window
            eta = 0 if not self._size else (self._size - self.total) / ups

            return ups, eta, self.total, self._size

    @property
    def window(self):
        return self._window

    def set_window(self, window):
        self._window = window

    @property
    def size(self):
        return self._size

    def set_size(self, size):
        self._size = size

    @property
    def done(self):
        return self.is_finished or (self._size - self.total == 0 if self._size else False)

    def clear(self):
        self.total = 0
        self.is_finished = False
        self.times.clear()
        self.time_total.clear()


class Counter:
    def __init__(self):
        self.total = 0
        self.lock = Lock()

    def set(self, n):
        with self.lock:
            self.total = n

    def __gt__(self, other):
        with self.lock:
            return self.total > other

    def __lt__(self, other):
        with self.lock:
            return self.total < other
