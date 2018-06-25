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
from django.conf.urls import url
from .query import sqlquery, getTableNameList, sqlquery_and_return, querylog, \
	getdbNameList, query, explain
from .sqlad import sqladvisor, sqladvisorcheck

urlpatterns = [
    url(r'^sqlquery/', sqlquery, name='sqlquery'),
    url(r'^getTableNameList/$', getTableNameList, name='getTableNameList'),
    url(r'^sqlquery_and_return/$', sqlquery_and_return, name='sqlquery_get_result'),
    url(r'querylog/$', querylog, name='querylog'),
    url(r'getdbNameList/$', getdbNameList, name='getdbNameList'),
    url(r'query/$', query, name='query'),
    url(r'explain/$', explain, name='explain'),
    url(r'sqladvisor/$', sqladvisor, name='sqladvisor'),
    url(r'^sqladvisorcheck/$', sqladvisorcheck, name='sqladvisorcheck'),
]
