import os
import pytest
import tempfile
import time
from random import SystemRandom
from spry import utils


class TestCreateNullFile:
    def test_invalid_size_raises_error(self):
        with pytest.raises(ValueError):
            utils.create_null_file(None, 0)

    def test_file_exists(self):
        fp = os.path.join(tempfile.gettempdir(), 'spry_test_6108589.tmp')
        utils.create_null_file(fp)
        assert os.path.exists(fp)
        os.remove(fp)

    def test_file_correct_size(self):
        fp = os.path.join(tempfile.gettempdir(), 'spry_test_6108589.tmp')
        size = 12345
        utils.create_null_file(fp, size)
        assert os.stat(fp).st_size == size
        os.remove(fp)


class TestGetFileNameFromHeader:
    def test_failure_returns_none(self):
        assert utils.parse_fname_from_headers({}) is None

    def test_content_disposition_with_quotes(self):
        headers = {'content-disposition': 'attachment; filename="fname.ext"'}
        assert utils.parse_fname_from_headers(headers) == 'fname.ext'

    def test_content_disposition_without_quotes(self):
        headers = {'content-disposition': 'attachment; filename=fname.ext'}
        assert utils.parse_fname_from_headers(headers) == 'fname.ext'


class TestTimestamp:
    def test_consecutive_creation_unique(self):
        num_timestamps = 1000
        timestamps = set((utils.get_timestamp() for _ in range(num_timestamps)))
        assert len(timestamps) == num_timestamps

    def test_cache_resets(self):
        timestamp = [utils.get_timestamp()]
        time.sleep(3)
        timestamp[0] = utils.get_timestamp()
        assert timestamp[0][-1] == '1'


class TestSecondsUnitPair:
    def test_seconds(self):
        seconds = utils.MINUTE - 1
        assert utils.seconds_to_unit_pair(seconds) == (seconds, 'second(s)')

    def test_minutes(self):
        seconds = utils.HOUR - 1
        assert utils.seconds_to_unit_pair(seconds) == (seconds / utils.MINUTE, 'minute(s)')

    def test_hours(self):
        seconds = utils.DAY - 1
        assert utils.seconds_to_unit_pair(seconds) == (seconds / utils.HOUR, 'hour(s)')

    def test_days(self):
        seconds = utils.WEEK - 1
        assert utils.seconds_to_unit_pair(seconds) == (seconds / utils.DAY, 'day(s)')

    def test_weeks(self):
        seconds = utils.WEEK
        assert utils.seconds_to_unit_pair(seconds) == (seconds / utils.WEEK, 'week(s)')

    def test_weeks_highest_unit(self):
        seconds = utils.WEEK * 1000
        assert utils.seconds_to_unit_pair(seconds) == (seconds / utils.WEEK, 'week(s)')

    def test_specify_unit(self):
        seconds = utils.MINUTE
        assert utils.seconds_to_unit_pair(seconds, 'day') == (seconds / utils.DAY, 'day(s)')


class TestBytesToUnitPair:
    def test_bytes(self):
        bytes_ = utils.KIBIBYTE - 1
        assert utils.bytes_to_unit_pair(bytes_) == (bytes_, 'B')

    def test_kibibytes(self):
        bytes_ = utils.MEBIBYTE - 1
        assert utils.bytes_to_unit_pair(bytes_) == (bytes_ / utils.KIBIBYTE, 'KiB')

    def test_mebibytes(self):
        bytes_ = utils.GIBIBYTE - 1
        assert utils.bytes_to_unit_pair(bytes_) == (bytes_ / utils.MEBIBYTE, 'MiB')

    def test_gibibytes(self):
        bytes_ = utils.TEBIBYTE - 1
        assert utils.bytes_to_unit_pair(bytes_) == (bytes_ / utils.GIBIBYTE, 'GiB')

    def test_tebibytes(self):
        bytes_ = utils.PEBIBYTE - 1
        assert utils.bytes_to_unit_pair(bytes_) == (bytes_ / utils.TEBIBYTE, 'TiB')

    def test_pebibytes(self):
        bytes_ = utils.EXBIBYTE - 1
        assert utils.bytes_to_unit_pair(bytes_) == (bytes_ / utils.PEBIBYTE, 'PiB')

    def test_exbibytes(self):
        bytes_ = utils.ZEBIBYTE - 1
        assert utils.bytes_to_unit_pair(bytes_) == (bytes_ / utils.EXBIBYTE, 'EiB')

    def test_zebibytes(self):
        bytes_ = utils.YOBIBYTE - 1
        assert utils.bytes_to_unit_pair(bytes_) == (bytes_ / utils.ZEBIBYTE, 'ZiB')

    def test_yobibytes(self):
        bytes_ = utils.YOBIBYTE
        assert utils.bytes_to_unit_pair(bytes_) == (bytes_ / utils.YOBIBYTE, 'YiB')

    def test_specify_unit(self):
        bytes_ = utils.KIBIBYTE
        assert utils.bytes_to_unit_pair(bytes_, 'GiB') == (bytes_ / utils.GIBIBYTE, 'GiB')


class TestWorkerBPS:
    def test_default(self):
        assert utils.get_worker_bps((500, 'B')) == int(500 * 0.95)

    def test_no_pair(self):
        assert utils.get_worker_bps(None) == 0

    def test_with_workers(self):
        assert utils.get_worker_bps((500, 'B'), 5) == int(500 * 0.95 / 5)


class TestParseSpeedLimit:
    def test_no_match_default(self):
        assert utils.parse_speed_limit('test') == (0.0, 'KiB')

    def test_ps_accepted(self):
        assert utils.parse_speed_limit('55kb') == utils.parse_speed_limit('55kbps')

    def test_value_is_float(self):
        assert isinstance(utils.parse_speed_limit('55kb')[0], float)

    def test_add_i(self):
        assert utils.parse_speed_limit('55kb')[1] == 'KiB'

    def test_case_insensitive(self):
        assert utils.parse_speed_limit('55kB')[1] == 'KiB'

    def test_bytes_no_i(self):
        assert utils.parse_speed_limit('55b')[1] == 'B'


class TestParseKwargs:
    def test_no_args_returns_empty_dict(self):
        assert utils.parse_kwargs(None) == {}
        assert utils.parse_kwargs({}) == {}

    def test_single_keyword_arg(self):
        assert utils.parse_kwargs(['kw=arg']) == {'kw': 'arg'}

    def test_multiple_keyword_args(self):
        assert utils.parse_kwargs(['kw1=arg', 'kw2=arg']) == {'kw1': 'arg', 'kw2': 'arg'}

    def test_multiple_args_in_tuple(self):
        assert utils.parse_kwargs(['kw=arg1|arg2']) == {'kw': ('arg1', 'arg2')}

    def test_convert_args_to_constants(self):
        assert utils.parse_kwargs(['kw=nonE']) == {'kw': None}
        assert utils.parse_kwargs(['kw=tRue']) == {'kw': True}
        assert utils.parse_kwargs(['kw=faLse']) == {'kw': False}
        assert utils.parse_kwargs(['kw=none|true|false']) == {'kw': (None, True, False)}

    def test_convert_args_to_integers(self):
        assert utils.parse_kwargs(['kw=123']) == {'kw': 123}
        assert utils.parse_kwargs(['kw=x265|9000|23.0']) == {'kw': ('x265', 9000, '23.0')}


class TestCalcChunkData:
    def test_no_size_default(self):
        assert utils.calc_section_data(0, 1) == [{'start': 0, 'end': None, 'size': 0}]
        assert utils.calc_section_data(None, 1) == [{'start': 0, 'end': None, 'size': 0}]

    def test_no_num_parts(self):
        assert len(utils.calc_section_data(10, 0)) == 1

    def test_num_parts_greater_than_size(self):
        assert len(utils.calc_section_data(10, 11)) == 10

    def test_end_is_size_minus_one(self):
        for i in range(1000):
            l = SystemRandom().randrange(1024, 1024000000)
            n = SystemRandom().randrange(2, 20)
            chunk_data = utils.calc_section_data(l, n)
            for data in chunk_data:
                assert data['end'] == data['size'] + data['start'] - 1

    def test_size_is_end_minus_start(self):
        for i in range(1000):
            l = SystemRandom().randrange(1024, 1024000000)
            n = SystemRandom().randrange(2, 20)
            chunk_data = utils.calc_section_data(l, n)
            for data in chunk_data:
                assert data['size'] == data['end'] - data['start'] + 1

    def test_sizes_are_within_one_step(self):
        for i in range(1000):
            s = set()
            l = SystemRandom().randrange(1024, 1024000000)
            n = SystemRandom().randrange(2, 20)
            chunk_data = utils.calc_section_data(l, n)
            for data in chunk_data:
                s.add(data['size'])
            assert len(s) in (1, 2)
