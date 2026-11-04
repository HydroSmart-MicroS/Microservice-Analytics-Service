ALTER TABLE savings_goals ADD COLUMN unit_id UUID;
ALTER TABLE savings_goals ADD COLUMN notified_80 BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE savings_goals DROP CONSTRAINT IF EXISTS savings_goals_user_id_month_key;
CREATE UNIQUE INDEX goal_user_unit_month ON savings_goals(user_id,unit_id,month);
ALTER TABLE alert_rules ADD COLUMN settings JSONB NOT NULL DEFAULT '{}';
CREATE UNIQUE INDEX rule_unit_kind ON alert_rules(unit_id,kind) WHERE unit_id IS NOT NULL;
ALTER TABLE alerts ADD COLUMN fingerprint TEXT UNIQUE;
CREATE TABLE alert_samples (
 reading_id UUID PRIMARY KEY,unit_id UUID NOT NULL,device_id UUID NOT NULL,
 liters NUMERIC(18,6) NOT NULL,interval_seconds INTEGER NOT NULL,measured_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX samples_unit_time ON alert_samples(unit_id,measured_at DESC);
CREATE INDEX samples_device_time ON alert_samples(device_id,measured_at DESC);
CREATE TABLE monitoring_inbox(event_id UUID PRIMARY KEY,processed_at TIMESTAMPTZ NOT NULL DEFAULT now());
