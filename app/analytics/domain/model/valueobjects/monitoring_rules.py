from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

def outside_hours(instant: datetime, start_hour: int, end_hour: int) -> bool:
    hour=instant.astimezone(ZoneInfo('America/Lima')).hour
    inside=start_hour <= hour < end_hour if start_hour < end_hour else hour >= start_hour or hour < end_hour
    return not inside

def possible_leak(samples, seconds, start_hour, end_hour, all_day=False):
    if len(samples)<2:return False
    rows=sorted(samples,key=lambda row:row['measured_at'])
    active=[]
    for row in rows:
        if row['liters']<=0 or (not all_day and not outside_hours(row['measured_at'],start_hour,end_hour)):
            active=[];continue
        if active and (row['measured_at']-active[-1]['measured_at']).total_seconds()>max(row['interval_seconds']*1.5,15):
            active=[]
        active.append(row)
    if len(active)<2:return False
    duration=(active[-1]['measured_at']-active[0]['measured_at']).total_seconds()+active[0]['interval_seconds']
    return duration>=seconds
