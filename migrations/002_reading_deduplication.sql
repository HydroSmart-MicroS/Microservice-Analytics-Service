-- Deduplicate reading identities even if an event is republished with another event_id.
CREATE TABLE processed_readings (
    reading_id UUID PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE REFERENCES processed_events(event_id),
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
