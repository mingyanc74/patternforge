import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_s3connection_source_type")]
    operations = [
        migrations.AddField(
            model_name="job", name="dataset_path", field=models.CharField(max_length=1024, blank=True)
        ),
        migrations.AddField(
            model_name="job", name="dataset_expires_at", field=models.DateTimeField(null=True, blank=True)
        ),
        migrations.AddField(
            model_name="job",
            name="input_dataset",
            field=models.ForeignKey(
                "core.job",
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transforms",
            ),
        ),
    ]
