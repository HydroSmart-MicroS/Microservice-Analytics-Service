from datetime import timedelta
from decimal import Decimal
from ....domain.services.tariff_repository import TariffRepository
from ..outboundservices.monitoring_dependencies import MonitoringDependencies
from .historical_estimate import estimate_history

class InternalEstimateQueryServiceImpl:
    def __init__(self,tariffs:TariffRepository,dependencies:MonitoringDependencies):
        self.tariffs,self.dependencies=tariffs,dependencies

    def handle(self,unit_id,start,end):
        if start.tzinfo is None or end.tzinfo is None or not start<end or end-start>timedelta(days=366):raise ValueError('Período inválido.')
        snapshot=self.dependencies.snapshot(unit_id)
        if snapshot is None:raise LookupError('Unidad no encontrada.')
        result=self.dependencies.consumption(unit_id,start.isoformat(),end.isoformat())
        tariff=self.tariffs.current(unit_id,snapshot['ownerUserId'])
        result['estimate']=estimate_history(self.tariffs,unit_id,snapshot['ownerUserId'],result.get('daily',[]),tariff)
        versions=result['estimate']['months']
        result['tariffName']=versions[0]['tariffName'] if len({v['tariffId'] for v in versions})==1 else 'Tarifas del período' if versions else tariff.name
        result['unitName']=snapshot.get('name','Unidad seleccionada')
        names={str(device['id']):device['name'] for device in snapshot.get('devices',[])}
        for row in result.get('daily',[]):row['deviceName']=names.get(row['deviceId'],row['deviceId'])
        return result
