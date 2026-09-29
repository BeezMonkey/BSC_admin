from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from service_logs.filters import format_hours, resolve_service_date_filter


class ServiceDateFilterTests(SimpleTestCase):
    def test_resolves_current_week_from_monday_to_sunday(self):
        result = resolve_service_date_filter(
            "this_week",
            "",
            "",
            today=date(2026, 9, 29),
        )

        self.assertEqual(result["start"], date(2026, 9, 28))
        self.assertEqual(result["end"], date(2026, 10, 4))

    def test_resolves_previous_and_current_billing_periods(self):
        expected = {
            "last_week": (date(2026, 9, 21), date(2026, 9, 27)),
            "this_fortnight": (date(2026, 9, 28), date(2026, 10, 11)),
            "last_fortnight": (date(2026, 9, 14), date(2026, 9, 27)),
            "this_month": (date(2026, 9, 1), date(2026, 9, 30)),
            "last_month": (date(2026, 8, 1), date(2026, 8, 31)),
        }

        for key, bounds in expected.items():
            with self.subTest(key=key):
                result = resolve_service_date_filter(
                    key,
                    "",
                    "",
                    today=date(2026, 9, 29),
                )

                self.assertEqual((result["start"], result["end"]), bounds)

    def test_custom_range_accepts_open_and_reversed_bounds(self):
        result = resolve_service_date_filter(
            "custom",
            "2026-09-20",
            "",
            today=date(2026, 9, 29),
        )
        reversed_result = resolve_service_date_filter(
            "custom",
            "2026-09-30",
            "2026-09-01",
            today=date(2026, 9, 29),
        )

        self.assertEqual(result["start"], date(2026, 9, 20))
        self.assertIsNone(result["end"])
        self.assertGreater(reversed_result["start"], reversed_result["end"])

    def test_invalid_values_are_safe_and_preserved_for_correction(self):
        result = resolve_service_date_filter(
            "unknown",
            "bad",
            "2026-99-99",
            today=date(2026, 9, 29),
        )
        custom = resolve_service_date_filter(
            "custom",
            "bad",
            "2026-99-99",
            today=date(2026, 9, 29),
        )

        self.assertEqual(result["key"], "all")
        self.assertIsNone(result["start"])
        self.assertIsNone(result["end"])
        self.assertEqual(custom["start_value"], "bad")
        self.assertEqual(custom["end_value"], "2026-99-99")

    def test_formats_hours_without_unnecessary_zeroes(self):
        self.assertEqual(format_hours(Decimal("22.50")), "22.5")
        self.assertEqual(format_hours(None), "0")
