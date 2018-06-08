"""mysql_platform URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from .views import schema_add, instance_add, main_schema_list, shard_schema_list,env_name_by_ajax_and_is_shard,host_by_ajax_and_env_name,flyway_submit_step,deal_instance_add,all_instance_list,deal_change_env_step,deal_change_env_submit,deal_delete_schema_env

urlpatterns = [
    url(r'^schema_add/', schema_add, name='schema_add'),
    url(r'^main_schema_info/', main_schema_list, name='main_schema_info'),
    url(r'^shard_schema_info/', shard_schema_list, name='shard_schema_info'),
    url(r'^instance_add/', instance_add, name='instance_add'),
    url(r'^instance_list/', all_instance_list, name='instance_list'),
    url(r'^env_name_by_ajax_and_is_shard/', env_name_by_ajax_and_is_shard, name='env_name_by_ajax_and_is_shard'),
    url(r'^host_by_ajax_and_env_name/', host_by_ajax_and_env_name, name='host_by_ajax_and_env_name'),
    url(r'^flyway_submit_step/', flyway_submit_step, name='flyway_submit_step'),
    url(r'^deal_change_env/(?P<record_id>[0-9]+)/', deal_change_env_step, name='deal_change_env'),
    url(r'^deal_instance_add/', deal_instance_add, name='deal_instance_add'),
    url(r'^change_env_submit/', deal_change_env_submit, name='deal_change_env_submit'),
    url(r'^deal_delete_schema_env/', deal_delete_schema_env, name='deal_delete_schema_env'),
]
