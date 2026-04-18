import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0002_post_social_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='replies',
                to='posts.post',
            ),
        ),
    ]
