from datetime import datetime


class DevicePresenceCommandService:
    def __init__(self,repository,dependencies):
        self.repository,self.dependencies=repository,dependencies

    def pending(self):
        # An unavailable ingestion service is an infrastructure incident, not 100 offline meters.
        return self.repository.offline_candidates() if self.dependencies.telemetry_ready() else []

    def check(self,row):
        snapshot=self.dependencies.snapshot(str(row['unit_id']))
        if not snapshot:
            self.repository.claim_offline(row['device_id'],row['last_seen_at']);return
        device=next((d for d in snapshot.get('devices',[]) if str(d['id'])==str(row['device_id'])),None)
        if not device or device.get('state')!='active':
            # Retired meters must not occupy every batch ahead of active ones.
            self.repository.claim_offline(row['device_id'],row['last_seen_at']);return
        if not self.repository.claim_offline(row['device_id'],row['last_seen_at']):return
        recipients=[{'userId':snapshot['ownerUserId'],'visibleFrom':None},*snapshot['tenants']]
        for recipient in recipients:
            if recipient['visibleFrom'] and row['last_seen_at']<datetime.fromisoformat(recipient['visibleFrom'].replace('Z','+00:00')):continue
            self.repository.add_alert(recipient['userId'],str(row['unit_id']),str(row['device_id']),'meter_offline',
                'Medidor sin conexión',str(device['name'])+' · '+str(device.get('category','Zona sin configurar'))+
                ': no recibimos lecturas desde hace más de 5 minutos. Revisa su conexión o reanuda la generación de datos.',60)
