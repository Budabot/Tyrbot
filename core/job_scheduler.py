from core.decorators import instance
from core.logger import Logger
from collections import deque
import time


@instance()
class JobScheduler:
    def __init__(self):
        self.logger = Logger("setting_manager")
        self.scheduled_jobs = deque([])
        self.job_id_index = 0

    def inject(self, registry):
        pass

    def start(self):
        pass

    def check_for_scheduled_jobs(self, timestamp):
        while self.scheduled_jobs and self.scheduled_jobs[0]["time"] <= timestamp:
            try:
                job = self.scheduled_jobs.popleft()
                job["callback"](job["time"], *job["args"], **job["kwargs"])
            except Exception as e:
                self.logger.warning("Error processing scheduled job", e)

    def schedule_job(self, callback, delay, *args, **kwargs):
        job_id = self._get_next_job_id()
        new_job = {
            "id": job_id,
            "callback": callback,
            "args": args,
            "kwargs": kwargs,
            "time": int(time.time()) + delay
        }

        self._insert_job(new_job)
        return job_id

    def _insert_job(self, new_job):
        for index, job in enumerate(self.scheduled_jobs):
            if job["time"] > new_job["time"]:
                self.scheduled_jobs.insert(index, new_job)
                return
        self.scheduled_jobs.append(new_job)

    def _get_next_job_id(self):
        self.job_id_index += 1
        return self.job_id_index
