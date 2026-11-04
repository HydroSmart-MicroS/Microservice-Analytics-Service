import os
from urllib.parse import urlencode
from fastapi import HTTPException

from ....shared.infrastructure.messaging.rabbitmq import json_rpc, BrokerUnavailable

def get(base,path,token):
    service='properties' if 'properties' in base else 'telemetry'
    try:
        status,result=json_rpc(service,path,token)
        if status!=200: raise HTTPException(status if status in (400,401,403,404) else 503,'No se pudo consultar la unidad o sus lecturas.')
        return result
    except BrokerUnavailable:
        raise HTTPException(503,'La comunicación por RabbitMQ no está disponible.')

class MonitoringContextFacade:
    def access(self, unit_id, token):
        return get(os.environ.get('PROPERTIES_INTERNAL_URL','http://properties:8080'), '/internal/v1/units/'+unit_id+'/access', token)

    def consumption(self, unit_id, token, start, end):
        return get(os.environ.get('TELEMETRY_INTERNAL_URL','http://telemetry:8080'), '/api/v1/consumption/daily?'+urlencode({'unitId':unit_id,'from':start,'to':end}), token)
