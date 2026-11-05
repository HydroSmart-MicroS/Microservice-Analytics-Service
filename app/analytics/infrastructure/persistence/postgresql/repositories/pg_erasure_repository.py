from ......shared.infrastructure.persistence.postgresql.connection_pool import connect
from ......shared.infrastructure.privacy import gate

def unit_erased(conn,unit):
    return conn.execute("SELECT 1 FROM privacy_units WHERE unit_hash=encode(sha256(convert_to(%s,'UTF8')),'hex')",(str(unit),)).fetchone() is not None

def erase(user,units):
    with gate.write(),connect() as conn:
        if conn.execute("SELECT 1 FROM privacy_receipts WHERE user_hash=encode(sha256(convert_to(%s,'UTF8')),'hex')",(user,)).fetchone():return
        conn.execute('DELETE FROM alerts WHERE user_id=%s OR rule_id IN(SELECT id FROM alert_rules WHERE user_id=%s)',(user,user))
        for table in ('alert_rules','savings_goals','recommendations'):
            conn.execute(f'DELETE FROM {table} WHERE user_id=%s',(user,))
        for unit in units:
            conn.execute("INSERT INTO privacy_units VALUES(encode(sha256(convert_to(%s,'UTF8')),'hex')) ON CONFLICT DO NOTHING",(unit,))
            for table in ('alerts','alert_rules','savings_goals','recommendations','alert_samples','device_presence','unit_daily_consumption','unit_tariffs','unit_tariff_periods'):
                conn.execute(f'DELETE FROM {table} WHERE unit_id=%s',(unit,))
            conn.execute('DELETE FROM outbox_events WHERE strpos(payload::text,%s)>0',(unit,))
        conn.execute('DELETE FROM tariff_tiers WHERE tariff_id IN(SELECT id FROM tariff_versions WHERE owner_user_id=%s)',(user,))
        conn.execute('DELETE FROM tariff_versions WHERE owner_user_id=%s',(user,))
        conn.execute('DELETE FROM outbox_events WHERE aggregate_id=%s OR strpos(payload::text,%s)>0',(user,user))
        conn.execute("INSERT INTO privacy_receipts VALUES(encode(sha256(convert_to(%s,'UTF8')),'hex'),now()+interval '365 days')",(user,))
        conn.execute('DELETE FROM privacy_receipts WHERE expires_at<=now()')

class PgAccountErasureRepository:
    def erase(self,user,units):erase(user,units)
