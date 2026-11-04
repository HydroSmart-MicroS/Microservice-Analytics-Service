from ....domain.model.aggregates.unit_daily_consumption import UnitDailyConsumption
from ....domain.model.commands.record_consumption_command import RecordConsumptionCommand
from ....domain.services.consumption_repository import ConsumptionRepository

class ConsumptionCommandServiceImpl:
    def __init__(self, repository: ConsumptionRepository):
        self.repository = repository

    def handle(self, command: RecordConsumptionCommand) -> bool:
        daily = UnitDailyConsumption.from_reading(command.reading)
        return self.repository.record_once(command.reading, daily)
