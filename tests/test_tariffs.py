import unittest
from dataclasses import replace
from decimal import Decimal as D
from app.analytics.domain.model.aggregates.tariff import Tariff, Tier
from app.analytics.application.internal.commandservices.tariff_command_service_impl import TariffCommandServiceImpl

class TariffTests(unittest.TestCase):
    def setUp(self):
        self.tariff = Tariff('test','Doméstico','domestic',(Tier(D(0),D(10),D('1.50'),D('.80')),Tier(D(10),D(20),D('2.30'),D('1.10')),Tier(D(20),None,D('4.50'),D('2.10'))))

    def test_progressive_boundaries_and_rounding(self):
        for liters, expected in [('0','0.00'),('10000','23.00'),('20000','57.00'),('25000','90.00'),('25001','90.00'),('25002','90.01')]:
            self.assertEqual(self.tariff.estimate(D(liters))['total'],expected)

    def test_invalid_ranges_and_nonfinite_values(self):
        for tiers in [(Tier(D(1),None,D(1),D(1)),), (Tier(D(0),D(10),D(1),D(1)),), (Tier(D(0),None,D('NaN'),D(1)),), (Tier(D(0),None,D(0),D(0)),)]:
            with self.assertRaises(ValueError):
                Tariff('','a','domestic',tiers).validate()

    def test_tariff_name_rejects_controls_and_oversized_untrimmed_values(self):
        for name in ('a'*121, 'Casa\x00falsa', 'Casa\nsegunda', ' '*10):
            with self.assertRaises(ValueError):replace(self.tariff,name=name).validate()

    def test_tenant_cannot_change_tariff(self):
        class Gateway:
            def access(self,*args): return {'ownerUserId':'owner'}
        with self.assertRaises(PermissionError):
            TariffCommandServiceImpl(None,Gateway()).handle('unit','token','tenant',self.tariff)

    def sedapal(self):
        return Tariff('sedapal','Sedapal doméstico Grupo 1','domestic',(
            Tier(D(0),D(10),D('2.20'),D('1.38')),
            Tier(D(10),D(20),D('2.36'),D('1.48')),
            Tier(D(20),D(50),D('3.22'),D('1.98')),
            Tier(D(50),None,D('7.32'),D('3.49'))),D('6.30'),tax_rate=D('.18'))

    def test_sedapal_five_cubic_meters_includes_fixed_charge_and_igv(self):
        result=self.sedapal().estimate(D(5000))
        self.assertEqual({k:result[k] for k in ('m3','water','sewer','fixedCharge','subtotal','tax','total')},
                         {'m3':'5','water':'11.00','sewer':'6.90','fixedCharge':'6.30','subtotal':'24.20','tax':'4.36','total':'28.56'})

    def test_sedapal_progressive_blocks_and_zero_still_has_fixed_charge(self):
        for liters,expected in [('0','7.43'),('10000','49.68'),('20000','94.99'),('25000','125.67'),('50000','279.07'),('51000','291.83')]:
            with self.subTest(liters=liters):
                self.assertEqual(self.sedapal().estimate(D(liters))['total'],expected)

    def test_billed_components_add_up_after_rounding(self):
        tariff=Tariff('','test','domestic',(Tier(D(0),None,D('.005'),D('.005')),),tax_rate=D('.18'))
        result=tariff.estimate(D(1000))
        self.assertEqual(result['total'],'0.02')
        self.assertEqual(sum(D(result[k]) for k in ('water','sewer','fixedCharge','tax')),D(result['total']))

    def test_invalid_tax_and_fixed_charge_precision_are_rejected(self):
        for rate in ('NaN','-.1','1.1','.12345'):
            with self.assertRaises(ValueError):replace(self.tariff,tax_rate=D(rate)).validate()
        with self.assertRaises(ValueError):replace(self.tariff,fixed_charge=D('1.001')).validate()

    def test_budget_accounts_for_tax_and_fixed_charge(self):
        tariff=self.sedapal()
        with self.assertRaisesRegex(ValueError,'cargo fijo'):
            tariff.liters_for_budget(D('7.43'))
        target=tariff.liters_for_budget(D('28.56'))
        self.assertGreaterEqual(target,D(5000))
        self.assertLess(target,D(5010))
        self.assertLessEqual(D(tariff.estimate(target)['total']),D('28.56'))

    def test_minimum_budget_is_the_first_cent_above_the_exact_base_cost(self):
        for fixed,tax,expected in [('6.30','.18','7.44'),('0','0','.01'),('1.15','.10','1.27'),('100','.18','118.01')]:
            tariff=replace(self.tariff,fixed_charge=D(fixed),tax_rate=D(tax))
            minimum=tariff.minimum_budget()
            self.assertEqual(minimum,D(expected))
            self.assertGreater(tariff.liters_for_budget(minimum),0)
            with self.assertRaisesRegex(ValueError,f'S/{minimum:.2f}'):
                tariff.liters_for_budget(minimum-D('.01'))

    def test_budget_target_respects_individually_rounded_billed_components(self):
        tariff=Tariff('t','Redondeo','domestic',(Tier(D(0),None,D('.005'),D('.005')),))
        target=tariff.liters_for_budget(D('.01'))
        self.assertGreater(target,0)
        self.assertLessEqual(D(tariff.estimate(target)['total']),D('.01'))
        self.assertGreater(D(tariff.estimate(target+D('.000001'))['total']),D('.01'))

    def test_owner_edit_preserves_tax_rate(self):
        class Gateway:
            def access(self,*args):return {'ownerUserId':'owner'}
        class Repository:
            def save(self,unit,tariff):return tariff
        result=TariffCommandServiceImpl(Repository(),Gateway()).handle('unit','token','owner',self.sedapal())
        self.assertEqual(result.tax_rate,D('.18'))
        self.assertEqual(result.owner_user_id,'owner')
