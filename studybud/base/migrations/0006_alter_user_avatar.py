# Generated by Django 4.2.16 on 2025-07-16 18:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_alter_user_avatar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='avatar',
            field=models.URLField(default='https://avatar.iran.liara.run/public/17', null=True),
        ),
    ]
