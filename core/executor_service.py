import time
from concurrent.futures import ThreadPoolExecutor

from core.decorators import instance
from core.dict_object import DictObject


@instance()
class ExecutorService:
    def __init__(self):
        self.jobs = []
        self.job_scheduler_id = None

    def inject(self, registry):
        self.job_scheduler = registry.get_instance("job_scheduler")

    def start(self):
        self.executor = ThreadPoolExecutor(max_workers=10)

    def submit_job(self, start_timeout, job, *args, **kwargs):
        fut = self.executor.submit(job, *args, **kwargs)
        self.jobs.append(DictObject({"future": fut,
                                     "expires": int(time.time()) + start_timeout}))
        self.jobs.sort(key=lambda x: x.expires)
        self.update_next_expiration()

    def update_next_expiration(self):
        if self.jobs:
            job = self.jobs[0]
            if self.job_scheduler_id:
                self.job_scheduler.cancel_job(self.job_scheduler_id)
            self.job_scheduler_id = self.job_scheduler.scheduled_job(self.cancel_expired_jobs, job.expires)

    def cancel_expired_jobs(self, t):
        while self.jobs and self.jobs[0].expires <= t:
            job = self.jobs.pop(0)
            if job.future.cancel():
                self.logger.warning("canceling job due to timeout: '%s'" % job)
        self.update_next_expiration()
