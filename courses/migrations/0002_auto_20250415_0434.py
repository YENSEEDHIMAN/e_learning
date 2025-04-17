from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='certificate',
            name='issued_on',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
