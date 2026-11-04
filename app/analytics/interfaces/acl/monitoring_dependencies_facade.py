from urllib.parse import urlencode
from fastapi import HTTPException
from ....shared.infrastructure.messaging.rabbitmq import json_rpc,BrokerUnavailable
class MonitoringDependenciesFacade:
    def access(self,unit,token):
        status,data=json_rpc('properties','/internal/v1/units/'+unit+'/access',token)
        if status!=200:raise HTTPException(status if status in (401,403,404) else 503,'No tienes acceso a esta unidad.')
        return data
    def snapshot(self,unit):
        status,data=json_rpc('properties','/internal/v1/units/'+unit+'/snapshot',internal=True)
        if status==404:return None
        if status!=200:raise BrokerUnavailable('Registry unavailable')
        return data
    def consumption(self,unit,start,end):
        status,data=json_rpc('telemetry','/internal/v1/consumption?'+urlencode({'unitId':unit,'from':start,'to':end}),internal=True)
        if status!=200:raise BrokerUnavailable('Consumption unavailable')
        return data

