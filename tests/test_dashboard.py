import unittest
from datetime import datetime, timedelta
from decimal import Decimal as D
from unittest.mock import patch
from zoneinfo import ZoneInfo
from app.analytics.domain.model.aggregates.tariff import Tariff, Tier
from app.analytics.application.internal.queryservices.dashboard_query_service_impl import DashboardQueryServiceImpl

MODULE='app.analytics.application.internal.queryservices.dashboard_query_service_impl'
LIMA=ZoneInfo('America/Lima')
NOW=datetime(2026,10,24,13,0,tzinfo=LIMA)
class Clock(datetime):
    @classmethod
    def now(cls,tz=None): return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)
class Repo:
    def for_month(self,*args):return self.current(*args)
    def current(self,*args): return Tariff('','Reference','domestic',(Tier(D(0),None,D(1),D(1)),))
class Gateway:
    def __init__(self,daily): self.daily=daily
    def access(self,*args): return {'ownerUserId':'owner'}
    def consumption(self,*args): return {'daily':self.daily,'liters':sum(row['liters'] for row in self.daily),'lastReadingAt':None}

class DashboardTests(unittest.TestCase):
    def test_tenant_partial_first_day_is_not_a_complete_comparison_day(self):
        monday=NOW.date()-timedelta(days=NOW.weekday())
        start=monday-timedelta(days=7)
        data=[{'date':(start+timedelta(days=i)).isoformat(),'deviceId':'one','liters':100} for i in range(20)]
        class TenantGateway(Gateway):
            def access(self,*args):return {'ownerUserId':'owner','visibleFrom':start.isoformat()+'T12:00:00-05:00'}
        with patch(MODULE+'.datetime',Clock):
            result=DashboardQueryServiceImpl(Repo(),TenantGateway(data)).handle('unit','token',NOW-timedelta(days=31),NOW)
        self.assertFalse(result['comparisons']['weekly']['available'])

    def query(self,days,today=0):
        rows=[{'date':(NOW-timedelta(days=d)).date().isoformat(),'deviceId':'one','liters':100} for d in range(1,days+1)]
        if today: rows.append({'date':NOW.date().isoformat(),'deviceId':'one','liters':today})
        with patch(MODULE+'.datetime',Clock):
            return DashboardQueryServiceImpl(Repo(),Gateway(rows)).handle('unit','token',NOW-timedelta(days=31),NOW)

    def test_projection_requires_seven_complete_dates(self):
        self.assertIsNone(self.query(6,today=10000)['projection'])
        self.assertEqual(self.query(7)['projection'],{'liters':3100.0,'cost':'6.20'})

    def test_partial_today_does_not_distort_comparison_or_projection(self):
        result=self.query(14,today=1000000)
        self.assertEqual(result['comparison']['changePercent'],0)
        self.assertEqual(result['projection']['liters'],3100.0)

    def test_comparison_requires_two_weeks(self):
        self.assertIsNone(self.query(7)['comparison'])

    def test_stale_readings_keep_history_but_mark_unavailable(self):
        for minutes,expected in [(4,True),(5,True),(6,False)]:
            class LatestGateway(Gateway):
                def consumption(self,*args):
                    result=super().consumption(*args)
                    result['lastReadingAt']=(NOW-timedelta(minutes=minutes)).isoformat()
                    return result
            rows=[{'date':'2026-10-23','liters':100,'deviceId':'one'}]
            with patch(MODULE+'.datetime',Clock):
                result=DashboardQueryServiceImpl(Repo(),LatestGateway(rows)).handle('unit','token',NOW-timedelta(days=31),NOW)
            self.assertEqual(result['available'],expected)
            self.assertEqual(result['liters'],100)

    def test_history_filter_does_not_reduce_this_month_or_today(self):
        rows=[{'date':'2026-10-01','liters':5000,'deviceId':'one'},
              {'date':'2026-10-24','liters':200,'deviceId':'one'}]
        class FilteringGateway(Gateway):
            def consumption(self,unit,token,start,end):
                first,last=datetime.fromisoformat(start).date().isoformat(),datetime.fromisoformat(end).date().isoformat()
                daily=[row for row in self.daily if first<=row['date']<=last]
                return {'daily':daily,'liters':sum(row['liters'] for row in daily),'lastReadingAt':None}
        with patch(MODULE+'.datetime',Clock):
            result=DashboardQueryServiceImpl(Repo(),FilteringGateway(rows)).handle('unit','token',NOW.replace(day=20),NOW)
        self.assertEqual(result['liters'],200)
        self.assertEqual(result['monthLiters'],5200)
        self.assertEqual(result['todayLiters'],200)
        self.assertEqual(result['monthEstimate']['total'],'10.40')

    def test_unrelated_old_history_cannot_change_month_projection(self):
        rows=[{'date':'2026-09-01','liters':1000000,'deviceId':'one'}]
        rows += [{'date':f'2026-10-{day:02d}','liters':100,'deviceId':'one'} for day in range(1,24)]
        class FilteringGateway(Gateway):
            def consumption(self,unit,token,start,end):
                first,last=datetime.fromisoformat(start).date().isoformat(),datetime.fromisoformat(end).date().isoformat()
                daily=[row for row in self.daily if first<=row['date']<=last]
                return {'daily':daily,'liters':sum(row['liters'] for row in daily),'lastReadingAt':None}
        with patch(MODULE+'.datetime',Clock):
            result=DashboardQueryServiceImpl(Repo(),FilteringGateway(rows)).handle('unit','token',NOW.replace(month=9,day=1),NOW)
        self.assertEqual(result['projection']['liters'],3100)

    def test_history_estimate_applies_progressive_blocks_and_fixed_charge_per_month(self):
        class MonthlyRepo:
            def for_month(self,*args):return self.current(*args)
            def current(self,*args):
                return Tariff('','reference','domestic',(Tier(D(0),D(10),D(1),D(1)),Tier(D(10),None,D(2),D(2))),D(5),tax_rate=D('.18'))
        rows=[{'date':'2026-09-30','liters':10000,'deviceId':'one'},
              {'date':'2026-10-01','liters':10000,'deviceId':'one'}]
        with patch(MODULE+'.datetime',Clock):
            result=DashboardQueryServiceImpl(MonthlyRepo(),Gateway(rows)).handle('unit','token',NOW.replace(month=9,day=1),NOW)
        self.assertEqual(D(result['estimate']['total']),D('59.00'))
        self.assertEqual(D(result['estimate']['fixedCharge']),D('10.00'))
        self.assertEqual([month['month'] for month in result['estimate']['months']],['2026-09','2026-10'])

    def test_empty_history_has_no_monthly_charge_but_current_month_still_shows_fixed(self):
        class MonthlyRepo:
            def for_month(self,*args):return self.current(*args)
            def current(self,*args):
                return Tariff('','reference','domestic',(Tier(D(0),None,D('2.20'),D('1.38')),),D('6.30'),tax_rate=D('.18'))
        with patch(MODULE+'.datetime',Clock):
            result=DashboardQueryServiceImpl(MonthlyRepo(),Gateway([])).handle('unit','token',NOW.replace(day=1),NOW)
        self.assertEqual(result['estimate']['months'],[])
        self.assertEqual(result['estimate']['total'],'0.00')
        self.assertEqual(result['estimate']['fixedCharge'],'0.00')
        self.assertEqual(result['monthEstimate']['total'],'7.43')


    def test_one_supplementary_range_covers_month_week_and_insights(self):
        class CountingGateway(Gateway):
            def __init__(self):super().__init__([]);self.calls=[]
            def consumption(self,*args):self.calls.append(args);return super().consumption(*args)
        gateway=CountingGateway()
        with patch(MODULE+'.datetime',Clock):
            DashboardQueryServiceImpl(Repo(),gateway).handle('unit','token',NOW-timedelta(days=6),NOW)
        self.assertEqual(len(gateway.calls),2)
        self.assertLessEqual(datetime.fromisoformat(gateway.calls[1][2]),NOW.replace(month=9,day=1,hour=0,minute=0))
