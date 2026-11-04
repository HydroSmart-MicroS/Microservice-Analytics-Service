from decimal import Decimal

def estimate_history(repository,unit,owner,daily,fallback):
    volumes={}
    for row in daily:
        month=row['date'][:7]
        volumes[month]=volumes.get(month,Decimal(0))+Decimal(str(row['liters']))
    months=[]
    for month,volume in sorted(volumes.items()):
        tariff=repository.for_month(unit,owner,month)
        months.append({'month':month,'tariffId':tariff.id,'tariffName':tariff.name,
                       'legacySnapshot':bool(tariff.effective_from and tariff.effective_from.year==1900),**tariff.estimate(volume)})
    result=fallback.estimate(Decimal(0))
    for field in ('water','sewer','fixedCharge','subtotal','tax','total','m3'):
        total=sum((Decimal(item[field]) for item in months),Decimal(0))
        result[field]=str(total if field=='m3' else total.quantize(Decimal('.01')))
    result['breakdown']=[{'month':item['month'],'tariffName':item['tariffName'],**tier} for item in months for tier in item['breakdown']]
    result['months']=months
    rates={item['taxRate'] for item in months}
    result['taxRate']=next(iter(rates)) if len(rates)==1 else None
    return result
