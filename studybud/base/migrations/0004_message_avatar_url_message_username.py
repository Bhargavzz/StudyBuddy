# Generated by Django 4.2.16 on 2025-07-16 14:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_user_avatar'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='avatar_url',
            field=models.CharField(default='/static/images/default-avatar.png', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='message',
            name='username',
            field=models.CharField(default='User', max_length=150),
            preserve_default=False,
        ),
    ]
