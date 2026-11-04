import json
import logging
import threading
import pika
import psycopg
from typing import Callable

logger = logging.getLogger(__name__)

class ReadingConsumer:
    def __init__(self, url: str, handler: Callable[[bytes], bool], queue="analytics.readings"):
        self.url = url
        self.queue = queue
        self.handler = handler
        self.connected = threading.Event()
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, name="analytics-readings", daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stopped.set()
        self.thread.join(timeout=8)

    def _run(self):
        while not self.stopped.is_set():
            connection = None
            try:
                parameters = pika.URLParameters(self.url)
                parameters.heartbeat = 30
                parameters.socket_timeout = 5
                parameters.blocked_connection_timeout = 5
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                channel.basic_qos(prefetch_count=20)
                channel.basic_consume(queue=self.queue, on_message_callback=self._receive, auto_ack=False)
                self.connected.set()
                while not self.stopped.is_set():
                    connection.process_data_events(time_limit=1)
            except Exception:
                logger.warning("Reading consumer disconnected; uncommitted events will be redelivered")
            finally:
                self.connected.clear()
                if connection is not None and connection.is_open:
                    try:
                        connection.close()
                    except Exception:
                        pass
            self.stopped.wait(2)

    def _receive(self, channel, method, properties, body):
        try:
            self.handler(body)
        except (ValueError, KeyError, TypeError, AttributeError, OverflowError, psycopg.DataError):
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            logger.warning("Malformed reading event sent to dead-letter queue")
            return
        # Database failures leave the delivery unacknowledged. The outer loop closes
        # the connection and backs off before RabbitMQ redelivers.
        event=json.loads(body)
        logging.getLogger('uvicorn.error').info(json.dumps({'event':'message_consumed','service':'analytics','queue':self.queue,'eventId':event.get('event_id'),'eventType':event.get('event_type')}))
        channel.basic_ack(delivery_tag=method.delivery_tag)
