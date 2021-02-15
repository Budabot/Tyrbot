from core.conn import Conn
from core.decorators import instance, event
from core.public_channel_service import PublicChannelService


@instance()
class WaveCounterController:
    MESSAGE_SOURCE = "wave_counter"
    CITY_TARGETED = [1001, 3]

    ALERT_TIMES = [105, 150, 90, 120, 120, 120, 120, 120, 120]

    def inject(self, registry):
        self.job_scheduler = registry.get_instance("job_scheduler")
        self.message_hub_service = registry.get_instance("message_hub_service")

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Start wave counter when city is targeted by aliens")
    def check_for_city_raid_start(self, event_type, event_data):
        ext_msg = event_data.extended_message
        if ext_msg:
            if [ext_msg.category_id, ext_msg.instance_id] == self.CITY_TARGETED:
                self.start_counter(event_data.conn)

    def start_counter(self, conn: Conn):
        if conn.data.scheduled_job_id:
            self.job_scheduler.cancel_job(conn.data.scheduled_job_id)

        self.send_message(f"Wave counter started for {conn.org_name or conn.char_name}.")
        conn.data.scheduled_job_id = self.job_scheduler.delayed_job(self.timer_alert, self.ALERT_TIMES[0], conn, 0)

    def timer_alert(self, conn, t, wave_number):
        wave_number += 1

        if wave_number == 9:
            self.send_message("General incoming.")
            conn.data.scheduled_job_id = None
        else:
            self.send_message("Wave <highlight>%d</highlight> incoming." % wave_number)
            conn.data.scheduled_job_id = self.job_scheduler.scheduled_job(self.timer_alert, t + self.ALERT_TIMES[wave_number], conn, wave_number)

    def send_message(self, msg):
        self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, msg)
