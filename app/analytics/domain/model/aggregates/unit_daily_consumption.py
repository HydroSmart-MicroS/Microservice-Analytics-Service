from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo
from ..entities.reading_recorded import ReadingRecorded

@dataclass(frozen=True)
class UnitDailyConsumption:
    unit_id: UUID
    local_date: date
    liters: Decimal

    @staticmethod
    def from_reading(reading: ReadingRecorded):
        return UnitDailyConsumption(
            reading.unit_id, reading.measured_at.astimezone(ZoneInfo("America/Lima")).date(),
            Decimal(reading.volume_ml) / Decimal(1000))
