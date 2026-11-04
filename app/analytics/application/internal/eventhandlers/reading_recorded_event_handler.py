from ....domain.model.commands.record_consumption_command import RecordConsumptionCommand
from ....domain.model.entities.reading_recorded import ReadingRecorded
from ....domain.services.consumption_command_service import ConsumptionCommandService

class ReadingRecordedEventHandler:
    def __init__(self, commands: ConsumptionCommandService):
        self.commands = commands

    def handle(self, reading: ReadingRecorded) -> bool:
        return self.commands.handle(RecordConsumptionCommand(reading))

