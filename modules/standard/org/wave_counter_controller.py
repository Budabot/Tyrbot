from core.decorators import instance, event, command
from core.public_channel_service import PublicChannelService


@instance()
class WaveCounterController:
    CITY_TARGETED = [1001, 3]

    ALERT_TIMES = [105, 150, 90, 120, 120, 120, 120, 120, 120]

    def __init__(self):
        self.current_wave = None
        self.scheduled_job_id = None

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.job_scheduler = registry.get_instance("job_scheduler")

    @event(event_type=PublicChannelService.ORG_MSG_EVENT, description="Start wave counter when city is targeted by aliens")
    def check_for_city_raid_start(self, event_type, event_data):
        ext_msg = event_data.extended_message
        if [ext_msg.category_id, ext_msg.instance_id] == self.CITY_TARGETED:
            self.start_counter()

    def start_counter(self):
        if self.scheduled_job_id:
            self.job_scheduler.cancel_job(self.scheduled_job_id)

        self.bot.send_org_message("Wave counter started.")
        self.scheduled_job_id = self.job_scheduler.delayed_job(self.timer_alert, self.ALERT_TIMES[0], 0)

    def timer_alert(self, t, wave_number):
        wave_number += 1

        if wave_number == 9:
            self.bot.send_org_message("General incoming.")
            self.scheduled_job_id = None
        else:
            self.bot.send_org_message("Wave <highlight>%d<end> incoming." % wave_number)
            self.scheduled_job_id = self.job_scheduler.scheduled_job(self.timer_alert, t + self.ALERT_TIMES[wave_number], wave_number)
