import json
from datetime import datetime
from uuid import UUID
from ....domain.model.entities.reading_recorded import ReadingRecorded

def from_resource(body: bytes, expected_type="telemetry.reading.recorded.v1", expected_producer="telemetry") -> ReadingRecorded:
    if len(body) > 16384:
        raise ValueError("Event too large")
    event = json.loads(body)
    if not isinstance(event, dict) or set(event)-{"schema_version"} != {"event_id", "event_type", "occurred_at", "producer", "data"}:
        raise ValueError("Invalid event envelope")
    if "schema_version" in event and (type(event["schema_version"]) is not int or event["schema_version"] != 1):
        raise ValueError("Unsupported event schema")
    if event["event_type"] != expected_type or event["producer"] != expected_producer:
        raise ValueError("Unsupported event")
    occurred = datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00"))
    if occurred.utcoffset() is None:
        raise ValueError("Timezone required")
    data = event["data"]
    expected = {"reading_id", "device_id", "unit_id", "volume_ml", "interval_seconds", "measured_at"}
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("Invalid event data")
    if type(data["volume_ml"]) is not int or not 0 <= data["volume_ml"] <= 2**63-1:
        raise ValueError("Invalid volume")
    if type(data["interval_seconds"]) is not int or data["interval_seconds"] < 1:
        raise ValueError("Invalid interval")
    measured = datetime.fromisoformat(data["measured_at"].replace("Z", "+00:00"))
    if measured.utcoffset() is None:
        raise ValueError("Timezone required")
    identifiers = [UUID(event["event_id"]), UUID(data["reading_id"]), UUID(data["unit_id"]), UUID(data["device_id"])]
    if any(value.int == 0 for value in identifiers):
        raise ValueError("Invalid identifier")
    return ReadingRecorded(*identifiers, data["volume_ml"], data["interval_seconds"], measured)
