from .transform.reading_recorded_from_resource_assembler import from_resource
class MonitoringEventsController:
    def __init__(self,handler):self.handler=handler
    def handle(self,body):
        return self.handler.handle(from_resource(body,'analytics.consumption.updated.v1','analytics'))

