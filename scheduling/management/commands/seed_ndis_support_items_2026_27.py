from decimal import Decimal

from django.core.management.base import BaseCommand

from scheduling.models import SupportItem


SUPPORT_ITEMS = (
    {
        "item_number": "01_011_0107_1_1",
        "name": "Assistance With Self-Care Activities - Standard - Weekday Daytime",
        "category": "Core Supports",
        "unit": SupportItem.Unit.HOUR,
        "price_limit": Decimal("73.58"),
        "gst_code": SupportItem.GSTCode.GST_FREE,
        "is_active": True,
        "notes": "2026-27 NDIS Pricing Schedule v1.2. National price.",
    },
    {
        "item_number": "04_104_0125_6_1",
        "name": "Access Community Social and Rec Activ - Standard - Weekday Daytime",
        "category": "Core Supports",
        "unit": SupportItem.Unit.HOUR,
        "price_limit": Decimal("73.58"),
        "gst_code": SupportItem.GSTCode.GST_FREE,
        "is_active": True,
        "notes": "2026-27 NDIS Pricing Schedule v1.2. National price.",
    },
    {
        "item_number": "04_799_0125_6_1",
        "name": "Provider travel - non-labour costs",
        "category": "Core Supports",
        "unit": SupportItem.Unit.EACH,
        "price_limit": Decimal("1.00"),
        "gst_code": SupportItem.GSTCode.GST_FREE,
        "is_active": True,
        "notes": (
            "2026-27 NDIS Pricing Schedule v1.2. Claim-value mechanism. "
            "Do not automatically convert worker kilometres into a claim amount."
        ),
    },
)


class Command(BaseCommand):
    help = "Seed the three verified 2026-27 NDIS support items used by Brisbane Star Care."

    def handle(self, *args, **options):
        for item_data in SUPPORT_ITEMS:
            item_number = item_data["item_number"]
            _, created = SupportItem.objects.update_or_create(
                item_number=item_number,
                defaults=item_data,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action}: {item_number}")

        self.stdout.write(self.style.SUCCESS("NDIS support items are ready."))
