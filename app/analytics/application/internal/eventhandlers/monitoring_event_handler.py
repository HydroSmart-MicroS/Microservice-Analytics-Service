from datetime import datetime,timedelta,timezone
from decimal import Decimal
from ....domain.model.valueobjects.monitoring_rules import possible_leak

class MonitoringEventHandler:
    def __init__(self,repository,dependencies,goals):
        self.repository,self.dependencies,self.goals=repository,dependencies,goals
    def handle(self,reading):
        if self.repository.monitoring_processed(reading.event_id):return False
        now=datetime.now(timezone.utc)
        if reading.measured_at>now+timedelta(minutes=5):raise ValueError('Future sample')
        if reading.measured_at<now-timedelta(minutes=5):
            self.repository.mark_monitoring(reading.event_id);return True
        # Evaluate the measured window even when network/queue processing is delayed.
        observed=min(now,reading.measured_at)
        snapshot=self.dependencies.snapshot(str(reading.unit_id))
        if snapshot is None:
            self.repository.mark_monitoring(reading.event_id);return True
        self.repository.store_sample(reading)
        device=next((d for d in snapshot.get('devices',[]) if str(d['id'])==str(reading.device_id)),{})
        location=str(device.get('name','Medidor'))+' · '+str(device.get('category','Zona sin configurar'))
        settings=self.repository.rules(str(reading.unit_id),snapshot['ownerUserId'])
        recipients=[{'userId':snapshot['ownerUserId'],'visibleFrom':None},*snapshot['tenants']]
        cutoff=observed-timedelta(seconds=int(settings['windowSeconds']))
        for recipient in recipients:
            visible=datetime.fromisoformat(recipient['visibleFrom'].replace('Z','+00:00')) if recipient['visibleFrom'] else datetime.min.replace(tzinfo=timezone.utc)
            if observed<visible:continue
            samples=self.repository.samples(str(reading.unit_id),max(cutoff,visible),observed)
            volume=sum((row['liters'] for row in samples),Decimal(0))
            if settings['highEnabled'] and volume>=Decimal(str(settings['thresholdLiters'])):
                self.repository.add_alert(recipient['userId'],str(reading.unit_id),str(reading.device_id),'high_consumption',
                    'Consumo inusual detectado','Se registraron '+str(volume.quantize(Decimal('.01')))+' litros en la ventana de seguimiento.',settings['cooldownSeconds'])
            if settings['leakEnabled']:
                rows=self.repository.samples(str(reading.unit_id),max(observed-timedelta(seconds=int(settings['leakWindowSeconds'])+15),visible),observed,str(reading.device_id))
                # Zero samples and missing intervals break continuity; normal bursts do not become leaks.
                if rows and rows[-1]['measured_at']>=observed-timedelta(seconds=30) and possible_leak(rows,int(settings['leakWindowSeconds']),int(settings['normalStartHour']),int(settings['normalEndHour']),settings['leakAllDay']):
                    self.repository.add_alert(recipient['userId'],str(reading.unit_id),str(reading.device_id),'possible_leak',
                        'Posible fuga de agua','Se detectó flujo continuo en '+location+'. Revisa este punto y confirma o descarta la fuga.',settings['cooldownSeconds'])
        for goal in self.repository.goals_for_unit(str(reading.unit_id)):
            recipient=next((r for r in recipients if r['userId']==goal['user_id']),None)
            if recipient:self.goals.goal_progress(goal,{'ownerUserId':snapshot['ownerUserId'],'visibleFrom':recipient['visibleFrom']})
        self.repository.mark_monitoring(reading.event_id)
        return True

