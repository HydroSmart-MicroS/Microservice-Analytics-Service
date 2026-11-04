from .....domain.model.aggregates.tariff import Tariff, Tier
from datetime import datetime, date
from zoneinfo import ZoneInfo
from ......shared.infrastructure.persistence.postgresql.connection_pool import connect

class PgTariffRepository:
    def current(self, unit_id, owner_id, category='domestic', reference=False):
        return self._at(unit_id,owner_id,datetime.now(ZoneInfo('America/Lima')).date(),category,reference)

    def for_month(self,unit_id,owner_id,month):
        return self._at(unit_id,owner_id,date.fromisoformat(month+'-01'))

    def history(self,unit_id,owner_id):
        with connect() as conn:
            rows=conn.execute('''SELECT p.effective_month,v.name,p.legacy_snapshot,v.category,v.fixed_charge,v.tax_rate
                FROM unit_tariff_periods p JOIN tariff_versions v ON v.id=p.tariff_id
                WHERE p.unit_id=%s AND v.owner_user_id=%s ORDER BY p.effective_month DESC''',(unit_id,owner_id)).fetchall()
            return [{'effectiveFrom':None if r[2] else r[0].isoformat(),'name':r[1],'legacySnapshot':r[2],
                     'category':r[3],'fixedCharge':str(r[4]),'taxRate':str(r[5])} for r in rows]

    def _at(self,unit_id,owner_id,at,category='domestic',reference=False):
        with connect() as conn:
            row = None if reference else conn.execute('''SELECT v.id,v.name,v.category,v.fixed_charge,v.owner_user_id,v.tax_rate,v.source_url,v.source_date,u.effective_month FROM unit_tariff_periods u
                JOIN tariff_versions v ON v.id=u.tariff_id WHERE u.unit_id=%s AND v.owner_user_id=%s AND u.effective_month<=%s ORDER BY u.effective_month DESC LIMIT 1''', (unit_id,owner_id,at)).fetchone()
            if row is None:
                row = conn.execute('''SELECT id,name,category,fixed_charge,owner_user_id,tax_rate,source_url,source_date,effective_from FROM tariff_versions
                    WHERE owner_user_id IS NULL AND category=%s AND effective_from<=%s AND (effective_until IS NULL OR effective_until>%s) ORDER BY effective_from DESC,id DESC LIMIT 1''', (category,at,at)).fetchone()
            if row is None:
                raise ValueError('No hay una tarifa de referencia disponible para esta categoría.')
            tiers = conn.execute('SELECT from_m3,to_m3,price_per_m3,sewer_price_per_m3 FROM tariff_tiers WHERE tariff_id=%s ORDER BY from_m3', (row[0],)).fetchall()
            return Tariff(str(row[0]),row[1],row[2],tuple(Tier(*t) for t in tiers),row[3],row[4],row[5],row[6],row[7].isoformat() if row[7] else None,row[8])

    def save(self, unit_id, tariff):
        with connect() as conn:
            conn.execute('''INSERT INTO tariff_versions(id,name,category,owner_user_id,effective_from,fixed_charge,tax_rate)
                VALUES (%s,%s,%s,%s,%s,%s,%s)''', (tariff.id,tariff.name,tariff.category,tariff.owner_user_id,tariff.effective_from,tariff.fixed_charge,tariff.tax_rate))
            for tier in tariff.tiers:
                conn.execute('''INSERT INTO tariff_tiers(tariff_id,from_m3,to_m3,price_per_m3,sewer_price_per_m3)
                    VALUES (%s,%s,%s,%s,%s)''', (tariff.id,tier.start,tier.end,tier.water,tier.sewer))
            conn.execute('''INSERT INTO unit_tariff_periods(unit_id,effective_month,tariff_id) VALUES(%s,%s,%s) ON CONFLICT(unit_id,effective_month) DO UPDATE SET tariff_id=excluded.tariff_id,recorded_at=now()''',(unit_id,tariff.effective_from,tariff.id))
            conn.execute('''INSERT INTO unit_tariffs(unit_id,tariff_id) VALUES (%s,%s)
                ON CONFLICT(unit_id) DO UPDATE SET tariff_id=EXCLUDED.tariff_id''', (unit_id,tariff.id))
        return tariff
