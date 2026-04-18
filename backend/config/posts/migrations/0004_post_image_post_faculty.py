# Generated migration for Post image and faculty fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('posts', '0003_post_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='posts/'),
        ),
        migrations.AddField(
            model_name='post',
            name='faculty',
            field=models.CharField(
                choices=[
                    ('fit', 'IT & Engineering'),
                    ('bs', 'Business School'),
                    ('ise', 'Economics'),
                    ('feogi', 'Oil & Gas'),
                    ('smsgt', 'Social Sciences'),
                    ('kma', 'Maritime'),
                    ('sam', 'Applied Math'),
                    ('sce', 'Chemical Engineering'),
                ],
                default='fit',
                max_length=20,
            ),
        ),
    ]
