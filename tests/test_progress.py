from __future__ import division

import time

from spry.progress import ProgressTracker


class TestProgressTracker:
    def test_defaults(self):
        tracker = ProgressTracker()
        assert tracker.size == 0
        assert tracker.window == 10
        assert tracker.is_finished == False
        assert len(tracker.times) == 0
        assert len(tracker.time_total) == 0

    def test_with_args(self):
        tracker = ProgressTracker(50, 5)
        assert tracker.size == 50
        assert tracker.window == 5

    def test_add(self):
        tracker = ProgressTracker()
        tracker.add(5)
        key = list(tracker.time_total.keys())[0]
        assert tracker.total == 5
        assert len(tracker.times) == 1
        assert tracker.time_total[key] == 5

    def test_add_same_time(self):
        tracker = ProgressTracker()
        num_adds = 20
        for i in range(num_adds):
            tracker.add(i)
        assert len(tracker.times) == len(tracker.time_total) < num_adds

    def test_remove(self):
        tracker = ProgressTracker()
        tracker.add(10)
        tracker.remove(3)
        key = list(tracker.time_total.keys())[0]
        assert tracker.total == 7
        assert tracker.time_total[key] == 10

    def test_grow(self):
        tracker = ProgressTracker()
        tracker.grow(5)
        assert tracker._size == 5

    def test_shrink(self):
        tracker = ProgressTracker(5)
        tracker.shrink(3)
        assert tracker._size == 2

    def test_done_true_if_is_finished(self):
        tracker = ProgressTracker()
        tracker.is_finished = True
        assert tracker.done == True

    def test_done_true_if_size_and_complete(self):
        tracker = ProgressTracker(1)
        tracker.add(1)
        assert tracker.done == True

    def test_done_false_if_size_and_not_complete(self):
        tracker = ProgressTracker(1)
        assert tracker.done == False

    def test_done_false_if_no_size_and_not_is_finished(self):
        tracker = ProgressTracker()
        assert tracker.done == False

    def test_progress_when_empty(self):
        tracker = ProgressTracker(5)
        assert tracker.get_progress() == (0, 0, 0, 5)

    def test_progress_when_no_time_elapsed(self):
        tracker = ProgressTracker(5)
        tracker.add(3)
        assert tracker.get_progress() == (0, 0, 3, 5)

    def test_progress_no_eta_when_no_size(self):
        tracker = ProgressTracker()
        tracker.add(5)
        tracker.add(5)
        assert tracker.get_progress()[1] == 0

    def test_progress_correct(self):
        tracker = ProgressTracker(10)
        tracker.add(3)
        time.sleep(0.1)
        tracker.add(5)
        seconds = tracker.times[-1] - tracker.times[0]
        ups = sum(tracker.time_total.values()) / seconds
        eta = (tracker._size - tracker.total) / ups
        assert tracker.get_progress() == (ups, eta, 8, 10)

    def test_progress_purges_outside_window(self):
        tracker = ProgressTracker(10, 1)
        tracker.add(3)
        time.sleep(0.5)
        tracker.add(5)
        time.sleep(0.6)
        assert tracker.get_progress() == (0, 0, 8, 10)
        assert len(tracker.times) == len(tracker.time_total) == 1
