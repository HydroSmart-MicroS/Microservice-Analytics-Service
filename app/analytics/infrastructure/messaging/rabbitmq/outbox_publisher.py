import logging
import threading
import json
from .....shared.infrastructure.persistence.postgresql.connection_pool import connect
from .....shared.infrastructure.messaging.rabbitmq import connection

logger=logging.getLogger(__name__)
class OutboxPublisher:
    def __init__(self):
        self.stop_event=threading.Event()
        self.thread=threading.Thread(target=self.run,name='analytics-outbox',daemon=True)
    def start(self):self.thread.start()
    def stop(self):self.stop_event.set();self.thread.join(timeout=8)
    def run(self):
        while not self.stop_event.is_set():
            broker=None
            try:
                with connect() as conn:
                    rows=conn.execute('SELECT event_id,event_type,payload FROM outbox_events WHERE published_at IS NULL ORDER BY occurred_at FOR UPDATE SKIP LOCKED LIMIT 30').fetchall()
                    if rows:
                        broker=connection();channel=broker.channel();channel.confirm_delivery()
                        import pika
                        for event,kind,payload in rows:
                            channel.basic_publish('hydrosmart.events',kind,json.dumps(payload).encode(),
                                properties=pika.BasicProperties(message_id=str(event),content_type='application/json',delivery_mode=2),mandatory=True)
                            conn.execute('UPDATE outbox_events SET published_at=now(),attempts=attempts+1 WHERE event_id=%s',(event,))
            except Exception:logger.warning('Analytics outbox will retry unpublished events')
            finally:
                if broker is not None and broker.is_open:
                    try:broker.close()
                    except Exception:pass
            self.stop_event.wait(.5)

