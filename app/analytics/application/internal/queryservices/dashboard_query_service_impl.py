from calendar import monthrange
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from .historical_estimate import estimate_history
from ....domain.services.monitoring_gateway import MonitoringGateway
from ....domain.services.tariff_repository import TariffRepository
from ....domain.model.valueobjects.consumption_insights import comparison_ranges, compare_periods, recommendations

LIMA = ZoneInfo('America/Lima')

class DashboardQueryServiceImpl:
    def __init__(self, repository: TariffRepository, gateway: MonitoringGateway):
        self.repository, self.gateway = repository, gateway

    def handle(self, unit_id, token, start, end):
        access = self.gateway.access(unit_id, token)
        tariff = self.repository.current(unit_id, access['ownerUserId'])
        data = self.gateway.consumption(unit_id, token, start.isoformat(), end.isoformat())
        data['estimate']=estimate_history(self.repository,unit_id,access['ownerUserId'],data.get('daily',[]),tariff)
        versions=data['estimate']['months']
        data['tariffName']=versions[0]['tariffName'] if len({v['tariffId'] for v in versions})==1 else 'Tarifas del período' if versions else tariff.name
        now = datetime.now(LIMA)
        latest = data.get('lastReadingAt')
        data['available'] = bool(latest and -300 <= (now - datetime.fromisoformat(latest.replace('Z', '+00:00'))).total_seconds() <= 300)
        daily = data.get('daily', [])
        month_start = now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
        week = now.date() - timedelta(days=now.weekday())
        previous = week - timedelta(days=7)
        previous_start = datetime.combine(previous,datetime.min.time(),tzinfo=LIMA)
        ranges = comparison_ranges(now.date())
        insights_start = datetime.combine(min(period[2] for period in ranges.values()), datetime.min.time(), tzinfo=LIMA)
        needed = min(month_start,previous_start,insights_start)
        # Fetch one authorized supplementary range for the current month, comparisons and advice.
        recent = data if start <= needed and end >= now else self.gateway.consumption(unit_id,token,needed.isoformat(),now.isoformat())
        monthly = data if start <= month_start and end >= now else recent
        month_daily = [row for row in monthly.get('daily', []) if row['date'].startswith(now.strftime('%Y-%m'))]
        month_liters = sum((Decimal(str(row['liters'])) for row in month_daily), Decimal(0))
        data['monthLiters'] = float(month_liters)
        data['monthEstimate'] = tariff.estimate(month_liters)
        data['todayLiters'] = float(sum((Decimal(str(row['liters'])) for row in month_daily if row['date'] == now.date().isoformat()), Decimal(0)))
        dates = {row['date'] for row in month_daily}
        first = min(dates) if dates else None
        days = (now.date() - datetime.fromisoformat(first).date()).days + 1 if first else 0
        # Only completed days are used, so a partially observed current day cannot depress the projection.
        complete = [row for row in month_daily if row['date'] < now.date().isoformat()]
        complete_dates = {row['date'] for row in complete}
        data['projection'] = None
        if len(complete_dates) >= 7 and days > 7:
            span = (now.date() - datetime.fromisoformat(min(complete_dates)).date()).days
            average = sum((Decimal(str(row['liters'])) for row in complete), Decimal(0)) / span
            projected = average * monthrange(now.year, now.month)[1]
            data['projection'] = {'liters': float(projected), 'cost': tariff.estimate(projected)['total']}
        cutoff = previous + timedelta(days=now.weekday())
        history_covers_week = start <= previous_start and end >= now
        week_daily = data.get('daily', []) if history_covers_week else [row for row in recent.get('daily',[]) if row['date'] >= previous.isoformat()]
        week_dates = {row['date'] for row in week_daily}
        current_liters = sum(Decimal(str(row['liters'])) for row in week_daily if week.isoformat() <= row['date'] < now.date().isoformat())
        previous_liters = sum(Decimal(str(row['liters'])) for row in week_daily if previous.isoformat() <= row['date'] < cutoff.isoformat())
        data['comparison'] = None
        if week_dates and min(week_dates) <= previous.isoformat() and len(week_dates) >= 14 and previous_liters > 0 and now.weekday() > 0:
            data['comparison'] = {'currentLiters': float(current_liters), 'previousLiters': float(previous_liters),
                                  'changePercent': float((current_liters - previous_liters) / previous_liters * 100)}
        insights = data if start <= insights_start and end >= now else recent
        insight_rows = insights.get('daily', [])
        if access.get('visibleFrom'):
            visible = datetime.fromisoformat(access['visibleFrom'].replace('Z', '+00:00')).astimezone(LIMA)
            first_full = visible.date() + timedelta(days=visible.hour != 0 or visible.minute != 0 or visible.second != 0 or visible.microsecond != 0)
            insight_rows = [row for row in insight_rows if row['date'] >= first_full.isoformat()]
        data['comparisons'] = compare_periods(insight_rows, ranges)
        data['recommendations'] = recommendations(insight_rows, data['comparisons'], now.date())
        return data
