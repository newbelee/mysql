# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from statistics.models import MysqlInstanceGroup, MysqlInstance

import sys

# 记录在线查询sql的日志
class QueryLog(models.Model):
    cluster_name = models.CharField('集群名称', max_length=50)
    db_name = models.CharField('数据库名称', max_length=30)
    sqllog = models.TextField('执行的sql查询')
    effect_row = models.BigIntegerField('返回行数')
    cost_time = models.CharField('执行耗时', max_length=10, default='')
    username = models.CharField('操作人', max_length=30)
    create_time = models.DateTimeField('操作时间', auto_now_add=True)
    sys_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_query_log'
        verbose_name = u'sql查询日志'
        verbose_name_plural = u'sql查询日志'