import unittest
import unittest.mock

from core.dict_object import DictObject
from core.executor_service import ExecutorService


class _StubFuture:
    def __init__(self, cancellable):
        self.cancellable = cancellable

    def cancel(self):
        return self.cancellable


class _StubScheduler:
    def __init__(self):
        self.scheduled = []
        self.cancelled = []
        self.next_id = 0

    def scheduled_job(self, callback, scheduled_time, *args, **kwargs):
        self.next_id += 1
        self.scheduled.append((callback, scheduled_time))
        return self.next_id

    def cancel_job(self, job_id):
        self.cancelled.append(job_id)
        return None


def make_service():
    service = ExecutorService()
    service.job_scheduler = _StubScheduler()
    return service


class CancelExpiredJobsTest(unittest.TestCase):

    def test_expired_job_is_cancelled_and_logged(self):
        # this raised AttributeError on self.logger before the fix, so the timeout path could
        # never run to completion. The log is captured rather than printed - an unmuted warning in
        # the suite output should always mean a real problem
        service = make_service()
        service.jobs = [DictObject({"future": _StubFuture(True), "expires": 100})]

        with unittest.mock.patch.object(service, "logger") as logger:
            service.cancel_expired_jobs(200)

        self.assertEqual([], service.jobs)
        self.assertEqual(1, logger.warning.call_count)

    def test_job_that_already_started_is_dropped_without_logging(self):
        service = make_service()
        service.jobs = [DictObject({"future": _StubFuture(False), "expires": 100})]

        with unittest.mock.patch.object(service, "logger") as logger:
            service.cancel_expired_jobs(200)

        # cancel() returns False once the worker has picked the job up - nothing to warn about
        self.assertEqual([], service.jobs)
        self.assertEqual(0, logger.warning.call_count)

    def test_unexpired_jobs_are_kept_and_rescheduled(self):
        service = make_service()
        service.jobs = [DictObject({"future": _StubFuture(True), "expires": 100}),
                        DictObject({"future": _StubFuture(True), "expires": 300})]

        with unittest.mock.patch.object(service, "logger"):
            service.cancel_expired_jobs(200)

        self.assertEqual(1, len(service.jobs))
        self.assertEqual(300, service.jobs[0].expires)
        # the next expiration is re-armed against the remaining job
        self.assertEqual([(service.cancel_expired_jobs, 300)], service.job_scheduler.scheduled)

    def test_no_jobs_is_a_noop(self):
        service = make_service()

        service.cancel_expired_jobs(200)

        self.assertEqual([], service.jobs)
        self.assertEqual([], service.job_scheduler.scheduled)
