# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-12-21 17:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('siteapp', '0011_organization_allowed_modules'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='allowed_modules',
            field=models.TextField(blank=True, default='', help_text='A list of module keys of `access: private` project modules that this Organization has permission to use, separated by spaces or newlines.'),
        ),
    ]
