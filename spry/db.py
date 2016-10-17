import contextlib
import os
import threading

from appdirs import AppDirs
from sqlalchemy import Column, ForeignKey, create_engine
from sqlalchemy.dialects.sqlite import INTEGER, TEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker

DATA_DIR = AppDirs('spry').user_data_dir
DB_FILE = os.path.join(DATA_DIR, 'sessions.db')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

engine = create_engine('sqlite:///{}'.format(DB_FILE))
engine.connect()

session_factory = sessionmaker(bind=engine)
DBSession = scoped_session(session_factory)

Base = declarative_base()


class Request(Base):
    __tablename__ = 'requests'

    id = Column(INTEGER, primary_key=True)
    method = Column(TEXT)
    remote_path = Column(TEXT)
    local_path = Column(TEXT)


class Session(Base):
    __tablename__ = 'sessions'

    id = Column(INTEGER, primary_key=True)
    method = Column(TEXT)
    remote_path = Column(TEXT)
    local_path = Column(TEXT)
    speed_limit = Column(INTEGER, nullable=True)
    timeout = Column(INTEGER, nullable=True)


class Section(Base):
    __tablename__ = 'sections'

    id = Column(INTEGER, primary_key=True)
    size = Column(INTEGER)
    start = Column(INTEGER)
    end = Column(INTEGER)

    def __repr__(self):
        return 'Size: {}, Start: {}, End: {}'.format(self.size, self.start, self.end)


class RWLock:
    # Taken from https://github.com/django/django/blob/master/django/utils/synch.py
    def __init__(self):
        self.mutex = threading.RLock()
        self.can_read = threading.Semaphore(0)
        self.can_write = threading.Semaphore(0)
        self.active_readers = 0
        self.active_writers = 0
        self.waiting_readers = 0
        self.waiting_writers = 0

    def reader_enters(self):
        with self.mutex:
            if self.active_writers == 0 and self.waiting_writers == 0:
                self.active_readers += 1
                self.can_read.release()
            else:
                self.waiting_readers += 1
        self.can_read.acquire()

    def reader_leaves(self):
        with self.mutex:
            self.active_readers -= 1
            if self.active_readers == 0 and self.waiting_writers != 0:
                self.active_writers += 1
                self.waiting_writers -= 1
                self.can_write.release()

    @contextlib.contextmanager
    def reader(self):
        self.reader_enters()
        try:
            yield
        finally:
            self.reader_leaves()

    def writer_enters(self):
        with self.mutex:
            if self.active_writers == 0 and self.waiting_writers == 0 and self.active_readers == 0:
                self.active_writers += 1
                self.can_write.release()
            else:
                self.waiting_writers += 1
        self.can_write.acquire()

    def writer_leaves(self):
        with self.mutex:
            self.active_writers -= 1
            if self.waiting_writers != 0:
                self.active_writers += 1
                self.waiting_writers -= 1
                self.can_write.release()
            elif self.waiting_readers != 0:
                t = self.waiting_readers
                self.waiting_readers = 0
                self.active_readers += t
                while t > 0:
                    self.can_read.release()
                    t -= 1

    @contextlib.contextmanager
    def writer(self):
        self.writer_enters()
        try:
            yield
        finally:
            self.writer_leaves()
