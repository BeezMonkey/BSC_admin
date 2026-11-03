from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("service_logs", "0003_servicelog_source_servicelog_unscheduled_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicelog", name="submission_key",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddConstraint(
            model_name="servicelog",
            constraint=models.UniqueConstraint(
                fields=("submission_key",), name="unique_service_log_submission",
            ),
        ),
    ]
