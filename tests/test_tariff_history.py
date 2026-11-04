import unittest
from dataclasses import replace
from datetime import date,datetime
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from app.analytics.domain.model.aggregates.tariff import Tariff,Tier
from app.analytics.application.internal.queryservices.historical_estimate import estimate_history
from app.analytics.application.internal.commandservices.tariff_command_service_impl import TariffCommandServiceImpl

class HistoryTests(unittest.TestCase):
 def setUp(self):
  self.old=Tariff('old','Anterior','domestic',(Tier(D(0),D(10),D(1),D(1)),Tier(D(10),None,D(2),D(2))),D(5),effective_from=date(2026,1,1))
  self.new=replace(self.old,id='new',name='Nueva',tiers=(Tier(D(0),None,D(3),D(3)),),effective_from=date(2026,11,1))

 def test_monthly_blocks_and_fees_use_the_version_of_each_month(self):
  old,new=self.old,self.new
  class Repo:
   def for_month(self,u,o,m):return old if m<'2026-11' else new
  rows=[{'date':'2026-10-20','liters':15000},{'date':'2026-11-02','liters':5000}]
  result=estimate_history(Repo(),'unit','owner',rows,new)
  self.assertEqual(result['total'],'80.00')
  self.assertEqual(result['fixedCharge'],'10.00')
  self.assertEqual([x['tariffId'] for x in result['months']],['old','new'])
  self.assertEqual(estimate_history(Repo(),'unit','owner',[],new)['total'],'0.00')
  self.assertEqual(estimate_history(Repo(),'unit','owner',[{'date':'2026-10-01','liters':0}],new)['total'],'5.00')

 def test_closed_months_cannot_be_changed_and_current_default_is_compatible(self):
  class Repo:
   def save(self,u,t):return t
  class Access:
   def access(self,*a):return {'ownerUserId':'owner'}
  service=TariffCommandServiceImpl(Repo(),Access())
  current=datetime.now(ZoneInfo('America/Lima')).date().replace(day=1)
  with self.assertRaises(ValueError):service.handle('u','t','owner',replace(self.old,effective_from=date(2000,1,1)))
  with self.assertRaises(ValueError):service.handle('u','t','owner',replace(self.old,effective_from=current.replace(day=2)))
  self.assertEqual(service.handle('u','t','owner',replace(self.old,effective_from=None)).effective_from,current)
  with self.assertRaises(PermissionError):service.handle('u','t','tenant',self.old)
