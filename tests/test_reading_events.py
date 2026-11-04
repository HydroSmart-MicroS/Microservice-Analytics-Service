import json
import unittest
from uuid import uuid4
from datetime import date
from decimal import Decimal
from app.analytics.interfaces.messaging.transform.reading_recorded_from_resource_assembler import from_resource
from app.analytics.domain.model.aggregates.unit_daily_consumption import UnitDailyConsumption

class ReadingEventTest(unittest.TestCase):
    def event(self):
        return {"event_id":str(uuid4()),"event_type":"telemetry.reading.recorded.v1","occurred_at":"2026-10-24T03:00:01Z",
                "producer":"telemetry","data":{"reading_id":str(uuid4()),"device_id":str(uuid4()),"unit_id":str(uuid4()),
                "volume_ml":1250,"interval_seconds":60,"measured_at":"2026-10-24T03:00:00Z"}}

    def test_lima_day_and_exact_volume(self):
        reading=from_resource(json.dumps(self.event()).encode())
        daily=UnitDailyConsumption.from_reading(reading)
        self.assertEqual(daily.local_date,date(2026,10,23))
        self.assertEqual(daily.liters,Decimal("1.25"))

    def test_boolean_volume_and_missing_timezone_are_invalid(self):
        for volume in [True,-1,"1250"]:
            event=self.event();event["data"]["volume_ml"]=volume
            with self.assertRaises(ValueError):
                from_resource(json.dumps(event).encode())
        event=self.event();event["data"]["measured_at"]="2026-10-24T03:00:00"
        with self.assertRaises(ValueError):
            from_resource(json.dumps(event).encode())

    def test_unknown_event_and_injected_fields_are_invalid(self):
        event=self.event();event["event_type"]="another.event"
        with self.assertRaises(ValueError):from_resource(json.dumps(event).encode())
        event=self.event();event["data"]["owner_user_id"]="forged"
        with self.assertRaises(ValueError):from_resource(json.dumps(event).encode())

