import os
import pika
class RabbitBrokerHealthProbe:
    def diagnostics(self):
        params=pika.URLParameters(os.environ['RABBITMQ_URL'])
        params.socket_timeout=1.5;params.stack_timeout=2;params.blocked_connection_timeout=1.5
        params.connection_attempts=1
        with pika.BlockingConnection(params) as connection:
            channel=connection.channel()
            channel.exchange_declare(exchange='hydrosmart.rpc',passive=True)
            channel.exchange_declare(exchange='hydrosmart.events',passive=True)
            channel.confirm_delivery()
            consumers={queue:'UP' if channel.queue_declare(queue=queue,passive=True).method.consumer_count>0 else 'DOWN' for queue in ('rpc.analytics','analytics.readings','analytics.monitoring')}
            return {'ready':all(v=='UP' for v in consumers.values()),'connection':'UP','publisherChannel':'READY','consumers':consumers}
