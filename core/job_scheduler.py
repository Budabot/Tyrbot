from core.decorators import instance
from core.logger import Logger
import time


@instance()
class JobScheduler:
    def __init__(self):
        self.logger = Logger("setting_manager")
        self.jobs = []
        self.job_id_index = 0

    def inject(self, registry):
        pass

    def start(self):
        pass

    def check_for_scheduled_jobs(self, timestamp):
        while self.jobs and self.jobs[0]["time"] <= timestamp:
            try:
                job = self.jobs.pop(0)
                job["callback"](job["time"], *job["args"], **job["kwargs"])
            except Exception as e:
                self.logger.warning("Error processing scheduled job", e)

    def delayed_job(self, callback, delay, *args, **kwargs):
        return self.scheduled_job(callback, int(time.time()) + delay, *args, **kwargs)

    def scheduled_job(self, callback, scheduled_time, *args, **kwargs):
        job_id = self._get_next_job_id()
        new_job = {
            "id": job_id,
            "callback": callback,
            "args": args,
            "kwargs": kwargs,
            "time": scheduled_time
        }

        self._insert_job(new_job)
        return job_id

    def cancel_job(self, job_id):
        for index, job in enumerate(self.jobs):
            if job["id"] == job_id:
                return self.jobs.pop(index)
        return None

    def _insert_job(self, new_job):
        for index, job in enumerate(self.jobs):
            if job["time"] > new_job["time"]:
                self.jobs.insert(index, new_job)
                return
        self.jobs.append(new_job)

    def _get_next_job_id(self):
        self.job_id_index += 1
        return self.job_id_index
