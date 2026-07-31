from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from scheduling.models import SupportItem


class SeedNdisSupportItemsCommandTests(TestCase):
    def test_command_creates_and_updates_the_supported_2026_27_items(self):
        SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Outdated name",
            category="Outdated category",
            unit=SupportItem.Unit.EACH,
            price_limit=Decimal("1.00"),
            gst_code=SupportItem.GSTCode.TAXABLE,
            is_active=False,
        )
        unrelated_item = SupportItem.objects.create(
            item_number="LOCAL-ITEM-001",
            name="Local item",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("12.00"),
            gst_code=SupportItem.GSTCode.GST_FREE,
        )

        call_command("seed_ndis_support_items_2026_27")
        call_command("seed_ndis_support_items_2026_27")

        self.assertEqual(SupportItem.objects.count(), 4)
        self.assertEqual(SupportItem.objects.get(pk=unrelated_item.pk).name, "Local item")

        self.assertEqual(
            SupportItem.objects.get(item_number="01_011_0107_1_1").price_limit,
            Decimal("73.58"),
        )
        self.assertEqual(
            SupportItem.objects.get(item_number="04_104_0125_6_1").name,
            "Access Community Social and Rec Activ - Standard - Weekday Daytime",
        )
        travel_item = SupportItem.objects.get(item_number="04_799_0125_6_1")
        self.assertEqual(travel_item.name, "Provider travel - non-labour costs")
        self.assertEqual(travel_item.unit, SupportItem.Unit.EACH)
        self.assertEqual(travel_item.price_limit, Decimal("1.00"))
        self.assertEqual(travel_item.gst_code, SupportItem.GSTCode.GST_FREE)
        self.assertTrue(travel_item.is_active)
