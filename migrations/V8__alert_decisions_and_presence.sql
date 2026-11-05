ALTER TABLE alerts DROP CONSTRAINT alerts_status_check;
ALTER TABLE alerts ADD CONSTRAINT alerts_status_check CHECK(status IN('open','resolved','confirmed','dismissed'));
ALTER TABLE alerts DROP CONSTRAINT alerts_kind_check;
ALTER TABLE alerts ADD CONSTRAINT alerts_kind_check CHECK(kind IN('high_consumption','possible_leak','meter_offline'));
CREATE TABLE device_presence(
 device_id UUID PRIMARY KEY,unit_id UUID NOT NULL,last_seen_at TIMESTAMPTZ NOT NULL,
 offline_notified BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX device_presence_due ON device_presence(last_seen_at) WHERE NOT offline_notified;
-- A deployment must not replay an old monetary threshold as a new liters notice.
-- Existing notified_80 flags remain unchanged; new/edited goals use liters.
