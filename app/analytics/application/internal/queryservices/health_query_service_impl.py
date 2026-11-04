from ..outboundservices.database_probe import DatabaseProbe
from ..outboundservices.broker_probe import BrokerProbe
import time

class HealthQueryServiceImpl:
    def __init__(self, consumers, database: DatabaseProbe, broker: BrokerProbe):
        self.consumers,self.database,self.broker=consumers,database,broker

    def ready(self) -> bool:
        return all(c['status']=='UP' for c in self.components().values())

    def components(self)->dict:
        start=time.monotonic()
        try:database=self.database.ready()
        except Exception:database=False
        components={'database':{'status':'UP' if database else 'DOWN','details':{'type':'PostgreSQL','check':'SELECT 1','message':'La base de datos responde.' if database else 'No se pudo consultar la base de datos; revisa su disponibilidad y acceso.','durationMs':round((time.monotonic()-start)*1000,2)}}}
        start=time.monotonic()
        consumers={name:'UP' if consumer.connected.is_set() else 'DOWN' for name,consumer in self.consumers.items()}
        try:
            details=self.broker.diagnostics()
            ready=details.pop('ready') and all(v=='UP' for v in consumers.values())
            details.update(workers=consumers,message='Conexión, canal y consumidores disponibles.' if ready else 'El broker responde, pero falta un consumidor requerido.')
        except Exception:
            ready=False;details={'workers':consumers,'message':'No se pudo comprobar RabbitMQ; revisa la conexión, permisos y las colas del servicio.'}
        details['durationMs']=round((time.monotonic()-start)*1000,2)
        components['rabbitmq']={'status':'UP' if ready else 'DOWN','details':details}
        return components

