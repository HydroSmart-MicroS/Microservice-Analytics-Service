CREATE TABLE savings_goals (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    month DATE NOT NULL CHECK (EXTRACT(DAY FROM month) = 1),
    budget_amount NUMERIC(12,2) CHECK (budget_amount >= 0),
    target_liters NUMERIC(18,6) CHECK (target_liters >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'PEN' CHECK (currency = 'PEN'),
    CHECK (budget_amount IS NOT NULL OR target_liters IS NOT NULL),
    UNIQUE (user_id, month)
);
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    unit_id UUID,
    kind TEXT NOT NULL CHECK (kind IN ('high_consumption','possible_leak')),
    threshold_liters NUMERIC(18,6) NOT NULL CHECK (threshold_liters > 0),
    window_seconds INTEGER NOT NULL CHECK (window_seconds > 0),
    enabled BOOLEAN NOT NULL DEFAULT true
);
CREATE TABLE alerts (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    unit_id UUID NOT NULL,
    device_id UUID,
    rule_id UUID REFERENCES alert_rules(id),
    kind TEXT NOT NULL CHECK (kind IN ('high_consumption','possible_leak')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved')),
    details JSONB NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ
);
CREATE INDEX alerts_user_idx ON alerts (user_id, detected_at DESC);
CREATE TABLE unit_daily_consumption (
    unit_id UUID NOT NULL,
    local_date DATE NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'America/Lima',
    liters NUMERIC(18,6) NOT NULL CHECK (liters >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (unit_id, local_date)
);
CREATE TABLE recommendations (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    unit_id UUID,
    rule_code TEXT NOT NULL,
    message TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE tariff_versions (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'PEN' CHECK (currency = 'PEN'),
    effective_from DATE NOT NULL,
    effective_until DATE,
    fixed_charge NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (fixed_charge >= 0),
    CHECK (effective_until IS NULL OR effective_until > effective_from)
);
CREATE TABLE tariff_tiers (
    tariff_id UUID NOT NULL REFERENCES tariff_versions(id),
    from_m3 NUMERIC(12,3) NOT NULL CHECK (from_m3 >= 0),
    to_m3 NUMERIC(12,3),
    price_per_m3 NUMERIC(12,6) NOT NULL CHECK (price_per_m3 >= 0),
    CHECK (to_m3 IS NULL OR to_m3 > from_m3),
    PRIMARY KEY (tariff_id, from_m3)
);
-- Fórmula y tarifa comercial pendientes de confirmación: no se cargan valores inventados.


CREATE TABLE outbox_events (
    event_id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0)
);
CREATE INDEX outbox_pending_idx ON outbox_events (occurred_at) WHERE published_at IS NULL;
CREATE TABLE processed_events (
    event_id UUID PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
