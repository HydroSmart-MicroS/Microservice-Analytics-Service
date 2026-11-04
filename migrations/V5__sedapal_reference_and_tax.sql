ALTER TABLE tariff_versions ADD COLUMN tax_rate NUMERIC(5,4) NOT NULL DEFAULT 0 CHECK (tax_rate BETWEEN 0 AND 1);
ALTER TABLE tariff_versions ADD COLUMN source_url TEXT;
ALTER TABLE tariff_versions ADD COLUMN source_date DATE;

-- Retire only the old global examples. Private tariffs and issued payment orders keep their values.
UPDATE tariff_versions SET effective_until=GREATEST(CURRENT_DATE,effective_from+1)
WHERE owner_user_id IS NULL AND id IN ('10000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000002');

INSERT INTO tariff_versions (id,name,effective_from,category,fixed_charge,tax_rate,source_url,source_date) VALUES
('10000000-0000-4000-8000-000000000003','Sedapal · doméstico Grupo 1 (23/12/2025)','2025-12-23','domestic',6.30,0.18,'https://www.gob.pe/institucion/sedapal/informes-publicaciones/3989288-estructura-tarifaria','2025-12-23'),
('10000000-0000-4000-8000-000000000004','Sedapal · comercial (23/12/2025)','2025-12-23','commercial',6.30,0.18,'https://www.gob.pe/institucion/sedapal/informes-publicaciones/3989288-estructura-tarifaria','2025-12-23');

INSERT INTO tariff_tiers (tariff_id,from_m3,to_m3,price_per_m3,sewer_price_per_m3) VALUES
('10000000-0000-4000-8000-000000000003',0,10,2.20,1.38),
('10000000-0000-4000-8000-000000000003',10,20,2.36,1.48),
('10000000-0000-4000-8000-000000000003',20,50,3.22,1.98),
('10000000-0000-4000-8000-000000000003',50,NULL,7.32,3.49),
('10000000-0000-4000-8000-000000000004',0,1000,8.82,4.21),
('10000000-0000-4000-8000-000000000004',1000,NULL,9.46,4.51);
