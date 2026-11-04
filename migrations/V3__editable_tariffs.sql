ALTER TABLE tariff_versions ADD COLUMN category TEXT NOT NULL DEFAULT 'domestic' CHECK (category IN ('domestic','commercial'));
ALTER TABLE tariff_versions ADD COLUMN owner_user_id TEXT;
ALTER TABLE tariff_tiers ADD COLUMN sewer_price_per_m3 NUMERIC(12,6) NOT NULL DEFAULT 0 CHECK (sewer_price_per_m3 >= 0);
CREATE TABLE unit_tariffs (
    unit_id UUID PRIMARY KEY,
    tariff_id UUID NOT NULL REFERENCES tariff_versions(id)
);
-- User-supplied demonstration prices, not an official SEDAPAL tariff.
INSERT INTO tariff_versions (id,name,effective_from,category) VALUES
('10000000-0000-4000-8000-000000000001','Referencia doméstica', '2026-01-01','domestic'),
('10000000-0000-4000-8000-000000000002','Referencia comercial', '2026-01-01','commercial');
INSERT INTO tariff_tiers (tariff_id,from_m3,to_m3,price_per_m3,sewer_price_per_m3) VALUES
('10000000-0000-4000-8000-000000000001',0,10,1.50,0.80),
('10000000-0000-4000-8000-000000000001',10,20,2.30,1.10),
('10000000-0000-4000-8000-000000000001',20,NULL,4.50,2.10),
('10000000-0000-4000-8000-000000000002',0,NULL,6.20,3.00);
