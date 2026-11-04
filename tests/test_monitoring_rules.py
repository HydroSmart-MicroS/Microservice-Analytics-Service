import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
from app.analytics.domain.model.valueobjects.monitoring_rules import possible_leak,outside_hours
from app.analytics.domain.model.aggregates.tariff import Tariff,Tier
from app.analytics.interfaces.rest.alerts_controller import RulesResource
class MonitoringRulesTests(unittest.TestCase):
    def test_distinct_hours_are_required_only_for_outside_hours_leak_detection(self):
        with self.assertRaises(ValueError):RulesResource(normalStartHour=6,normalEndHour=6)
        self.assertTrue(RulesResource(normalStartHour=6,normalEndHour=6,leakAllDay=True).leakAllDay)
        self.assertFalse(RulesResource(normalStartHour=6,normalEndHour=6,leakEnabled=False).leakEnabled)
    def samples(self,count=18,hour=8):
        start=datetime(2026,10,24,hour,0,tzinfo=timezone.utc)
        return [{'liters':D(1),'interval_seconds':10,'measured_at':start+timedelta(seconds=i*10)} for i in range(count)]
    def test_continuous_night_flow_reaches_window(self):
        self.assertTrue(possible_leak(self.samples(),180,6,22))
        self.assertFalse(possible_leak(self.samples(17),180,6,22))
    def test_normal_day_and_zero_samples_do_not_trigger(self):
        self.assertFalse(possible_leak(self.samples(hour=18),180,6,22))
        rows=self.samples();rows[-1]['liters']=D(0)
        self.assertFalse(possible_leak(rows,180,6,22,True))
    def test_last_continuous_suffix_and_gaps(self):
        rows=self.samples();zero={**rows[0],'liters':D(0),'measured_at':rows[0]['measured_at']-timedelta(seconds=10)}
        self.assertTrue(possible_leak([zero,*rows],180,6,22))
        rows[9]['measured_at']+=timedelta(seconds=5)
        self.assertTrue(possible_leak(rows,180,6,22))
        rows[9]['measured_at']+=timedelta(seconds=20)
        self.assertFalse(possible_leak(rows,180,6,22))
    def test_budget_inverts_progressive_rates(self):
        tariff=Tariff('','domestic','domestic',(Tier(D(0),D(10),D('1.5'),D('.8')),Tier(D(10),D(20),D('2.3'),D('1.1')),Tier(D(20),None,D('4.5'),D('2.1'))))
        for budget,liters in [('23','10000'),('57','20000'),('90','25000')]:
            self.assertEqual(tariff.liters_for_budget(D(budget)),D(liters))
        with self.assertRaises(ValueError):tariff.liters_for_budget(D(0))

