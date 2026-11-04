import unittest
from datetime import date, timedelta
from app.analytics.domain.model.valueobjects.consumption_insights import comparison_ranges, compare_periods, recommendations


def rows(start, end, liters=100):
    return [{'date': (start + timedelta(days=i)).isoformat(), 'deviceId': 'meter', 'liters': liters} for i in range((end-start).days)]


class ConsumptionInsightsTests(unittest.TestCase):
    def test_weekly_uses_two_complete_weeks_and_ignores_today(self):
        today = date(2026, 11, 3)
        data = rows(date(2026, 10, 19), date(2026, 10, 26), 100) + rows(date(2026, 10, 26), date(2026, 11, 2), 150)
        data += rows(today, today+timedelta(days=1), 999999)
        value = compare_periods(data, comparison_ranges(today))['weekly']
        self.assertTrue(value['available'])
        self.assertEqual((value['currentLiters'], value['previousLiters'], value['changePercent']), (1050, 700, 50))
        self.assertEqual((value['currentStart'], value['currentEnd']), ('2026-10-26', '2026-11-01'))

    def test_monthly_uses_same_number_of_completed_days_across_year_and_leap_boundary(self):
        for today in (date(2027, 1, 3), date(2028, 3, 31)):
            ranges = comparison_ranges(today)
            start, end, previous, previous_end = ranges['monthly']
            self.assertEqual((end-start).days, (previous_end-previous).days)
            data = rows(start, end, 200) + rows(previous, previous_end, 100)
            value = compare_periods(data, ranges)['monthly']
            self.assertTrue(value['available'])
            self.assertEqual(value['changePercent'], 100)
        self.assertEqual(comparison_ranges(date(2028, 3, 31))['monthly'][1], date(2028, 3, 30))

    def test_missing_days_and_first_of_month_are_not_presented_as_zero_consumption(self):
        today = date(2026, 11, 3)
        self.assertFalse(compare_periods(rows(date(2026, 11, 1), today), comparison_ranges(today))['monthly']['available'])
        self.assertIsNone(compare_periods([], comparison_ranges(today))['weekly']['currentLiters'])
        self.assertIn('segundo día', compare_periods([], comparison_ranges(date(2026, 11, 1)))['monthly']['reason'])

    def test_recorded_zero_is_valid_but_does_not_create_an_infinite_percentage(self):
        today = date(2026, 11, 3)
        data = rows(date(2026, 10, 1), date(2026, 10, 3), 0) + rows(date(2026, 11, 1), today, 100)
        value = compare_periods(data, comparison_ranges(today))['monthly']
        self.assertTrue(value['available'])
        self.assertEqual(value['previousLiters'], 0)
        self.assertIsNone(value['changePercent'])

    def test_recommendations_use_actual_trend_and_device_and_wait_for_history(self):
        today = date(2026, 11, 3)
        data = rows(date(2026, 10, 19), date(2026, 10, 26), 100) + rows(date(2026, 10, 26), today, 150)
        advice = recommendations(data, compare_periods(data, comparison_ranges(today)), today)
        self.assertEqual(advice[0]['code'], 'weekly_increase')
        self.assertIn('50.0%', advice[0]['body'])
        self.assertEqual(advice[-1]['deviceId'], 'meter')
        self.assertEqual(recommendations(data[-2:], compare_periods(data, comparison_ranges(today)), today), [])
        self.assertEqual(recommendations(rows(today-timedelta(days=7), today, 0), compare_periods([], comparison_ranges(today)), today), [])

