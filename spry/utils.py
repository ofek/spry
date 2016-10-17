from __future__ import division

import datetime
import os
import re
from collections import defaultdict, OrderedDict
from functools import wraps
from threading import Lock
from time import time

SECOND = 1
MINUTE = SECOND * 60
HOUR = MINUTE * 60
DAY = HOUR * 24
WEEK = DAY * 7

TIME_UNIT = {
    'second': SECOND,
    'minute': MINUTE,
    'hour': HOUR,
    'day': DAY,
    'week': WEEK,
}

BYTE = 1
KIBIBYTE = 1024**1
MEBIBYTE = 1024**2
GIBIBYTE = 1024**3
TEBIBYTE = 1024**4
PEBIBYTE = 1024**5
EXBIBYTE = 1024**6
ZEBIBYTE = 1024**7
YOBIBYTE = 1024**8

BINARY_PREFIX = OrderedDict((
    ('B', BYTE),
    ('KiB', KIBIBYTE),
    ('MiB', MEBIBYTE),
    ('GiB', GIBIBYTE),
    ('TiB', TEBIBYTE),
    ('PiB', PEBIBYTE),
    ('EiB', EXBIBYTE),
    ('ZiB', ZEBIBYTE),
    ('YiB', YOBIBYTE),
))

SPEED_FORMAT = re.compile(r'^([0-9.]+)(B|Ki?B|Mi?B|Gi?B|Ti?B|Pi?B|Ei?B|Zi?B|Yi?B)(ps)?$', re.I)

INTEGER = re.compile(r'^[0-9]+$')
CLI_CONSTANTS = {
    'none': None,
    'true': True,
    'false': False,
}

# Time between polls of Streamer objects' status in Session
STATE_CHECK = SECOND * 1

# 16 KiB per TCP request seems optimal, and is also the
# recommended chunk size of the Bittorrent protocol
CHUNK_SIZE = KIBIBYTE * 16


def find_dirs_and_files(directory):
    dirs = []
    files = []

    for root, _, filenames in os.walk(directory):
        dirs.append(root)
        files.extend(os.path.join(root, file) for file in filenames)

    return dirs, files


def parse_speed_limit(limit):
    """
    Converts CLI speed limit field to normalized tuple(quantity, binary_prefix)
    """

    match = SPEED_FORMAT.search(limit)

    if not match:
        return 0.0, 'KiB'

    else:
        speed, unit = match.groups()[:2]
        speed, unit = float(speed), unit.upper()

        # Ensure 'i' is present in binary prefix
        if unit != 'B':
            unit = '{}{}{}'.format(unit[0], 'i', unit[-1])

        return speed, unit


def parse_fname_from_headers(headers):
    """Infers file name from HTTP Response headers"""

    # Currently, headers are provided by the requests library and are stored
    # in its CaseInsensitiveDict. In future, care is needed if a different
    # library is used that doesn't normalize casing.
    fname = headers.get('content-disposition', None)

    if fname:
        fname = fname.partition('filename=')[2]

        # Discard optional quotes in Content-Disposition file name
        if '"' == fname[0] == fname[-1]:
            fname = fname[1:-1]

    return fname


def parse_kwargs(args):
    """
    Returns a properly formatted dict of CLI keyword arguments
    for use in Session's underlying connection class.

    Input is list of keyword argument strings with key and
    value separated by a '=', with the latter further
    optionally separated by a '|' to denote a sequence.
    """

    kwargs = {}

    if args:
        for arg in args:
            key, value = arg.split('=', 1)
            values = value.split('|')

            # Convert values to Python primitives if possible
            for i, val in enumerate(list(values)):
                s = val.lower()

                if s in CLI_CONSTANTS:
                    values[i] = CLI_CONSTANTS[s]

                elif INTEGER.search(val):
                    values[i] = int(s)

            # If multiple values, make them a tuple
            if len(values) == 1:
                value = values[0]
            else:
                value = tuple(values)

            kwargs[key] = value

    return kwargs


def timestamp_cache(f):
    """
    Returns a timestamp. A cache is used to ensure timestamps are
    non-repeating even for parallel calls.
    """

    now = datetime.datetime.now
    lock = Lock()
    cache = defaultdict(int)

    # Make mutable to support Python 2.x
    # series' lack of nonlocal keyword
    start_time = [time()]

    @wraps(f)
    def wrapper():
        with lock:
            call_time = time()
            timestamp = now().strftime('%Y-%m-%dT%H.%M.%S.%f')
            cache[timestamp] += 1

            # Clear cache. 2 seconds is enough to ensure no repeats
            if call_time - start_time[0] > 2:
                start_time[0] = call_time

                ts_count = cache[timestamp]
                cache.clear()
                cache[timestamp] = ts_count

            return '{}_{}'.format(timestamp, str(cache[timestamp]))

    return wrapper


@timestamp_cache
def get_timestamp():
    pass  # pragma: no cover


def unit_pair_to_bytes(pair):
    """
    Calculates the number of bytes in a unit pair
    represented as tuple(quantity, binary_prefix)
    """

    if not pair:
        return 0

    speed, unit = pair
    nbytes = speed * BINARY_PREFIX[unit]

    return int(nbytes)


def bytes_to_unit_pair(nbytes, unit=None):
    """
    Converts bytes to appropriate representation of
    size in form tuple(quantity, binary_prefix)

    Examples:
        1023 returns (1023, 'B')
        1024 returns (1, 'KiB')

    Units conform to IEC standards, see:
    https://en.wikipedia.org/wiki/IEC_80000-13
    https://en.wikipedia.org/wiki/Binary_prefix
    """

    if unit:
        return nbytes / BINARY_PREFIX[unit], unit
    elif nbytes < KIBIBYTE:
        return nbytes, 'B'
    elif nbytes < MEBIBYTE:
        return nbytes / KIBIBYTE, 'KiB'
    elif nbytes < GIBIBYTE:
        return nbytes / MEBIBYTE, 'MiB'
    elif nbytes < TEBIBYTE:
        return nbytes / GIBIBYTE, 'GiB'
    elif nbytes < PEBIBYTE:
        return nbytes / TEBIBYTE, 'TiB'
    elif nbytes < EXBIBYTE:
        return nbytes / PEBIBYTE, 'PiB'
    elif nbytes < ZEBIBYTE:
        return nbytes / EXBIBYTE, 'EiB'
    elif nbytes < YOBIBYTE:
        return nbytes / ZEBIBYTE, 'ZiB'
    else:
        return nbytes / YOBIBYTE, 'YiB'


def seconds_to_eta_string(seconds):
    """
    Converts seconds to a readable representation of time remaining.

    Examples:
        59 returns '59s'
        83 returns '1m 23s'
    """

    # Approximate to an integer to avoid string padding or rounding logic
    seconds = int(seconds)

    if not seconds:
        return '< 1s'

    elif seconds < MINUTE:
        return '{}s'.format(seconds)

    elif seconds < HOUR:
        minutes, seconds = seconds // MINUTE, seconds % MINUTE
        return '{}m {}s'.format(minutes, seconds)

    elif seconds < DAY:
        hours, seconds = seconds // HOUR, seconds % HOUR
        minutes, seconds = seconds // MINUTE, seconds % MINUTE
        return '{}h {}m {}s'.format(hours, minutes, seconds)

    elif seconds < WEEK:
        days, seconds = seconds // DAY, seconds % DAY
        hours, seconds = seconds // HOUR, seconds % HOUR
        minutes = seconds // MINUTE
        return '{}d {}h {}m'.format(days, hours, minutes)

    else:
        weeks, seconds = seconds // WEEK, seconds % WEEK
        days, seconds = seconds // DAY, seconds % DAY
        hours = seconds // HOUR
        return '{}w {}d {}h'.format(weeks, days, hours)


def calc_section_data(size, num_parts):
    """
    Calculates info about each part of a file of given
    size separated into given number of parts. Returns
    a list of dicts having 3 pieces of information:

    - 'start' offset inclusive
    - 'end' offset inclusive
    - 'size'
    """

    # Changing this vital function could
    # completely break functionality.
    #
    # "Jar Jar is the key to all of this."

    if not size:
        return [{'start': 0, 'end': 0, 'size': 0}]
    elif not num_parts:
        num_parts = 1
    elif num_parts > size:
        num_parts = size

    section_size = size // num_parts
    remainder = size % num_parts
    section_data = []

    start = 0
    for _ in range(num_parts):
        end = start + section_size

        if remainder != 0:
            end += 1
            remainder -= 1

        section_data.append({'start': start, 'end': end - 1,
                             'size': end - start})
        start = end

    return section_data


def create_null_file(path, size=1):
    """Creates an empty file of optional size"""

    parent_dir = os.path.dirname(path)
    existing_dir = parent_dir
    free_space = 0

    # Walk up file system until an existing directory
    # is found to check for disk space remaining
    while True:
        if os.path.exists(existing_dir):
            free_space = disk_usage(existing_dir)['free']
            break
        existing_dir = os.path.dirname(existing_dir)

    if size >= free_space:
        raise OSError('insufficient storage space remaining')

    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    with open(path, 'wb') as f:
        f.seek(size - 1)
        f.write(b'\x00')


if hasattr(os, 'statvfs'):
    def disk_usage(path):
        """Return disk usage statistics about the given path.

        Returned value is a dict with keys 'total', 'used' and 'free',
        which are the amount of total, used and free space, in bytes.

        Modified from Python 3.3's shutil.disk_usage.
        """
        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        return {'total': total, 'used': used, 'free': free}

elif os.name == 'nt':
    import nt

    def disk_usage(path):
        """Return disk usage statistics about the given path.

        Returned value is a dict with keys 'total', 'used' and 'free',
        which are the amount of total, used and free space, in bytes.

        Modified from Python 3.3's shutil.disk_usage.
        """
        total, free = nt._getdiskusage(path)
        used = total - free
        return {'total': total, 'used': used, 'free': free}


def get_input(pattern, message):  # pragma: no cover
    """Gets user input until it matches the given pattern"""

    while True:
        text = input(message)
        if not re.match(pattern, text):
            continue
        else:
            return text
