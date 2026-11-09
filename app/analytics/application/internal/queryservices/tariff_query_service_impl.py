from dataclasses import replace
from decimal import Decimal

from ....domain.services.tariff_repository import TariffRepository
from ....domain.services.monitoring_gateway import MonitoringGateway

class TariffQueryServiceImpl:
    def __init__(self, repository: TariffRepository, gateway: MonitoringGateway):
        self.repository,self.gateway=repository,gateway

    def current(self,unit_id,token,category='domestic',reference=False):
        access=self.gateway.access(unit_id,token)
        return self.repository.current(unit_id,access['ownerUserId'],category,reference)

    def estimate(self,unit_id,token,liters,category='domestic',reference=False):
        tariff=self.current(unit_id,token,category,reference)
        preview_tariff = replace(tariff, fixed_charge=Decimal(0)) if liters == 0 else tariff
        return tariff,preview_tariff.estimate(liters)

    def history(self,unit_id,token):
        access=self.gateway.access(unit_id,token)
        return self.repository.history(unit_id,access['ownerUserId'])
