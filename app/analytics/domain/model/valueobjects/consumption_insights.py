from datetime import timedelta
from decimal import Decimal


def comparison_ranges(today):
    monday = today - timedelta(days=today.weekday())
    month = today.replace(day=1)
    previous_month = (month - timedelta(days=1)).replace(day=1)
    days = min(today.day - 1, (month - previous_month).days)
    return {
        'weekly': (monday, today, monday - timedelta(days=7), today - timedelta(days=7)),
        'monthly': (month, month + timedelta(days=days), previous_month, previous_month + timedelta(days=days)),
    }


def compare_periods(rows, ranges):
    by_day = {}
    for row in rows:
        by_day[row['date']] = by_day.get(row['date'], Decimal(0)) + Decimal(str(row['liters']))
    result = {}
    for kind, (start, end, previous, previous_end) in ranges.items():
        days = (end - start).days
        dates = [(start + timedelta(days=i)).isoformat() for i in range(days)]
        old_dates = [(previous + timedelta(days=i)).isoformat() for i in range(days)]
        complete = days > 0 and all(day in by_day for day in dates + old_dates)
        current = sum((by_day.get(day, Decimal(0)) for day in dates), Decimal(0))
        old = sum((by_day.get(day, Decimal(0)) for day in old_dates), Decimal(0))
        result[kind] = {
            'available': complete, 'days': days,
            'currentStart': start.isoformat(), 'currentEnd': (end - timedelta(days=1)).isoformat() if days else None,
            'previousStart': previous.isoformat(), 'previousEnd': (previous_end - timedelta(days=1)).isoformat() if days else None,
            'currentLiters': float(current) if complete else None, 'previousLiters': float(old) if complete else None,
            'changePercent': float((current - old) / old * 100) if complete and old > 0 else None,
            'reason': '' if complete else 'Aún no hay lecturas de todos los días de ambos períodos.' if days else
                'La comparación semanal estará disponible desde el martes, con el primer día completo.' if kind=='weekly' else 'La comparación mensual estará disponible desde el segundo día del mes.',
        }
    return result


def recommendations(rows, comparisons, today):
    start = (today - timedelta(days=7)).isoformat()
    recent = [row for row in rows if start <= row['date'] < today.isoformat()]
    if len({row['date'] for row in recent}) < 7:
        return []
    total = sum((Decimal(str(row['liters'])) for row in recent), Decimal(0))
    if total <= 0:
        return []
    advice = []
    weekly = comparisons['weekly']
    if weekly['available'] and weekly['changePercent'] is not None:
        change = weekly['changePercent']
        if change > 0:
            advice.append({'code': 'weekly_increase', 'title': 'Revisa el aumento de tu consumo', 'body': f'Esta semana consumiste {change:.1f}% más que en los mismos días completos de la anterior. Revisa las actividades de mayor uso y prueba reducir su duración.', 'path': '/historial'})
        elif change < 0:
            advice.append({'code': 'weekly_decrease', 'title': 'Conserva los hábitos que te ayudaron', 'body': f'Esta semana consumiste {abs(change):.1f}% menos que en los mismos días completos de la anterior. Identifica qué cambió para mantener la mejora.', 'path': '/historial'})
    devices, days = {}, {}
    for row in recent:
        value = Decimal(str(row['liters']))
        devices[row['deviceId']] = devices.get(row['deviceId'], Decimal(0)) + value
        days[row['date']] = days.get(row['date'], Decimal(0)) + value
    peak = max(days, key=days.get)
    if days[peak] > total / 7 * Decimal('1.25'):
        advice.append({'code': 'peak_day', 'title': 'Revisa tu día de mayor consumo', 'body': f'El {peak} registraste {days[peak]:.1f} L, por encima de tu promedio de {total / 7:.1f} L/día. Revisa qué actividades explican ese uso.', 'path': '/historial'})
    device = max(devices, key=devices.get)
    if devices[device] / total >= Decimal('.5'):
        advice.append({'code': 'main_device', 'deviceId': device, 'title': 'Prioriza este medidor', 'body': f'Concentra {devices[device] / total * 100:.1f}% del consumo de los últimos siete días completos. Revisa sus horarios de uso y evita dejar el agua corriendo entre actividades.', 'path': '/dispositivos'})
    if not advice:
        advice.append({'code': 'daily_average', 'title': 'Empieza por tu consumo habitual', 'body': f'Tu promedio de los últimos siete días completos fue {total / 7:.1f} L/día. Usa ese valor para fijar un presupuesto y revisar si tus cambios reducen el consumo.', 'path': '/alertas'})
    return advice[:3]
