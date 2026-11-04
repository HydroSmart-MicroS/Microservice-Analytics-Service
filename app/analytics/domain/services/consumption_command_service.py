from typing import Protocol
from ..model.commands.record_consumption_command import RecordConsumptionCommand

class ConsumptionCommandService(Protocol):
    def handle(self, command: RecordConsumptionCommand) -> bool: ...
