import unittest
from datetime import date
from decimal import Decimal as D
from uuid import UUID
from app.analytics.domain.model.aggregates.tariff import Tariff,Tier
from app.analytics.interfaces.rest.monitoring_controller import router_for
from app.analytics.interfaces.rest.resources.tariff_resource import TariffResource
from app.analytics.interfaces.rest.transform.tariff_transform import to_domain,to_resource
from app.analytics.application.internal.commandservices.monitoring_command_service_impl import MonitoringCommandServiceImpl
from app.analytics.application.internal.queryservices.tariff_query_service_impl import TariffQueryServiceImpl

class TariffApiTests(unittest.TestCase):
    def tariff(self):
        return Tariff('','Sedapal','domestic',(Tier(D(0),None,D('2.20'),D('1.38')),),D('6.30'),tax_rate=D('.18'))

    def test_preview_uses_authorized_unit_and_server_tariff(self):
        tariff=self.tariff()
        calls=[]
        class Repository:
            def current(self,*args):calls.append(('tariff',args));return tariff
        class Gateway:
            def access(self,*args):calls.append(('access',args));return {'ownerUserId':'owner'}
        router=router_for(TariffQueryServiceImpl(Repository(),Gateway()),None,None)
        endpoint=next(route.endpoint for route in router.routes if route.path=='/api/v1/tariffs/estimate')
        unit=UUID('10000000-0000-4000-8000-000000000001')
        result=endpoint(unitId=unit,liters=D(5000),category='domestic',reference=False,actor=('token',{}))
        self.assertEqual(calls,[('access',(str(unit),'token')),('tariff',(str(unit),'owner','domestic',False))])
        self.assertEqual(result['estimate']['total'],'28.56')
        self.assertEqual(result['minimumBudget'],'7.44')

        empty=endpoint(unitId=unit,liters=D('0.000'),category='domestic',reference=False,actor=('token',{}))
        charges=('water','sewer','fixedCharge','subtotal','tax','total')
        self.assertEqual({key:empty['estimate'][key] for key in charges},dict.fromkeys(charges,'0.00'))
        self.assertEqual(empty['estimate']['taxRate'],'0.18')
        self.assertEqual(empty['minimumBudget'],'7.44')

    def test_resource_preserves_tax_and_legacy_requests_default_to_zero(self):
        payload={'name':'custom','category':'domestic','fixedCharge':'6.30','tiers':[{'fromM3':'0','toM3':None,'waterPrice':'2.20','sewerPrice':'1.38'}]}
        self.assertEqual(to_domain(TariffResource(**payload)).tax_rate,D(0))
        payload['taxRate']='.18'
        self.assertEqual(to_resource(to_domain(TariffResource(**payload)))['taxRate'],'0.18')

    def test_saved_goal_below_new_tariff_minimum_remains_readable(self):
        tariff=self.tariff()
        class Tariffs:
            def current(self,*args):return tariff
        class Repository:
            def publish_goal_threshold(self,*args):pass
        class Dependencies:
            def consumption(self,*args):return {'liters':0}
        service=MonitoringCommandServiceImpl(Repository(),Tariffs(),Dependencies())
        result=service.goal_progress({'id':'goal','unit_id':'unit','month':date(2026,10,1),'budget_amount':D(1)}, {'ownerUserId':'owner'})
        self.assertEqual(result['targetLiters'],'0')
        self.assertEqual(result['minimumMonthlyCost'],'7.43')
        self.assertEqual(result['progress']['cost'],'7.43')
