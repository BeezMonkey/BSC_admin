import json
from datetime import date, datetime
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path

from django.template import Context, Template
from django.test import SimpleTestCase
from django.utils.html import json_script


CALENDAR_PATH = Path(__file__).parent / "data" / "qld_public_holidays.json"
REGIONS = ["QLD", "Brisbane", "Logan", "Gold Coast"]


class HolidayDataTests(SimpleTestCase):
    def setUp(self):
        self.assertTrue(CALENDAR_PATH.is_file(), "The verified calendar is missing.")
        self.calendar = json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))

    def test_calendar_records_verification_and_official_sources(self):
        self.assertEqual(
            set(self.calendar), {"verified_on", "sources", "coverage", "holidays"}
        )
        self.assertEqual(self.calendar["verified_on"], "2026-10-04")
        self.assertEqual(
            self.calendar["sources"],
            [
                "https://www.qld.gov.au/recreation/travel/holidays/public",
                "https://www.qld.gov.au/recreation/travel/holidays/show",
            ],
        )

    def test_coverage_only_claims_verified_years_and_regions(self):
        self.assertEqual(
            self.calendar["coverage"],
            {"2026": REGIONS, "2027": ["QLD", "Brisbane"]},
        )

    def test_holiday_entries_follow_the_shared_json_contract(self):
        for day, holidays in self.calendar["holidays"].items():
            with self.subTest(day=day):
                self.assertEqual(date.fromisoformat(day).isoformat(), day)
                self.assertIsInstance(holidays, list)
                self.assertTrue(holidays)
                for holiday in holidays:
                    self.assertEqual(set(holiday), {"name", "region", "hours"})
                    self.assertIsInstance(holiday["name"], str)
                    self.assertTrue(holiday["name"].strip())
                    self.assertIn(holiday["region"], self.calendar["coverage"][day[:4]])
                    self.assertIn(holiday["hours"], {"All day", "6 pm - midnight"})

    def assert_statewide_dates(self, year, expected):
        actual = {
            day: holidays
            for day, entries in self.calendar["holidays"].items()
            if day.startswith(f"{year}-")
            and (holidays := [entry for entry in entries if entry["region"] == "QLD"])
        }
        self.assertEqual(
            actual,
            {
                f"{year}-{day}": [
                    {
                        "name": name,
                        "region": "QLD",
                        "hours": "6 pm - midnight" if day == "12-24" else "All day",
                    }
                ]
                for day, name in expected.items()
            },
        )

    def test_all_2026_statewide_dates_match_the_official_calendar(self):
        self.assert_statewide_dates(
            2026,
            {
                "01-01": "New Year's Day",
                "01-26": "Australia Day",
                "04-03": "Good Friday",
                "04-04": "The day after Good Friday",
                "04-05": "Easter Sunday",
                "04-06": "Easter Monday",
                "04-25": "Anzac Day",
                "05-04": "Labour Day",
                "10-05": "King's Birthday",
                "12-24": "Christmas Eve",
                "12-25": "Christmas Day",
                "12-26": "Boxing Day",
                "12-28": "Boxing Day (additional holiday)",
            },
        )

    def test_all_2027_statewide_dates_match_the_official_calendar(self):
        self.assert_statewide_dates(
            2027,
            {
                "01-01": "New Year's Day",
                "01-26": "Australia Day",
                "03-26": "Good Friday",
                "03-27": "The day after Good Friday",
                "03-28": "Easter Sunday",
                "03-29": "Easter Monday",
                "04-26": "Anzac Day",
                "05-03": "Labour Day",
                "10-04": "King's Birthday",
                "12-24": "Christmas Eve",
                "12-25": "Christmas Day",
                "12-26": "Boxing Day",
                "12-27": "Christmas Day (additional holiday)",
                "12-28": "Boxing Day (additional holiday)",
            },
        )
        self.assertNotIn("2027-04-25", self.calendar["holidays"])

    def test_every_verified_regional_show_date_is_explicit(self):
        actual = {
            day: holidays
            for day, entries in self.calendar["holidays"].items()
            if (holidays := [entry for entry in entries if entry["region"] != "QLD"])
        }
        expected = {
            "2026-08-10": ("Royal Queensland Show", "Logan"),
            "2026-08-12": ("Royal Queensland Show", "Brisbane"),
            "2026-08-28": ("Gold Coast Show", "Gold Coast"),
            "2027-08-11": ("Royal Queensland Show", "Brisbane"),
        }
        self.assertEqual(
            actual,
            {
                day: [{"name": name, "region": region, "hours": "All day"}]
                for day, (name, region) in expected.items()
            },
        )

    def test_only_christmas_eve_is_a_part_day_holiday(self):
        self.assertEqual(
            [
                (day, holiday["hours"])
                for day, holidays in self.calendar["holidays"].items()
                for holiday in holidays
                if holiday["hours"] != "All day"
            ],
            [("2026-12-24", "6 pm - midnight"), ("2027-12-24", "6 pm - midnight")],
        )


class HolidayHelperTests(SimpleTestCase):
    def setUp(self):
        self.assertIsNotNone(
            find_spec("scheduling.holidays"), "The holiday presentation helpers are missing."
        )
        self.helpers = import_module("scheduling.holidays")

    def test_calendar_data_returns_the_bundled_json_as_a_dictionary(self):
        self.assertEqual(
            self.helpers.calendar_data(),
            json.loads(CALENDAR_PATH.read_text(encoding="utf-8")),
        )

    def test_calendar_data_cannot_be_mutated_by_a_caller(self):
        calendar = self.helpers.calendar_data()
        calendar["coverage"]["2027"].append("Logan")
        calendar["holidays"]["2026-10-05"][0]["name"] = "Changed"

        fresh = self.helpers.calendar_data()
        self.assertEqual(fresh["coverage"]["2027"], ["QLD", "Brisbane"])
        self.assertEqual(fresh["holidays"]["2026-10-05"][0]["name"], "King's Birthday")

    def test_holidays_on_accepts_date_and_iso_date(self):
        for value in (date(2026, 10, 5), "2026-10-05"):
            with self.subTest(value=value):
                self.assertEqual(
                    self.helpers.holidays_on(value),
                    [{"name": "King's Birthday", "region": "QLD", "hours": "All day"}],
                )

    def test_holidays_on_accepts_datetime_without_losing_the_date(self):
        self.assertEqual(
            self.helpers.holidays_on(datetime(2026, 10, 5, 10, 30)),
            self.helpers.holidays_on(date(2026, 10, 5)),
        )

    def test_holidays_on_preserves_region_and_part_day_hours(self):
        self.assertEqual(self.helpers.holidays_on("2026-08-10")[0]["region"], "Logan")
        self.assertEqual(
            self.helpers.holidays_on("2026-12-24"),
            [{"name": "Christmas Eve", "region": "QLD", "hours": "6 pm - midnight"}],
        )

    def test_holidays_on_returns_empty_list_for_ordinary_or_unknown_dates(self):
        for value in ("2026-10-06", "2027-04-25", "2028-01-01"):
            with self.subTest(value=value):
                self.assertEqual(self.helpers.holidays_on(value), [])

    def test_holidays_on_handles_invalid_inputs_without_raising(self):
        for value in (None, "", "not-a-date", "2026-02-30", "05/10/2026", 20261005, [], {}):
            with self.subTest(value=value):
                self.assertEqual(self.helpers.holidays_on(value), [])

    def test_holidays_on_requires_a_canonical_iso_date_string(self):
        for value in ("20261005", "2026-W41-1", "2026-10-05T10:30:00"):
            with self.subTest(value=value):
                self.assertEqual(self.helpers.holidays_on(value), [])

    def test_holidays_on_cannot_mutate_the_shared_calendar(self):
        holidays = self.helpers.holidays_on("2026-10-05")
        holidays[0]["region"] = "Logan"
        holidays.clear()

        self.assertEqual(
            self.helpers.holidays_on("2026-10-05"),
            [{"name": "King's Birthday", "region": "QLD", "hours": "All day"}],
        )

    def test_fully_verified_year_does_not_warn(self):
        self.assertEqual(self.helpers.coverage_warning(date(2026, 1, 1)), "")
        self.assertEqual(self.helpers.coverage_warning("2026-01-01", "2026-12-31"), "")

    def test_partial_coverage_warns_only_about_unverified_regions(self):
        warning = self.helpers.coverage_warning("2027-08-11")

        self.assertIn("2027", warning)
        self.assertIn("not verified", warning.lower())
        self.assertIn("Logan", warning)
        self.assertIn("Gold Coast", warning)
        self.assertNotIn("Brisbane", warning)
        self.assertNotIn("QLD", warning)

    def test_unknown_year_warns_for_all_regions(self):
        warning = self.helpers.coverage_warning("2030-01-01")

        self.assertIn("2030", warning)
        self.assertIn("not verified", warning.lower())
        for region in REGIONS:
            self.assertIn(region, warning)

    def test_coverage_warning_checks_each_year_of_an_inclusive_range(self):
        warning = self.helpers.coverage_warning(date(2026, 12, 31), "2028-01-01")

        self.assertNotIn("2026", warning)
        self.assertIn("2027", warning)
        self.assertIn("2028", warning)
        self.assertIn("Logan", warning)
        self.assertIn("Gold Coast", warning)

    def test_reversed_ranges_have_the_same_coverage_warning(self):
        self.assertEqual(
            self.helpers.coverage_warning("2028-01-01", "2026-12-31"),
            self.helpers.coverage_warning("2026-12-31", "2028-01-01"),
        )

    def test_none_end_is_a_single_date_check(self):
        self.assertEqual(
            self.helpers.coverage_warning("2027-01-01", None),
            self.helpers.coverage_warning("2027-01-01"),
        )

    def test_coverage_warning_handles_invalid_inputs_without_raising(self):
        for value in (None, "", "not-a-date", "2026-02-30", 2027, [], {}):
            with self.subTest(value=value):
                self.assertEqual(self.helpers.coverage_warning(value), "")
                self.assertEqual(self.helpers.coverage_warning(value, "2027-01-01"), "")
                if value is not None:
                    self.assertEqual(self.helpers.coverage_warning("2027-01-01", value), "")


class HolidayTemplateTagTests(SimpleTestCase):
    def setUp(self):
        tag_directory = Path(__file__).parent / "templatetags"
        self.assertTrue((tag_directory / "__init__.py").is_file())
        self.assertTrue((tag_directory / "holiday_tags.py").is_file())

    def test_calendar_data_tag_supplies_a_dictionary_for_json_script(self):
        rendered = Template(
            '{% load holiday_tags %}{% holiday_calendar_data as calendar %}'
            '{{ calendar|json_script:"holiday-data" }}'
        ).render(Context())

        self.assertEqual(
            rendered,
            json_script(json.loads(CALENDAR_PATH.read_text(encoding="utf-8")), "holiday-data"),
        )

    def test_holidays_on_tag_supports_date_and_iso_string_assignment(self):
        template = Template(
            "{% load holiday_tags %}{% holidays_on day as holidays %}"
            "{% for holiday in holidays %}"
            "{{ holiday.name }}|{{ holiday.region }}|{{ holiday.hours }}"
            "{% endfor %}"
        )
        for day in (date(2026, 12, 24), "2026-12-24"):
            with self.subTest(day=day):
                self.assertEqual(
                    template.render(Context({"day": day})),
                    "Christmas Eve|QLD|6 pm - midnight",
                )

    def test_holidays_on_tag_handles_an_empty_date(self):
        rendered = Template(
            "{% load holiday_tags %}{% holidays_on day as holidays %}"
            "{{ holidays|length }}"
        ).render(Context({"day": None}))

        self.assertEqual(rendered, "0")

    def test_coverage_warning_tag_supports_one_date_and_a_range(self):
        helpers = import_module("scheduling.holidays")
        rendered = Template(
            "{% load holiday_tags %}{% holiday_coverage_warning start %}"
        ).render(Context({"start": "2027-01-01"}))
        self.assertEqual(rendered, helpers.coverage_warning("2027-01-01"))

        rendered = Template(
            "{% load holiday_tags %}{% holiday_coverage_warning start end as warning %}"
            "{{ warning }}"
        ).render(Context({"start": "2026-12-31", "end": date(2028, 1, 1)}))
        self.assertEqual(rendered, helpers.coverage_warning("2026-12-31", "2028-01-01"))

    def test_coverage_warning_tag_is_empty_for_verified_or_invalid_dates(self):
        template = Template("{% load holiday_tags %}{% holiday_coverage_warning day %}")

        for day in ("2026-01-01", None, "invalid"):
            with self.subTest(day=day):
                self.assertEqual(template.render(Context({"day": day})), "")
