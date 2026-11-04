from uuid import uuid4
from datetime import datetime
from zoneinfo import ZoneInfo
from ....domain.model.aggregates.tariff import Tariff
from ....domain.services.tariff_repository import TariffRepository
from ....domain.services.monitoring_gateway import MonitoringGateway

class TariffCommandServiceImpl:
    def __init__(self, repository: TariffRepository, gateway: MonitoringGateway):
        self.repository, self.gateway = repository, gateway

    def handle(self, unit_id, token, user_id, tariff: Tariff):
        access = self.gateway.access(unit_id, token)
        if access['ownerUserId'] != user_id:
            raise PermissionError('Solo el propietario puede editar la tarifa.')
        month=datetime.now(ZoneInfo('America/Lima')).date().replace(day=1)
        effective=tariff.effective_from or month
        if effective.day!=1 or effective<month:raise ValueError('La tarifa debe comenzar el primer día del mes actual o de un mes futuro. Los meses cerrados se conservan.')
        private = Tariff(str(uuid4()), tariff.name, tariff.category, tariff.tiers, tariff.fixed_charge, user_id, tariff.tax_rate,effective_from=effective).validate()
        return self.repository.save(unit_id, private)
