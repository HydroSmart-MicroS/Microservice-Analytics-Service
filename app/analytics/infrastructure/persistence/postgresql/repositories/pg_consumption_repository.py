from ......shared.infrastructure.privacy import gate
from .pg_erasure_repository import unit_erased
import psycopg
import os
import json
from uuid import uuid5,NAMESPACE_URL
from datetime import datetime,timezone
from .....domain.model.entities.reading_recorded import ReadingRecorded
from .....domain.model.aggregates.unit_daily_consumption import UnitDailyConsumption
from ......shared.infrastructure.persistence.postgresql.connection_pool import connect

class PgConsumptionRepository:
    def ready(self) -> bool:
        try:
            with psycopg.connect(os.environ['DATABASE_URL'],connect_timeout=2,options='-c statement_timeout=1000',autocommit=True) as connection:
                connection.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False

    def record_once(self, reading: ReadingRecorded, daily: UnitDailyConsumption) -> bool:
        with gate.read(),connect() as connection:
            if unit_erased(connection,reading.unit_id):return False
            row = connection.execute(
                "INSERT INTO processed_events(event_id) VALUES(%s) ON CONFLICT DO NOTHING RETURNING event_id",
                (reading.event_id,)).fetchone()
            if row is None:
                return False
            row = connection.execute(
                "INSERT INTO processed_readings(reading_id,event_id) VALUES(%s,%s) ON CONFLICT DO NOTHING RETURNING reading_id",
                (reading.reading_id,reading.event_id)).fetchone()
            if row is None:
                return False
            connection.execute("""
                INSERT INTO unit_daily_consumption(unit_id,local_date,liters)
                VALUES(%s,%s,%s)
                ON CONFLICT(unit_id,local_date) DO UPDATE
                SET liters=unit_daily_consumption.liters+excluded.liters,updated_at=now()
                """, (daily.unit_id,daily.local_date,daily.liters))
            event_id=uuid5(NAMESPACE_URL,'analytics.consumption:'+str(reading.reading_id))
            payload={'event_id':str(event_id),'event_type':'analytics.consumption.updated.v1','schema_version':1,'producer':'analytics','occurred_at':datetime.now(timezone.utc).isoformat(),
                'data':{'reading_id':str(reading.reading_id),'unit_id':str(reading.unit_id),'device_id':str(reading.device_id),'volume_ml':reading.volume_ml,'interval_seconds':reading.interval_seconds,'measured_at':reading.measured_at.isoformat()}}
            connection.execute("INSERT INTO outbox_events(event_id,event_type,aggregate_id,payload) VALUES(%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING",(event_id,'analytics.consumption.updated.v1',str(reading.unit_id),json.dumps(payload)))
        return True
