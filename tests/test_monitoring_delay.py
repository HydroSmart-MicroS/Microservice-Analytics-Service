import unittest
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import patch
from app.analytics.application.internal.eventhandlers.monitoring_event_handler import MonitoringEventHandler

MODULE='app.analytics.application.internal.eventhandlers.monitoring_event_handler'
NOW=datetime(2026,10,27,5,tzinfo=timezone.utc)
class Clock(datetime):
    @classmethod
    def now(cls,tz=None):return NOW
class Repository:
    def __init__(self,at):
        self.rows=[{'measured_at':at-timedelta(seconds=10*i),'liters':1,'interval_seconds':10} for i in range(18)]
        self.alerts=[]
    def monitoring_processed(self,*args):return False
    def store_sample(self,*args):pass
    def rules(self,*args):return {'highEnabled':False,'windowSeconds':3600,'leakEnabled':True,'leakWindowSeconds':180,'normalStartHour':6,'normalEndHour':22,'leakAllDay':True,'cooldownSeconds':1800}
    def samples(self,unit,start,end,device=None):return sorted((row for row in self.rows if start<=row['measured_at']<=end),key=lambda row:row['measured_at'])
    def add_alert(self,*args):self.alerts.append(args)
    def goals_for_unit(self,*args):return []
    def mark_monitoring(self,*args):pass
class Dependencies:
    def snapshot(self,*args):return {'ownerUserId':'owner','tenants':[]}
class MonitoringDelayTests(unittest.TestCase):
    def test_queue_delay_does_not_shrink_a_complete_leak_window(self):
        at=NOW-timedelta(seconds=45)
        repository=Repository(at)
        with patch(MODULE+'.datetime',Clock):
            MonitoringEventHandler(repository,Dependencies(),None).handle(SimpleNamespace(event_id='event',unit_id='unit',device_id='meter',measured_at=at))
        self.assertEqual(len(repository.alerts),1)
        self.assertEqual(repository.alerts[0][3],'possible_leak')
    def test_old_history_still_does_not_generate_live_alerts(self):
        at=NOW-timedelta(minutes=6)
        repository=Repository(at)
        with patch(MODULE+'.datetime',Clock):
            MonitoringEventHandler(repository,Dependencies(),None).handle(SimpleNamespace(event_id='event',unit_id='unit',device_id='meter',measured_at=at))
        self.assertEqual(repository.alerts,[])
