# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-05-11 02:38
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statistics', '0004_auto_20180510_1853'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='instancerelation',
            options={},
        ),
        migrations.RemoveField(
            model_name='instancerelation',
            name='belong_group',
        ),
        migrations.RemoveField(
            model_name='instancerelation',
            name='master_instance',
        ),
        migrations.RemoveField(
            model_name='instancerelation',
            name='slave_instance',
        ),
    ]
