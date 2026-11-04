from typing import Protocol
from ..model.entities.reading_recorded import ReadingRecorded
from ..model.aggregates.unit_daily_consumption import UnitDailyConsumption

class ConsumptionRepository(Protocol):
    def record_once(self, reading: ReadingRecorded, daily: UnitDailyConsumption) -> bool: ...
