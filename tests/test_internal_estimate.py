import os,unittest
from unittest.mock import patch
from decimal import Decimal as D
from datetime import datetime,timezone
from uuid import UUID
from app.analytics.interfaces.rest.internal_estimates_controller import router_for
from app.analytics.application.internal.queryservices.internal_estimate_query_service_impl import InternalEstimateQueryServiceImpl
from app.analytics.domain.model.aggregates.tariff import Tariff,Tier
class InternalEstimateTests(unittest.TestCase):
 def test_unmeasured_month_has_no_invoice_but_zero_flow_readings_keep_fixed_charge(self):
  class Repo:
   def for_month(self,*args):return self.current(*args)
   def current(self,*args):return Tariff('','test','domestic',(Tier(D(0),None,D(1),D(1)),),D('6.30'),tax_rate=D('.18'))
  class Dependencies:
   count=0
   def snapshot(self,*args):return {'ownerUserId':'owner'}
   def consumption(self,*args):return {'liters':0,'readingCount':self.count,'daily':[{'date':'2026-09-15','deviceId':'device','liters':0,'readingCount':1}] if self.count else []}
  dependencies=Dependencies();router=router_for(InternalEstimateQueryServiceImpl(Repo(),dependencies));endpoint=router.routes[0].endpoint
  with patch.dict(os.environ,{'INTERNAL_SERVICE_TOKEN':'x'*32}):
   args={'unitId':UUID('00000000-0000-4000-8000-000000000001'),'start':datetime(2026,9,1,tzinfo=timezone.utc),'end':datetime(2026,10,1,tzinfo=timezone.utc),'service_token':'x'*32}
   self.assertEqual(endpoint(**args)['estimate']['total'],'0.00')
   dependencies.count=1
   self.assertEqual(endpoint(**args)['estimate']['total'],'7.43')
