from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR

D = Decimal

@dataclass(frozen=True)
class Tier:
    start: Decimal
    end: Decimal | None
    water: Decimal
    sewer: Decimal

@dataclass(frozen=True)
class Tariff:
    id: str
    name: str
    category: str
    tiers: tuple[Tier, ...]
    fixed_charge: Decimal = D('0')
    owner_user_id: str | None = None
    tax_rate: Decimal = D('0')
    source_url: str | None = None
    source_date: str | None = None
    effective_from: date | None = None

    def validate(self):
        if self.category not in ('domestic', 'commercial') or not 1 <= len(self.name.strip()) <= 120 or len(self.name)>120 or any(ord(c)<32 or ord(c)==127 for c in self.name) or not 1 <= len(self.tiers) <= 10:
            raise ValueError('Nombre, categoría o cantidad de tramos inválidos.')
        if not self.fixed_charge.is_finite() or not D('0') <= self.fixed_charge <= D('99999.99') or self.fixed_charge.as_tuple().exponent < -2:
            raise ValueError('Cargo fijo inválido.')
        if not self.tax_rate.is_finite() or not D('0') <= self.tax_rate <= D('1') or self.tax_rate.as_tuple().exponent < -4:
            raise ValueError('El impuesto debe estar entre 0 y 1, con hasta 4 decimales.')
        expected = D('0')
        for index, tier in enumerate(self.tiers):
            values = [tier.start, tier.water, tier.sewer] + ([tier.end] if tier.end is not None else [])
            if any(not n.is_finite() or n < 0 or n > D('999999') for n in values):
                raise ValueError('Los valores deben ser números positivos finitos.')
            if tier.start != expected or (tier.end is not None and tier.end <= tier.start):
                raise ValueError('Los tramos deben ser continuos y comenzar en 0 m³.')
            if tier.water + tier.sewer <= 0:
                raise ValueError('Cada tramo debe tener un precio mayor a cero.')
            if (tier.end is None) != (index == len(self.tiers) - 1):
                raise ValueError('Solo el último tramo debe tener límite abierto.')
            if any(n.as_tuple().exponent < -6 for n in (tier.water, tier.sewer)) or tier.start.as_tuple().exponent < -3 or (tier.end is not None and tier.end.as_tuple().exponent < -3):
                raise ValueError('Usa hasta 3 decimales en m³ y 6 en precios.')
            expected = tier.end
        return self

    def estimate(self, liters: Decimal):
        self.validate()
        if not liters.is_finite() or liters < 0:
            raise ValueError('Consumo inválido.')
        cubic_meters = liters / 1000
        water = sewer = D('0')
        breakdown = []
        for tier in self.tiers:
            volume = max(D('0'), min(cubic_meters, tier.end if tier.end is not None else cubic_meters) - tier.start)
            water += volume * tier.water
            sewer += volume * tier.sewer
            breakdown.append({'fromM3': str(tier.start), 'toM3': str(tier.end) if tier.end is not None else None,
                              'volumeM3': str(volume), 'water': str(volume * tier.water), 'sewer': str(volume * tier.sewer)})
        rounded = lambda n: n.quantize(D('.01'), rounding=ROUND_HALF_UP)
        money = lambda n: str(rounded(n))
        # Round each billed component before adding it, so the displayed amounts reconcile.
        water, sewer = rounded(water), rounded(sewer)
        subtotal = water + sewer + self.fixed_charge
        tax = rounded(subtotal * self.tax_rate)
        return {'currency': 'PEN', 'water': money(water), 'sewer': money(sewer), 'fixedCharge': money(self.fixed_charge),
                'subtotal': money(subtotal), 'tax': money(tax), 'taxRate': str(self.tax_rate),
                'total': money(subtotal + tax), 'm3': str(cubic_meters), 'breakdown': breakdown}

    def minimum_budget(self):
        self.validate()
        return (self.fixed_charge * (1 + self.tax_rate)).quantize(D('.01'), rounding=ROUND_FLOOR) + D('.01')

    def liters_for_budget(self, budget: Decimal):
        self.validate()
        if not budget.is_finite() or budget <= self.fixed_charge * (1 + self.tax_rate):
            raise ValueError(f'El presupuesto mínimo para esta tarifa es S/{self.minimum_budget():.2f}; debe superar el cargo fijo y sus impuestos.')
        remaining=budget/(1+self.tax_rate)-self.fixed_charge
        for tier in self.tiers:
            rate=tier.water+tier.sewer
            if tier.end is None or remaining <= (tier.end-tier.start)*rate:
                target=((tier.start+remaining/rate)*1000).quantize(D('.000001'),rounding='ROUND_FLOOR')
                if target>=D('1000000000000'):raise ValueError('El volumen objetivo supera el rango admitido.')
                # Component rounding can make the continuous inverse exceed the actual budget.
                if D(self.estimate(target)['total'])>budget:
                    low,high=0,int(target*1000000)
                    while low<high:
                        middle=(low+high+1)//2
                        if D(self.estimate(D(middle)/1000000)['total'])<=budget:low=middle
                        else:high=middle-1
                    target=(D(low)/1000000).quantize(D('.000001'))
                return target
            remaining-=(tier.end-tier.start)*rate
        raise ValueError('Tarifa incompleta.')
