import threading
import time
from collections import deque

from spry.progress import Counter, ProgressTracker, SpeedLimiter
from spry.utils import (
    STATE_CHECK, unit_pair_to_bytes
)


class Streamer:
    def __init__(self, remote_path, local_path, section, tracker, limiter, counter, timeout):

        self.remote_path = remote_path
        self.local_path = local_path
        self.section = section
        self.tracker = tracker
        self.limiter = limiter
        self.total = counter
        self.timeout = timeout
        self.reader = None
        self.writer = None

        # Control variables
        self.is_running = False
        self.is_paused = False

        # Uncontrolled state
        self.is_alive = False
        self.is_done = False
        self.is_connected = True

    def run(self):
        self.is_alive = True
        self.is_running = True

        # last_active = time.time()

        while True:

            try:
                self._setup()
                self.is_connected = True
            except:
                self.is_connected = False

            writer = self.writer
            reader = self.reader
            size = self.section.size
            tracker = self.tracker
            total = self.total
            get_size = self.limiter.get

            bytes_consumed = 0
            last_active = time.time()

            if self.is_connected:
                while True:

                    # Check state controlled by parent Session
                    if not self.is_running:
                        self.cleanup()
                        return
                    elif self.is_paused:
                        time.sleep(STATE_CHECK)
                        continue

                    # If a speed limit is set, this call to the limiter will
                    # block our thread until it is ready to serve more bytes.
                    # Advantageously, this also releases the GIL.
                    chunk_size = get_size()

                    # Catch broken internet connection
                    try:
                        chunk = reader.read(chunk_size)
                        if not chunk:

                            # If previously disconnected and no chunk,
                            # consider still unable to connect
                            if not self.is_connected:
                                break

                            self.is_connected = True
                            break
                        self.is_connected = True
                    except:
                        self.is_connected = False
                        break

                    chunk_size = len(chunk)

                    # Edge case to protect against incorrect response headers or
                    # SFTP implementation, therefore maintaining file integrity
                    if size and chunk_size + bytes_consumed > size:

                        remaining = chunk[:size - bytes_consumed]
                        chunk_size = len(remaining)

                        writer.write(remaining)
                        tracker.add(chunk_size)
                        bytes_consumed += chunk_size
                        break

                    writer.write(chunk)
                    tracker.add(chunk_size)
                    bytes_consumed += chunk_size

            if size:
                if bytes_consumed == size:
                    self.is_done = True
                    self.section.size -= bytes_consumed
                    self.cleanup()
                    return
                else:

                    # Connection was lost during reading, either server-side or
                    # locally. Update progress for future attempts.
                    if not self.is_connected:
                        self.section.start += bytes_consumed
                        self.section.size -= bytes_consumed

                    # Scenario #2 is that the server limits # of connections and
                    # sent us a redirect or nothing. In this case, whatever was
                    # read was not the proper content. Reset from initial offset.
                    else:
                        self.tracker.remove(bytes_consumed)

            else:

                # Assume finished in lieu of reference size
                if self.is_connected:
                    self.is_done = True
                    self.cleanup()
                    return

            if tracker.total > total:
                last_active = time.time()
                total.set(tracker.total)
                continue
            else:
                if not self.timeout or time.time() - last_active < self.timeout:
                    continue
                break

        self.cleanup()

    def start(self):
        if not self.is_alive and not self.is_done:
            threading.Thread(target=self.run).start()

    def stop(self):
        self.is_running = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def cleanup(self):
        self.writer.close()
        self.reader.close()
        self.is_running = False
        self.is_alive = False

    def _setup(self):
        raise NotImplementedError


class FileSync:
    def __init__(self, method, remote_path, local_path, keep=False,
                 parts=4, speed_limit=None, timeout=20, restart=False,
                 tracker=None, limiter=None):

        self.method = method
        self.remote_path = remote_path
        self.local_path = local_path
        self.keep = keep
        self.parts = parts or 4
        self.restart = restart

        # Control variables
        self.speed_limit = speed_limit
        self.timeout = timeout

        self.streamers = []
        self.tracker = ProgressTracker(parent=tracker)
        self.limiter = SpeedLimiter(parent=limiter)
        self.counter = Counter()

        if self.speed_limit:
            self.set_speed_limit(*self.speed_limit)

    def _spawn(self, *args, **kwargs):
        raise NotImplementedError

    def run(self, *args, **kwargs):
        if not self.is_alive():
            self._spawn(*args, **kwargs)

    def is_alive(self):
        for streamer in self.streamers:
            if streamer.is_alive:
                return True
        return False

    def success(self):
        for streamer in self.streamers:
            if not streamer.is_done:
                return False
        return True

    def stop(self):
        for streamer in self.streamers:
            streamer.stop()

    def pause(self):
        for streamer in self.streamers:
            streamer.pause()

    def resume(self):
        for streamer in self.streamers:
            streamer.resume()

    def get_progress(self):
        return self.tracker.get_progress()

    def set_speed_limit(self, value, unit='KiB'):
        if value:
            self.speed_limit = (value, unit)
            self.limiter.set_limit(
                unit_pair_to_bytes(self.speed_limit)
            )
        else:
            self.speed_limit = None
            self.limiter.set_limit(0)

    @property
    def done(self):
        return self.tracker.done

    def _reset(self):
        self.streamers.clear()
        self.tracker.clear()
        self.limiter.reset()
        self.counter.set(0)


class Session:
    def __init__(self, concurrent=4, parts=4, speed_limit=None, timeout=20, restart=False):
        self.concurrent = concurrent
        self.parts = parts
        self.restart = restart

        # Control variables
        self.is_running = False
        self.is_paused = False
        self.speed_limit = speed_limit
        self.timeout = timeout

        self.tracker = ProgressTracker()
        self.limiter = SpeedLimiter()

        self.unfinished = deque()
        self.workers = deque()
        self.finished = []
        self.errors = []

        if self.speed_limit:
            self.set_speed_limit(*self.speed_limit)

    def get(self, *args, **kwargs):
        raise NotImplementedError

    def send(self, *args, **kwargs):
        raise NotImplementedError

    def _run(self, forever=False):
        self.is_running = True

        while True:
            time.sleep(STATE_CHECK)

            if not self.is_running:
                break
            elif self.is_paused:
                continue

            # Remove finished workers from queue
            for _ in range(len(self.workers)):
                worker = self.workers[0]

                if not worker.is_alive():

                    if worker.success():
                        self.finished.append(self.workers.popleft())
                    else:
                        self.errors.append(self.workers.popleft())

                else:
                    self.workers.rotate(-1)

            # Repopulate worker queue
            while len(self.workers) < self.concurrent:
                if self.unfinished:
                    self.workers.append(self.unfinished.popleft())
                    continue
                break

            for worker in self.workers:
                if not worker.is_alive():
                    worker.run()

            if not forever and not self.unfinished and not self.workers:
                break

        self.is_running = False

    def run(self, *args, **kwargs):
        if not self.is_running:
            threading.Thread(target=self._run, args=args, kwargs=kwargs).start()

    def stop(self):
        self.is_running = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def get_progress(self):
        return self.tracker.get_progress()

    def set_speed_limit(self, value, unit='KiB'):
        if value:
            self.speed_limit = (value, unit)
            self.limiter.set_limit(
                unit_pair_to_bytes(self.speed_limit)
            )
        else:
            self.speed_limit = None
            self.limiter.set_limit(0)

    @property
    def done(self):
        return not self.unfinished

















