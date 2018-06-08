# -*- coding: utf-8 -*-

from django.contrib import admin

#from models import MysqlInstance, InstanceRelation, MysqlInstanceGroup, BackupInstance
from .models import MysqlInstance, MysqlInstanceGroup, BackupInstance, InstanceRelation


# Register your models here.


class MysqlInstanceAdmin(admin.ModelAdmin):
    pass


class InstanceRelationAdmin(admin.ModelAdmin):
    pass


class MysqlInstanceGroupAdmin(admin.ModelAdmin):
    pass


class BackupInstanceAdmin(admin.ModelAdmin):
    pass

admin.site.register(MysqlInstance, MysqlInstanceAdmin)
admin.site.register(InstanceRelation, InstanceRelationAdmin)
admin.site.register(MysqlInstanceGroup, MysqlInstanceGroupAdmin)
admin.site.register(BackupInstance, BackupInstanceAdmin)
