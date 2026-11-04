CREATE TABLE privacy_receipts(user_hash TEXT PRIMARY KEY,expires_at TIMESTAMPTZ NOT NULL);
CREATE TABLE privacy_units(unit_hash TEXT PRIMARY KEY);
