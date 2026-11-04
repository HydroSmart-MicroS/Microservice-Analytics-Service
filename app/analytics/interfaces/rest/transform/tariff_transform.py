from ....domain.model.aggregates.tariff import Tariff, Tier

def to_domain(resource):
    return Tariff('',resource.name.strip(),resource.category,
        tuple(Tier(t.fromM3,t.toM3,t.waterPrice,t.sewerPrice) for t in resource.tiers),resource.fixedCharge,tax_rate=resource.taxRate,effective_from=resource.effectiveFrom).validate()

def to_resource(tariff):
    return {'id':tariff.id,'name':tariff.name,'category':tariff.category,'currency':'PEN',
            'fixedCharge':str(tariff.fixed_charge),'isReference':tariff.owner_user_id is None,
            'taxRate':str(tariff.tax_rate),'sourceUrl':tariff.source_url,'sourceDate':tariff.source_date,'effectiveFrom':tariff.effective_from.isoformat() if tariff.effective_from else None,
            'tiers':[{'fromM3':str(t.start),'toM3':str(t.end) if t.end is not None else None,
                      'waterPrice':str(t.water),'sewerPrice':str(t.sewer)} for t in tariff.tiers]}
