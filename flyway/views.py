# -*- coding: utf-8 -*-

import json

from django.shortcuts import render, redirect, reverse
from django.http.response import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.views import View
from django.contrib.auth.decorators import login_required
from django.core import serializers
from pure_pagination import Paginator, EmptyPage, PageNotAnInteger
from mysql_platform.mysql_function import SQL

s = SQL('192.168.175.130', 3306, 'sqltool', 'mysqltool','test_remote_sql')


t_depandency_api = "http://dependency-t1.yonghuivip.com/api/database/customMigrate"
u_depandency_api = "http://flyway-test.yonghuivip.com/dependency-center-rest-api/database/customMigrate"
flyway_user = "flyway"
flyway_pass = "I0U1Bdw8uVWy"


def dictFetchall(cursor):
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

@login_required()
def check_db_if_exsits(request, db_name, env_name, is_shard):
    if is_shard == "db_main":
        sql = """SELECT 1 from yhops_flyway_db_detail a, yhops_flyway_env b where
            a.db_id =b.id and a.db_name='{0}' and b.env_name='{1}'""".format(db_name, env_name)
    else:
        sql = """SELECT 1 from yhops_flyway_sharding a, yhops_flyway_sharding_env b
            where a.flyway_sharding_id =b.id and a.db_name like '{0}%' and b.remask='{1}'""".format(db_name,  env_name)
    result = s.execute_and_fetchall(sql)
    if result:
        return True
    else:
        return False

def get_sharding_db_list(db_name, db_kind):
    if db_kind == "shard_16_01":
        db_list = [db_name + "_" + str(i) for i in range(1, 17)]
    elif db_kind == "shard_16_02":
        db_list1 = [db_name + str(1) + "_" + str(i) for i in range(1, 9)]
        db_list2 = [db_name + str(2) + "_" + str(i) for i in range(1, 9)]
        db_list = db_list1 + db_list2
    elif db_kind == "shard_16_03":
        db_list = [db_name + str(i) for i in range(1, 17)]
    elif db_kind == "shard_32_01":
        db_list = [db_name + "_" + str(i) for i in range(1, 33)]
    elif db_kind == "shard_32_02":
        db_list1 = [db_name + str(1) + "_" + str(i) for i in range(1, 17)]
        db_list2 = [db_name + str(2) + "_" + str(i) for i in range(1, 17)]
        db_list = db_list1 + db_list2
    elif db_kind == "shard_32_03":
        db_list = [db_name + str(i) for i in range(1, 33)]
    else:
        return []
    return db_list


@login_required()
def env_name_by_ajax_and_is_shard(request):
    is_shard = request.POST.get('is_shard', 0)
    if is_shard == "db_main":
        sql = "SELECT DISTINCT env as eenv from yhops_flyway_env where env !='online'"
    else:
        sql = "SELECT DISTINCT env_name as eenv from yhops_flyway_sharding_env where env_name !='online'"
    data = s.execute_and_return_dict(sql)
    return HttpResponse(json.dumps(data), content_type='application/json')


@login_required()
def host_by_ajax_and_env_name(request):
    is_shard = request.POST.get('is_shard', 0)
    env_name = request.POST.get('env_name', 0)
    print (env_name, is_shard)
    if is_shard == "db_main":
        sql = """SELECT env_name as eenv,CONCAT(env_name,'::',ip,':',`port`) as instance_info from yhops_flyway_env
            where env = '{0}'""".format(env_name)
    else:
        sql = """SELECT remask as eenv,GROUP_CONCAT(remask,'::',ip,":",`port`) as instance_info from yhops_flyway_sharding_env
                    where env_name ='{0}' GROUP BY remask""".format(env_name)
    print (sql)
    data = s.execute_and_return_dict(sql)
    return HttpResponse(json.dumps(data), content_type='application/json')


def get_project_name(db_name):
    s_project_name = "SELECT project_name  from yhops_project where project_db='{0}'".format(db_name)
    project_name = s.execute_and_return_value(s_project_name)
    if not project_name:
        project_name = db_name.replace('_', '-')
    return project_name

def get_project_id(db_name):
    s_project_name = "SELECT id from yhops_project where project_db='{0}'".format(db_name)
    project_id = s.execute_and_return_value(s_project_name)
    if not project_id:
        return ""
    return project_id

@login_required()
def non_shard_submit_step(request, db_name, env_name):
    s_db_id = "select id from yhops_flyway_env where env_name='{0}'".format(env_name)
    db_id = s.execute_and_return_value(s_db_id)
    project_name = get_project_name(db_name)
    insert_sql = """insert into yhops_flyway_db_detail(project_name, db_name,db_id,`status`,git_locaion)
                  VALUES ('{0}','{1}','{2}','{3}','{4}')""".format(project_name, db_name, db_id, "1", "backend")
    status = s.execute_and_return_status(insert_sql)
    if status == 'ok':
        data = {
            'status': 'ok',
            'result_content': '数据库已添加成功。'
        }
    else:
        data = {
            'status': 'error',
            'result_content': '增加数据库失败。'
        }
    return data


@login_required()
def sharding_submit_step(request, db_name, env_name, db_kind, sql_dir):
    s_db_id = """SELECT * from yhops_flyway_sharding_env where remask = '{0}' order by ip ; """.format(env_name)
    db_id_list = s.execute_and_fetchall(s_db_id)
    project_id = get_project_id(db_name)
    if not project_id:
        data = {
            'status': "error",
            'result_content': 'project_id不存在,请确认。'
        }
        return data
    db_list = get_sharding_db_list(db_name, db_kind)
    insert_sql = """insert into yhops_flyway_sharding(project_id,db_name,flyway_sharding_id) values
        ('{0}','{1}','{2}')"""
    insert_sql_with_dir = """insert into yhops_flyway_sharding(project_id,db_name,flyway_sharding_id,dir) values
            ('{0}','{1}','{2}','shard-sql')"""
    errors = []
    half = int(len(db_list)/2)
    full = len(db_list)
    db_id1 = db_id_list[0][0]
    db_id2 = db_id_list[1][0]
    if sql_dir:
        sql = insert_sql_with_dir
    else:
        sql = insert_sql
    for i in range(half):
        status = s.execute_and_return_status(sql.format(project_id, db_list[i], db_id1))
        errors.append(status)
    for i in range(half, full):
        status = s.execute_and_return_status(sql.format(project_id, db_list[i], db_id2))
        errors.append(status)
    if errors.count("nok") >0:
        data = {
            'status': "error",
            'result_content': '增加数据库失败。'
        }
    else:
        data = {
            'status': 'ok',
            'result_content': '数据库已添加成功。'
        }
    return data

@login_required()
def flyway_submit_step(request):
    db_name = request.POST.get('db_name', "")
    is_shard = request.POST.get('is_shard', "")
    env_name = request.POST.get('env_name', "")
    sql_dir = request.POST.get('sql_dir', "")
    print (request, db_name, env_name, is_shard)
    is_exsist = check_db_if_exsits(request, db_name, env_name, is_shard)
    if is_exsist:
        data = {
            'status': 'error',
            'result_content': '该DB在此环境下已存在对应关系，请点击shcema_list查看。'
        }
        return HttpResponse(json.dumps(data), content_type='application/json')

    if (sql_dir == "shard_sql") and (is_shard == "db_main"):
        data = {
            'status': 'error',
            'result_content': '非分库sql文件存放在shard-sql目录,Kidding？？？'
        }
        return HttpResponse(json.dumps(data), content_type='application/json')
    if not (db_name == 'none' or is_shard == 'none' or env_name =='none'):
        if is_shard == 'db_main':
           data = non_shard_submit_step(request, db_name, env_name)
        else:
            data = sharding_submit_step(request, db_name, env_name, is_shard, sql_dir)
    else:
        data = {
            'status': 'error',
            'result_content': '填写内容校验失败，请检查。'
        }
        return HttpResponse(json.dumps(data), content_type='application/json')

    return HttpResponse(json.dumps(data), content_type='application/json')

@login_required()
def schema_add(request):
    data = {
        'sub_module': '7_1'
    }
    return render(request, 'flyway/schema_add.html', data)


@login_required()
def main_schema_list(request):
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    sql = """SELECT a.id,b.env,b.env_name,a.project_name,a.db_name,b.ip,b.`port`,b.branch
          from yhops_flyway_db_detail a, yhops_flyway_env b
          where a.db_id =b.id and b.env !='online' ORDER by b.env"""
    record_list = s.execute_and_return_dict(sql)
    p = Paginator(record_list, 10, request=request)
    try:
        record_list_in_pages = p.page(page)
    except EmptyPage:
        record_list_in_pages = p.page(1)
    data = {
        'record_list': record_list_in_pages,
        'sub_module': '7_2_1'
    }
    return render(request, 'flyway/main_schema_list.html', data)

@login_required()
def shard_schema_list(request):
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    sql = """SELECT b.remask as env,c.project_name,GROUP_CONCAT(a.db_name order by a.id desc) as db_name,b.ip,b.`port`,
          b.branch,a.dir as sql_dir from yhops_flyway_sharding a, yhops_flyway_sharding_env b, yhops_project c
          where a.flyway_sharding_id=b.id and a.project_id=c.id and b.env_name!='online' group by remark,ip,`port` ORDER BY env """
    record_list = s.execute_and_return_dict(sql)
    p = Paginator(record_list, 10, request=request)
    try:
        record_list_in_pages = p.page(page)
    except EmptyPage:
        record_list_in_pages = p.page(1)

    data = {
        'record_list': record_list_in_pages,
        'sub_module': '7_2_2'
    }
    return render(request, 'flyway/shard_schema_list.html', data)

@login_required()
def instance_add(request):
    data = {
        'sub_module': '7_3'
    }
    return render(request, 'flyway/instance_add.html', data)


@login_required()
def check_main_instance_if_exsits(request, instance_ip, instance_port, remask, env_name):
    sql = """SELECT 1 from yhops_flyway_env where env_name='{0}' and env='{1}' and ip='{2}' and
            port='{3}'""".format(remask, env_name, instance_ip, instance_port)
    result = s.execute_and_fetchall(sql)
    if result:
        return True
    else:
        return False

@login_required()
def check_shard_instance_if_exsits(request, instance1, instance2, remask, env_name):
    instance1_ip, instance1_port = instance1.split(":")
    instance2_ip, instance2_port = instance2.split(":")
    sql1 = """SELECT 1 from yhops_flyway_sharding_env where env_name='{0}' and remask='{1}' and
        ip='{2}' and port='{3}''""".format(env_name, remask, instance1_ip, instance1_port)
    sql2 = """SELECT 1 from yhops_flyway_sharding_env where env_name='{0}' and remask='{1}' and
            ip='{2}' and port='{3}''""".format(env_name, remask, instance2_ip, instance2_port)
    result1 = s.execute_and_fetchall(sql1)
    result2 = s.execute_and_fetchall(sql2)
    if result1 or result2:
        return True
    else:
        return False


@login_required()
def non_shard_env_submit(request, remask, ip, port, branch, env_name):
    if env_name in ("t1", "t2"):
        depandency_api = t_depandency_api
    else:
        depandency_api = u_depandency_api
    sql = """INSERT into yhops_flyway_env(env_name,ip,port,username,password,branch,depandency_api,env)
        VALUES ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}')""".format(remask, ip, port, flyway_user, flyway_pass, branch, depandency_api, env_name)
    status = s.execute_and_return_status(sql)
    if status == "ok":
        msg = "已添加成功。"
        st = "ok"
    else:
        msg = "插入数据库报错，请重试。"
        st = 'error'
    data = {
        'status' : st,
        'result_content': msg
    }
    return data

@login_required()
def sharding_env_submit(request, remask, instance1, instance2, branch, env_name):
    if env_name in ("t1", "t2"):
        depandency_api = t_depandency_api
    else:
        depandency_api = u_depandency_api
    instance1_ip, instance1_port = instance1.split(":")
    instance2_ip, instance2_port = instance2.split(":")
    sql1 = """INSERT into yhops_flyway_sharding_env(env_name,remask,ip,port,username,password,branch,depandency_api)
                VALUES ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}')""".format(env_name, remask, instance1_ip,
                                                                                   instance1_port, flyway_user,
                                                                                   flyway_pass,
                                                                                   branch, depandency_api)
    sql2 = """INSERT into yhops_flyway_sharding_env(env_name,remask,ip,port,username,password,branch,depandency_api)
                VALUES ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}')""".format(env_name, remask, instance2_ip,
                                                                                   instance2_port, flyway_user,
                                                                                   flyway_pass,
                                                                                   branch, depandency_api)
    status1 = s.execute_and_return_status(sql1)
    status2 = s.execute_and_return_status(sql2)
    if status1 != "ok" or status2 != "ok":
        msg = "插入数据库报错，请重试。"
        st = "error"
    else:
        st = 'ok'
        msg = "已添加成功。"
    data = {
        'status' : st,
        'result_content': msg
    }
    return data


def deal_instance_add(request):
    remask = request.POST.get('remask', "")
    env_name = request.POST.get("env_name", "")
    is_shard = request.POST.get('is_shard', "")
    instance1 = request.POST.get('instance1', "")
    instance2 = request.POST.get('instance2', "")
    branch = request.POST.get('branch', "")

    if not (remask and env_name and is_shard and instance1 and branch):
        data = {
            'status': 'error',
            'result_content': '请检查是否所有选项已填写完成。'
        }
        return HttpResponse(json.dumps(data), content_type='application/json')
    try:
        instance1_ip, instance1_port = instance1.split(":")
        if is_shard != "db_main":
            instance2_ip, instance2_port = instance2.split(":")
    except:
        data = {
            'status': 'error',
            'result_content': 'IP端口请用英文符号的冒号间隔。'
        }
        return HttpResponse(json.dumps(data), content_type='application/json')
    if is_shard == "db_main":
        is_exsist = check_main_instance_if_exsits(request, instance1_ip, instance1_port, remask, env_name)
    else:
        is_exsist = check_shard_instance_if_exsits(request, instance1, instance2, remask, env_name)
    if is_exsist:
        data = {
            'status': 'error',
            'result_content': '该实例在此环境下已存在对应关系，请点击实例列表查看。'
        }
        return HttpResponse(json.dumps(data), content_type='application/json')

    if is_shard == 'db_main':
        data = non_shard_env_submit(request, remask, instance1_ip, instance1_port, branch, env_name)
    else:
        data = sharding_env_submit(request, remask, instance1, instance2, branch, env_name)

    return HttpResponse(json.dumps(data), content_type='application/json')


@login_required()
def all_instance_list(request):
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    sql = """SELECT * from (SELECT env_name as e_name, remask, ip,port,username,branch,'分库' as 'is_shard' from yhops_flyway_sharding_env
      where env_name !='online' UNION all SELECT env as e_name, env_name as remask,ip,port,username,branch,'非分库' as 'is_shard'
      from yhops_flyway_env where env != 'online') y order by e_name,is_shard,remask"""
    result = s.execute_and_fetchall(sql)
    data = {
        'result': result,
        'sub_module': '7_3_1'
    }
    return render(request, 'flyway/all_instance_list.html', data)


@login_required()
def deal_change_env_step(request, record_id):
    sql = """SELECT DISTINCT env from yhops_flyway_env where env_name not like '%online%'"""
    data_dict = s.execute_and_return_dict(sql)
    data = {
        'record_list': data_dict,
        'record_id': record_id
    }
    print (data['record_list'])
    return render(request, 'flyway/env_change.html', data)

@login_required()
def deal_change_env_submit(request):
    instance_id = request.POST.get("instance_id", "none")
    env_name = request.POST.get("env_name", "none")
    record_id = request.POST.get("record_id", 0)
    if  instance_id == "none" or env_name == "none":
        data = {
            'status': 'error',
            'result_content': '请选择需要切换的环境。'
        }
        return HttpResponse(json.dumps(data), content_type='application/json')

    sql = """update yhops_flyway_db_detail set db_id = (select id from yhops_flyway_env where env_name = '{0}' limit 1)
                where id = '{1}'""".format(instance_id, record_id)
    status = s.execute_and_return_status(sql)
    if status == 'ok':
        data = {
            'status': 'ok',
            'result_content': '已成功切换数据库环境。'
        }
    else:
        data = {
            'status': 'ok',
            'result_content': '切换数据库环境失败。'
        }
    return HttpResponse(json.dumps(data), content_type='application/json')


@login_required()
def deal_delete_schema_env(request):
    record_id = request.POST.get('record_id', "")
    if record_id:
        sql = "delete from yhops_flyway_db_detail where id = '{0}'".format(record_id)
        status = s.execute_and_return_status(sql)
        if status == 'ok':
            data = {
                'status': 'ok',
                'result_content': "删除数据库对应的环境信息成功。"
            }
        else:
            data = {
                'status': 'ok',
                'result_content': '删除数据库对应的环境信息失败。'
            }
    else:
        data = {
            'status': 'ok',
            'result_content': '选择删除的记录异常。'
        }
    return HttpResponse(json.dumps(data), content_type='application/json')


@login_required()
def new_message_by_ajax(request):
    message_list = MessageRecord.objects.filter(send_to=request.user.id, is_read=0).order_by('-id')[0:5]
    return HttpResponse(serializers.serialize("json", message_list), content_type='application/json')


@login_required()
def clear_unread_message_by_ajax(request):
    updated_message_number = MessageRecord.objects.filter(send_to=request.user.id, is_read=0).update(is_read=1)
    data = {
        'updated_message_number': updated_message_number
    }
    return HttpResponse(json.dumps(data), content_type='application/json')
