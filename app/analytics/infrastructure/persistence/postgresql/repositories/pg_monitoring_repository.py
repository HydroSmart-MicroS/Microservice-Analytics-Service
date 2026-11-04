import json
from decimal import Decimal
from uuid import uuid4
from datetime import datetime,timezone
from ......shared.infrastructure.persistence.postgresql.connection_pool import connect as database_connection

DEFAULT_RULES={'highEnabled':True,'thresholdLiters':'100','windowSeconds':3600,'leakEnabled':True,
              'leakWindowSeconds':180,'normalStartHour':6,'normalEndHour':22,'leakAllDay':False,'cooldownSeconds':1800}

def connect():return database_connection(dict_rows=True)
def outbox(conn,kind,user_id,data):
    event=str(uuid4())
    payload={'event_id':event,'event_type':kind,'schema_version':1,'producer':'analytics','occurred_at':datetime.now(timezone.utc).isoformat(),'data':{'user_id':user_id,**data}}
    conn.execute('INSERT INTO outbox_events(event_id,event_type,aggregate_id,payload) VALUES(%s,%s,%s,%s::jsonb)',(event,kind,user_id,json.dumps(payload,default=str)))

class PgMonitoringRepository:
    def rules(self,unit,owner):
        with connect() as conn:
            row=conn.execute("SELECT settings FROM alert_rules WHERE unit_id=%s AND kind='high_consumption'",(unit,)).fetchone()
            return {**DEFAULT_RULES,**(row['settings'] if row else {})}
    def save_rules(self,unit,owner,settings):
        with connect() as conn:
            for kind in ('high_consumption','possible_leak'):
                conn.execute('''INSERT INTO alert_rules(id,user_id,unit_id,kind,threshold_liters,window_seconds,enabled,settings)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(unit_id,kind) WHERE unit_id IS NOT NULL DO UPDATE
                 SET threshold_liters=excluded.threshold_liters,window_seconds=excluded.window_seconds,enabled=excluded.enabled,settings=excluded.settings''',
                 (str(uuid4()),owner,unit,kind,settings['thresholdLiters'],settings['windowSeconds'] if kind=='high_consumption' else settings['leakWindowSeconds'],
                  settings['highEnabled'] if kind=='high_consumption' else settings['leakEnabled'],json.dumps(settings,default=str)))
            outbox(conn,'analytics.rules.updated.v1',owner,{'unit_id':unit,'settings':settings})
        return settings
    def save_goal(self,user,unit,month,budget,target):
        with connect() as conn:
            row=conn.execute('''INSERT INTO savings_goals(id,user_id,unit_id,month,budget_amount,target_liters)
                VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,unit_id,month) DO UPDATE SET budget_amount=excluded.budget_amount,
                target_liters=excluded.target_liters,notified_80=CASE WHEN savings_goals.budget_amount=excluded.budget_amount THEN savings_goals.notified_80 ELSE false END
                RETURNING *''',(str(uuid4()),user,unit,month,budget,target)).fetchone()
            outbox(conn,'analytics.goal.saved.v1',user,{'goal_id':str(row['id']),'unit_id':unit,'month':month,'budget':str(budget),'target_liters':str(target)})
            return row
    def goals(self,user,unit,month):
        with connect() as conn:return conn.execute('SELECT * FROM savings_goals WHERE user_id=%s AND unit_id=%s AND month=%s',(user,unit,month)).fetchall()
    def alerts(self,user,unit):
        with connect() as conn:return conn.execute('SELECT * FROM alerts WHERE user_id=%s AND unit_id=%s ORDER BY detected_at DESC LIMIT 100',(user,unit)).fetchall()
    def resolve(self,user,alert):
        with connect() as conn:return conn.execute("UPDATE alerts SET status='resolved',resolved_at=now() WHERE id=%s AND user_id=%s RETURNING id",(alert,user)).fetchone() is not None
    def publish_goal_threshold(self,goal,progress):
        if progress['percent']<80:return
        with connect() as conn:
            row=conn.execute('UPDATE savings_goals SET notified_80=true WHERE id=%s AND notified_80=false RETURNING id',(goal['id'],)).fetchone()
            if row:
                outbox(conn,'analytics.goal.threshold.v1',goal['user_id'],{'goal_id':str(goal['id']),'unit_id':str(goal['unit_id']),
                   'kind':'goal_80','title':'Tu meta mensual llegó al 80%','body':'Llevas S/'+progress['cost']+' de tu presupuesto de S/'+str(goal['budget_amount'])+'.','progress':progress})


    def monitoring_processed(self,event):
        with connect() as conn:return conn.execute('SELECT 1 FROM monitoring_inbox WHERE event_id=%s',(event,)).fetchone() is not None
    def mark_monitoring(self,event):
        with connect() as conn:conn.execute('INSERT INTO monitoring_inbox(event_id) VALUES(%s) ON CONFLICT DO NOTHING',(event,))
    def store_sample(self,reading):
        with connect() as conn:
            conn.execute('INSERT INTO alert_samples(reading_id,unit_id,device_id,liters,interval_seconds,measured_at) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                (reading.reading_id,reading.unit_id,reading.device_id,Decimal(reading.volume_ml)/1000,reading.interval_seconds,reading.measured_at))
            conn.execute("DELETE FROM alert_samples WHERE measured_at<now()-interval '2 days'")
    def samples(self,unit,start,end,device=None):
        with connect() as conn:
            sql='SELECT * FROM alert_samples WHERE unit_id=%s AND measured_at>=%s AND measured_at<=%s'
            args=[unit,start,end]
            if device:sql+=' AND device_id=%s';args.append(device)
            return conn.execute(sql+' ORDER BY measured_at,reading_id',args).fetchall()
    def goals_for_unit(self,unit):
        with connect() as conn:return conn.execute("SELECT * FROM savings_goals WHERE unit_id=%s AND month=date_trunc('month',now() AT TIME ZONE 'America/Lima')::date",(unit,)).fetchall()
    def add_alert(self,user,unit,device,kind,title,body,cooldown):
        import time
        scope=unit+':'+kind+':'+user
        fingerprint=scope+':'+str(int(time.time())//int(cooldown))
        with connect() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,61))',(scope,))
            if conn.execute("SELECT 1 FROM alerts WHERE user_id=%s AND unit_id=%s AND kind=%s AND detected_at>now()-(%s*interval '1 second') LIMIT 1",(user,unit,kind,int(cooldown))).fetchone():return
            alert=str(uuid4())
            row=conn.execute("INSERT INTO alerts(id,user_id,unit_id,device_id,kind,details,detected_at,fingerprint) VALUES(%s,%s,%s,%s,%s,%s::jsonb,now(),%s) ON CONFLICT(fingerprint) DO NOTHING RETURNING id",(alert,user,unit,device,kind,json.dumps({'title':title,'body':body}),fingerprint)).fetchone()
            if row:outbox(conn,'analytics.alert.generated.v1',user,{'alert_id':alert,'unit_id':unit,'device_id':device,'kind':kind,'title':title,'body':body})
