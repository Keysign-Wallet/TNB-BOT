# Generated by Django 3.1.5 on 2021-03-19 06:31

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('DiscordID', models.IntegerField()),
                ('Address', models.TextField()),
                ('PaymentDue', models.TextField()),
                ('VIP', models.BooleanField()),
            ],
        ),
    ]
