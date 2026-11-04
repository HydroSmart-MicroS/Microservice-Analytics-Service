from datetime import datetime,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from ....domain.services.monitoring_repository import MonitoringRepository
from ....domain.services.tariff_repository import TariffRepository
from ..outboundservices.monitoring_dependencies import MonitoringDependencies
LIMA=ZoneInfo('America/Lima')
class MonitoringCommandServiceImpl:
    def __init__(self,repository:MonitoringRepository,tariffs:TariffRepository,dependencies:MonitoringDependencies):
        self.repository,self.tariffs,self.dependencies=repository,tariffs,dependencies
    def rules(self,unit,token):
        access=self.dependencies.access(unit,token)
        return self.repository.rules(unit,access['ownerUserId'])
    def save_rules(self,unit,token,user,settings):
        access=self.dependencies.access(unit,token)
        if access['ownerUserId']!=user:raise PermissionError('Solo el propietario puede cambiar las reglas.')
        return self.repository.save_rules(unit,user,settings)
    def save_goal(self,unit,token,user,budget):
        access=self.dependencies.access(unit,token)
        tariff=self.tariffs.current(unit,access['ownerUserId'])
        target=tariff.liters_for_budget(budget)
        month=datetime.now(LIMA).date().replace(day=1).isoformat()
        goal=self.repository.save_goal(user,unit,month,budget,target)
        return self.goal_progress(goal,access)
    def current_goal(self,unit,token,user):
        access=self.dependencies.access(unit,token)
        rows=self.repository.goals(user,unit,datetime.now(LIMA).date().replace(day=1).isoformat())
        return self.goal_progress(rows[0],access) if rows else None
    def goal_progress(self,goal,access):
        now=datetime.now(LIMA)
        start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
        if access.get('visibleFrom'):
            start=max(start,datetime.fromisoformat(access['visibleFrom'].replace('Z','+00:00')))
        data=self.dependencies.consumption(str(goal['unit_id']),start.isoformat(),now.isoformat())
        tariff=self.tariffs.current(str(goal['unit_id']),access['ownerUserId'])
        cost=tariff.estimate(Decimal(str(data['liters'])))['total']
        progress={'cost':cost,'liters':data['liters'],'percent':float(Decimal(cost)/goal['budget_amount']*100)}
        self.repository.publish_goal_threshold(goal,progress)
        # A new tariff can exceed an existing budget before any water is consumed.
        minimum=Decimal(tariff.estimate(Decimal(0))['total'])
        target=tariff.liters_for_budget(goal['budget_amount']) if goal['budget_amount']>minimum else Decimal(0)
        return {'id':str(goal['id']),'month':str(goal['month']),'budget':str(goal['budget_amount']),
                'targetLiters':str(target),'progress':progress,'minimumMonthlyCost':str(minimum)}
    def alerts(self,unit,token,user):
        self.dependencies.access(unit,token)
        return self.repository.alerts(user,unit)
    def resolve(self,unit,token,user,alert):
        self.dependencies.access(unit,token)
        return self.repository.resolve(user,alert)

