from core.decorators import instance
from core.logger import Logger
from collections import deque
import time


@instance()
class Scheduler:
    def __init__(self):
        self.logger = Logger("setting_manager")
        self.scheduled_jobs = deque([])

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
        new_job = {
            "callback": callback,
            "args": args,
            "kwargs": kwargs,
            "time": int(time.time()) + delay
        }

        for index, job in enumerate(self.scheduled_jobs):
            if job["time"] > new_job["time"]:
                self.scheduled_jobs.insert(index, new_job)
                return
        self.scheduled_jobs.append(new_job)
