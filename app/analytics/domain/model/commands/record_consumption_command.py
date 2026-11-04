from dataclasses import dataclass
from ..entities.reading_recorded import ReadingRecorded

@dataclass(frozen=True)
class RecordConsumptionCommand:
    reading: ReadingRecorded
