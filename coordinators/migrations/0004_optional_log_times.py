from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("coordinators", "0003_coordinationlogchange")]

    operations = [
        migrations.AlterField(
            model_name="coordinationlog", name="start_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="coordinationlog", name="end_time",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
