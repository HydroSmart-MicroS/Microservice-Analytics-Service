from ...application.internal.eventhandlers.reading_recorded_event_handler import ReadingRecordedEventHandler
from .transform.reading_recorded_from_resource_assembler import from_resource

class ReadingEventsController:
    def __init__(self, handler: ReadingRecordedEventHandler):
        self.handler = handler

    def handle(self, body: bytes) -> bool:
        return self.handler.handle(from_resource(body))

