import unittest
from datetime import datetime,timezone,timedelta
from decimal import Decimal as D
from types import SimpleNamespace
from unittest.mock import Mock
from app.analytics.application.internal.commandservices.device_presence_command_service import DevicePresenceCommandService
from app.analytics.application.internal.commandservices.monitoring_command_service_impl import MonitoringCommandServiceImpl
from app.analytics.domain.model.aggregates.tariff import Tariff,Tier


class AdditionalMonitoringTests(unittest.TestCase):
    def test_valid_minimum_budget_keeps_a_positive_target_when_base_rounds_up(self):
        repo,deps,tariffs=Mock(),Mock(),Mock()
        tariff=Tariff('t','Test','domestic',(Tier(D(0),None,D(1),D(0)),),D('1.15'),tax_rate=D('.10'))
        tariffs.current.return_value=tariff;deps.consumption.return_value={'liters':0}
        budget=tariff.minimum_budget()
        self.assertEqual(budget,D('1.27'))
        value=MonitoringCommandServiceImpl(repo,tariffs,deps).goal_progress(
            {'id':'g','unit_id':'u','budget_amount':budget,'month':'2026-11-01'},{'ownerUserId':'o'})
        self.assertGreater(D(value['targetLiters']),0)
        self.assertEqual(value['progress']['percent'],0)

    def test_tariff_increase_that_exceeds_budget_does_not_invent_a_liters_threshold(self):
        repo,deps,tariffs=Mock(),Mock(),Mock()
        tariffs.current.return_value=Tariff('t','Test','domestic',(Tier(D(0),None,D(1),D(0)),),D(10))
        deps.consumption.return_value={'liters':50}
        value=MonitoringCommandServiceImpl(repo,tariffs,deps).goal_progress(
            {'id':'g','unit_id':'u','budget_amount':D(9),'month':'2026-11-01'},{'ownerUserId':'o'})
        self.assertEqual(value['targetLiters'],'0');self.assertEqual(value['progress']['percent'],0)
        repo.publish_goal_threshold.assert_not_called()
    def test_fixed_charge_cannot_trigger_liters_threshold(self):
        repo,deps=Mock(),Mock()
        tariff=Tariff('t','Test','domestic',(Tier(D(0),None,D(1),D(0)),),D(10))
        tariffs=Mock();tariffs.current.return_value=tariff
        deps.consumption.return_value={'liters':70000}
        value=MonitoringCommandServiceImpl(repo,tariffs,deps).goal_progress(
            {'id':'g','unit_id':'u','budget_amount':D(100),'month':'2026-11-01'}, {'ownerUserId':'o'})
        self.assertAlmostEqual(value['progress']['percent'],70000/90000*100)
        self.assertEqual(value['progress']['budgetPercent'],80)
        deps.consumption.return_value={'liters':0}
        value=MonitoringCommandServiceImpl(repo,tariffs,deps).goal_progress(
            {'id':'g','unit_id':'u','budget_amount':D(100),'month':'2026-11-01'}, {'ownerUserId':'o'})
        self.assertEqual(value['progress']['percent'],0)

    def test_offline_ignores_unavailable_ingestion_and_disabled_meters(self):
        repo,deps=Mock(),Mock();service=DevicePresenceCommandService(repo,deps)
        deps.telemetry_ready.return_value=False
        self.assertEqual(service.pending(),[]);repo.offline_candidates.assert_not_called()
        deps.snapshot.return_value={'devices':[{'id':'d','state':'disabled'}]}
        service.check({'unit_id':'u','device_id':'d','last_seen_at':datetime.now(timezone.utc)})
        repo.claim_offline.assert_called_once();repo.add_alert.assert_not_called()

    def test_offline_notifies_once_and_respects_tenant_visibility(self):
        repo,deps=Mock(),Mock();service=DevicePresenceCommandService(repo,deps)
        seen=datetime.now(timezone.utc)-timedelta(minutes=6)
        deps.snapshot.return_value={'ownerUserId':'owner','devices':[{'id':'d','state':'active','name':'Cocina','category':'COCINA'}],
            'tenants':[{'userId':'old','visibleFrom':(seen-timedelta(days=1)).isoformat()}, {'userId':'new','visibleFrom':(seen+timedelta(seconds=1)).isoformat()}]}
        repo.claim_offline.side_effect=[True,False]
        row={'unit_id':'u','device_id':'d','last_seen_at':seen}
        service.check(row);service.check(row)
        self.assertEqual(repo.add_alert.call_count,2)
        self.assertEqual({c.args[0] for c in repo.add_alert.call_args_list},{'owner','old'})
        self.assertIn('Cocina',repo.add_alert.call_args.args[5])
