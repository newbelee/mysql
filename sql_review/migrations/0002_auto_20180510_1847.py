# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-05-10 10:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('statistics', '0003_auto_20170827_2320'),
        ('sql_review', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SqlReviewRecord_old',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('for_what', models.CharField(max_length=255, verbose_name='\u6267\u884csql\u7684\u76ee\u7684')),
                ('user_name', models.CharField(default='system', max_length=30, verbose_name='\u7533\u8bf7\u4eba')),
                ('pm_name', models.CharField(default='system', max_length=30, verbose_name='\u9879\u76ee\u7ecf\u7406\u540d')),
                ('submit_time', models.DateTimeField(auto_now=True, verbose_name='\u63d0\u4ea4\u8bf7\u6c42\u7684\u65f6\u95f4')),
                ('execute_time', models.DateTimeField(verbose_name='\u8981\u6c42\u6267\u884c\u7684\u65f6\u95f4')),
                ('sql', models.TextField(verbose_name='\u60f3\u8981\u6267\u884c\u7684SQL')),
                ('is_checked', models.IntegerField(default=0, verbose_name='\u673a\u5668\u5ba1\u6838\u72b6\u6001')),
                ('is_submitted', models.IntegerField(default=0, verbose_name='\u63d0\u4ea4\u72b6\u6001')),
                ('is_reviewed', models.IntegerField(default=0, verbose_name='\u9879\u76ee\u7ecf\u7406\u5ba1\u6838\u72b6\u6001')),
                ('is_executed', models.IntegerField(default=0, verbose_name='\u6267\u884c\u72b6\u6001')),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='statistics.MysqlInstance', verbose_name='\u5bf9\u5e94\u7ec4\u5185\u7684\u5177\u4f53\u5b9e\u4f8b')),
                ('instance_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='statistics.MysqlInstanceGroup', verbose_name='\u5b9e\u4f8b\u7ec4')),
            ],
            options={
                'verbose_name': 'SQL\u5ba1\u6838\u63d0\u4ea4\u8bb0\u5f55',
                'verbose_name_plural': 'SQL\u5ba1\u6838\u63d0\u4ea4\u8bb0\u5f55',
            },
        ),
        migrations.RemoveField(
            model_name='sqlreviewrecord',
            name='instance',
        ),
        migrations.RemoveField(
            model_name='sqlreviewrecord',
            name='instance_group',
        ),
        migrations.RemoveField(
            model_name='sqlreviewrecord',
            name='pm_name',
        ),
        migrations.AddField(
            model_name='sqlreviewrecord',
            name='conn_id',
            field=models.IntegerField(default=0, verbose_name='\u8fde\u63a5\u7684\u5b9e\u4f8bID'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sqlreviewrecord',
            name='db_id',
            field=models.IntegerField(default=0, verbose_name='database ID'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='sqlreviewrecord',
            name='is_reviewed',
            field=models.IntegerField(default=0, verbose_name='\u9879\u76ee\u8d1f\u8d23\u4eba\u5ba1\u6838\u72b6\u6001'),
        ),
        migrations.AlterModelTable(
            name='sqlreviewrecord',
            table='t_sql_review_record',
        ),
    ]
