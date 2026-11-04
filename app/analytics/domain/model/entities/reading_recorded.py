from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True)
class ReadingRecorded:
    event_id: UUID
    reading_id: UUID
    unit_id: UUID
    device_id: UUID
    volume_ml: int
    interval_seconds: int
    measured_at: datetime
