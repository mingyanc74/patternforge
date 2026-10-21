from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="s3connection",
            name="source_type",
            field=models.CharField(
                max_length=16,
                default="amazon_s3",
                choices=[
                    ("amazon_s3", "Amazon S3"),
                    ("sample", "Simulated sample bucket"),
                ],
            ),
        )
    ]
