# Generated by Django 5.2.4 on 2025-07-12 19:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_department_options_department_date_joined_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='department',
            name='account_name',
            field=models.CharField(default='XXXXXXXXXX', max_length=200, verbose_name='Account Name'),
        ),
    ]
