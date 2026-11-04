CREATE TABLE unit_tariff_periods (
 unit_id UUID NOT NULL,effective_month DATE NOT NULL,tariff_id UUID NOT NULL REFERENCES tariff_versions(id),
 legacy_snapshot BOOLEAN NOT NULL DEFAULT false,recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(unit_id,effective_month),CHECK(extract(day FROM effective_month)=1)
);
-- Previous assignments were not recorded. Preserve the previous estimation baseline,
-- marking it as a snapshot rather than inventing historical changes.
INSERT INTO unit_tariff_periods(unit_id,effective_month,tariff_id,legacy_snapshot)
SELECT unit_id,'1900-01-01',tariff_id,true FROM unit_tariffs;
