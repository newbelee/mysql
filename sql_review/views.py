# -*- coding: utf-8 -*-
#from __future__ import print_function
from __future__ import unicode_literals
from datetime import datetime, timedelta
from contextlib import contextmanager
# import pymysql
import json
from pymysql.constants.CLIENT import MULTI_STATEMENTS, MULTI_RESULTS
from django.http.response import HttpResponse, HttpResponseRedirect

from django.shortcuts import render, redirect, reverse, render_to_response
from django.core import serializers
from django.contrib.auth.decorators import login_required

from mysql_platform.settings import INCEPTION_IP, INCEPTION_PORT, BACKUP_HOST_IP, BACKUP_HOST_PORT, BACKUP_PASSWORD
from mysql_platform.settings import BACKUP_USER
from statistics.models import MysqlInstance, MysqlInstanceGroup
from sql_review.models import SqlReviewRecord, SqlBackupRecord, SpecificationContentForSql, SpecificationTypeForSql
from sql_review.forms import SqlReviewRecordForm
from users.models import UserProfile, MessageRecord

from pure_pagination import Paginator, EmptyPage, PageNotAnInteger

from utils.log import my_logger
import pymysql
from mysql_platform.mysql_function import SQL
from  .Inceptions import Inception
from users.endecrypt import endeCrypt


s = SQL()
# 或者读写用户
en = endeCrypt()
review_user, review_password = en.get_ro_user_pass()
admin_user, admin_password = en.get_rw_user_pass()

# 连接mysql配置
conn_args = dict(host='127.0.0.1', user='root', password='test123', db='platform', port=3306, charset="utf8mb4")


def dictFetchall(cursor):
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


@contextmanager
def get_mysql_conn():
    conn = pymysql.connect(**conn_args)
    try:
        yield conn
    finally:
        conn.close()



@login_required()
def review(request, record_id):
    s_sql = """select a.submit_sql,b.dbname,c.host,c.port from
        t_sql_review_record a,t_db_basic_info b, t_db_conn_info c where
        a.db_id=b.id and a.conn_id=c.id  and a.id = {0}"""
    s = SQL()
    rows = s.execute_and_fetchall(s_sql.format(record_id))
    if rows:
        submit_sql = rows[0][0]
        dbname = rows[0][1]
        instance_ip = rows[0][2]
        instance_port = rows[0][3]
    else:
        return HttpResponse('Error ...', status=500)

    exec_sql = Inception.get_enable_check_sql(submit_sql, instance_ip, instance_port, dbname)
    try:
        with Inception.get_inception_conn as cur:
            ret = cur.execute(exec_sql)
            num_fields = len(cur.description)
            field_names = [i[0] for i in cur.description]
            result = cur.fetchall()
        # 判断结果中是否有error level 为 2 的，如果有，则不做操作，如果没有则将sql_review_record 记录的 is_checked 设为1
        flag = 'success'
        for res in result:
            if res[2] == 2:
                flag = 'failed'
        if flag == 'success':
            with get_mysql_conn() as conn:
                with conn as cur:
                    cur.execute("update t_sql_review_record set is_checked=1 where id = {}".format(record_id))
        #第一行为use database，丢弃
        if len(result) > 1:
            result = result[1:]

        data = {
            'field_names': field_names,
            'result': result,
            'sub_module': '2_1',
            'flag': flag,
            'record_id': record_id,
            'sql': submit_sql
        }
        return render(request, 'sql_review/result.html', data)
    except:
        return HttpResponse('Mysql Error ...', status=500)

@login_required()
def failed_to_pass_list(request):
    # 取出账号权限下所有的审核请求
    select_sql = """select a.id,a.for_what,a.user_name,a.submit_time,a.execute_time,a.submit_sql,a.is_checked,
         a.is_submitted,a.is_reviewed,a.is_executed,b.dbname,c.env_name
         from t_sql_review_record a,t_db_basic_info b, t_db_conn_info c
         where  a.db_id=b.id and a.conn_id=c.id and a.is_submitted=1 and a.is_reviewed !=1 order by a.id desc limit 200"""
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    with  get_mysql_conn() as conn:
        with conn as cur:
            cur.execute(select_sql)
            record_list = dictFetchall(cur)

    p = Paginator(record_list, 10, request=request)
    try:
        record_list_in_pages = p.page(page)
    except EmptyPage:
        record_list_in_pages = p.page(1)
    print(record_list_in_pages)
    data = {
        'record_list': record_list_in_pages,
        'sub_module': '2_6'
    }
    return render(request, 'sql_review/checked_failed_list.html', data)

    return redirect(reverse('sql_review_reviewed_list'))


#@login_required(identity=('operation', 'project_manager'))
@login_required
def pm_review(request, record_id):
    s = SQL()
    submit_sql,dbname,instance_ip,instance_port = s.get_db_info_from_record_id(record_id)

    exec_sql = "/*--user=%s;--password=%s; --enable-check;--host=%s;--disable-remote-backup;--port=%s;*/\
                        inception_magic_start;\
                        use %s;" % ('root', 'test123',
                                    instance_ip, int(instance_port), dbname)

    if str(submit_sql).strip()[-1:] != ";":
        exec_sql = exec_sql + str(submit_sql).strip() + ";"
    else:
        exec_sql = exec_sql + str(submit_sql).strip()
    exec_sql = exec_sql + "inception_magic_commit;"

    try:
        conn = pymysql.connect(host=INCEPTION_IP, user='', passwd='', db='', port=INCEPTION_PORT, charset='utf8')
        cur = conn.cursor()
        ret = cur.execute(exec_sql)
        num_fields = len(cur.description)
        field_names = [i[0] for i in cur.description]
        result = cur.fetchall()
        cur.close()
        conn.close()
        # 第一行为use database，丢弃
        if len(result) > 1:
            result = result[1:]

        data = {
            'field_names': field_names,
            'result': result,
            'sub_module': '2_1',
            'record_id': record_id,
            'sql': submit_sql
        }
        return render(request, 'sql_review/pm_review_result.html', data)
    except pymysql.Error as e:
        return HttpResponse('Mysql Error {}: {}'.format(e.args[0], e.args[1]), status=500)


@login_required()
def submit_to_pm(request):
    record_id = request.POST.get('record_id', 0)
    with get_mysql_conn() as conn:
        with conn as cur:
            try:
                cur.execute('update t_sql_review_record set is_submitted = 1 where id = {} '.format(record_id))
                u_status = 'success'
            except:
                u_status = 'error'

    data = {
        'status': u_status
    }
    return HttpResponse(json.dumps(data), content_type='application/json')


#@login_required(identity=('operation', 'project_manager'))
@login_required()
def submit_to_ops(request, record_id):
    # record = SqlReviewRecord.objects.get(id=record_id)
    # record.is_reviewed = 1
    # record.save()
    sql = "update t_sql_review_record set is_reviewed=1 where id = {}".format(record_id)
    e_status = s.execute_and_return_status(sql)
    return redirect(reverse('sql_review_reviewed_list'))


#@login_required(identity=('operation', 'project_manager'))
@login_required()
def reject_to_dev(request):
    # 拒绝执行sql，将审核状态置为2，写入通知消息到消息系统
    record_id = request.POST.get('record_id', 0)
    print (record_id)
    if request.user.identity == 'project_manager':
        update_sql = "update t_sql_review_record set is_reviewed = 2 where id={0}".format(record_id)
    else:
        update_sql = "update t_sql_review_record set is_executed = 2 where id={0}".format(record_id)
    e_status = s.execute_and_return_status(update_sql)
    print (e_status)
    return HttpResponse(json.dumps({'status': 'success'}), content_type='application/json')
#    return redirect(reverse('sql_review_reviewed_list'))


# 开始提交审核sql
@login_required()
def step(request):
    db_list = []
    with  get_mysql_conn() as conn:
        with conn as cur:
            cur.execute("select id,dbname from t_db_basic_info")
            db_list = dictFetchall(cur)

    specification_type = SpecificationTypeForSql.objects.order_by('?')[0:3]
    content = []
    for idx, s_type in enumerate(specification_type):
        content.append(SpecificationContentForSql.objects.filter(type=s_type.id).order_by('?')[0:10])
    dict_content = {
        'content1': content[0],
        'content2': content[1],
        'content3': content[2]
    }
    # 查找出所有项目经理，以供开发选择
    project_manager = UserProfile.objects.filter(identity='project_manager')
    data = {
        'sub_module': '2_1',
        'instance_groups': db_list,
        'start_time': (datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M'),
        'dict_content': dict_content,
        'project_manager': project_manager
    }
    return render(request, 'sql_review/step.html', data)


@login_required()
def submit_step(request):
    sql = request.POST.get('sql', "")
    for_what = request.POST.get('for_what', "")
    conn_id = request.POST.get('instance', "")
    db_id = request.POST.get('instance_group',"")
    execute_time = request.POST.get('execute_time',"")
    user_name = request.user.name
    param = []
    if sql and for_what and db_id and conn_id and execute_time:
        param = [db_id,conn_id,for_what,user_name,execute_time,sql,1]
        sql_max_id = "select max(id) from t_sql_review_record"
        insert_sql = """insert into t_sql_review_record(db_id,conn_id,for_what,user_name,execute_time,submit_sql,is_submitted)
            VALUES (%s,%s,%s,%s,%s,%s,%s)"""
        with  get_mysql_conn() as conn:
            with conn as cur:
                cur.execute(insert_sql, param)
                cur.execute(sql_max_id)
                max_id = cur.fetchall()[0][0]

        data = {
             'result': 'success',
             'result_id': max_id
         }
        return HttpResponse(json.dumps(data), content_type='application/json')
    else:
        data = {
            'result': 'error'
        }
        return HttpResponse(json.dumps(data), content_type='application/json')


@login_required()
def instance_by_ajax_and_id(request):
    group_id = request.POST.get('group_id', '1')
   # instance = MysqlInstance.objects.filter(group=group_id)
    with  get_mysql_conn() as conn:
        with conn as cur:
            cur.execute("select * from t_db_conn_info where db_id = {0} and type = 'W'".format(group_id))
            instance = dictFetchall(cur)
    return HttpResponse(json.dumps(instance), content_type='application/json')


@login_required()
def submitted_list(request):
    # 取出账号权限下所有的审核请求
    select_sql = """select a.id,a.for_what,a.user_name,a.submit_time,a.execute_time,a.submit_sql,a.is_checked,
          a.is_submitted,a.is_reviewed,a.is_executed,b.dbname,c.env_name
          from t_sql_review_record a,t_db_basic_info b, t_db_conn_info c
          where  a.db_id=b.id and a.conn_id=c.id and a.is_submitted=1 and a.is_reviewed !=1 order by a.id desc limit 200"""
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    with  get_mysql_conn() as conn:
        with conn as cur:
            cur.execute(select_sql)
            record_list = dictFetchall(cur)

    p = Paginator(record_list, 10, request=request)
    try:
        record_list_in_pages = p.page(page)
    except EmptyPage:
        record_list_in_pages = p.page(1)
    data = {
        'record_list': record_list_in_pages,
        'sub_module': '2_2'
    }
    return render(request, 'sql_review/record_list.html', data)

@login_required()
def modify_submitted_sql(request):
    #  record = SqlReviewRecord.objects.get(id=request.POST.get('record_id'))
    record_id = request.POST.get('record_id')
    new_sql = request.POST.get('sql', 'select 1')
    print(new_sql)
    user_name = request.user.username
    update_sql = """update t_sql_review_record set submit_sql = "{0}", user_name = "{1}"
        where id = {2}""".format(new_sql, user_name, record_id)
    e_status = s.execute_and_return_status(update_sql)
    print(e_status)
    # if e_status

    data = {
        'new_id': record_id,
        'status': 'success'
    }
    return HttpResponse(json.dumps(data), content_type='application/json')


#@login_required(identity=('operation', ))
@login_required()
def sql_review_before_execute(request, record_id):
    s = SQL()
    submit_sql,dbname,instance_ip,instance_port = s.get_db_info_from_record_id(record_id)
    exec_sql = "/*--user=%s;--password=%s; --enable-check;--host=%s;--disable-remote-backup;--port=%s;*/\
                        inception_magic_start;\
                        use %s;" % ('root', 'test123',
                                    instance_ip, int(instance_port), dbname)

    if str(submit_sql).strip()[-1:] != ";":
        exec_sql = exec_sql + str(submit_sql).strip() + ";"
    else:
        exec_sql = exec_sql + str(submit_sql).strip()
    exec_sql = exec_sql + "inception_magic_commit;"

    try:
        conn = pymysql.connect(host=INCEPTION_IP, user='', passwd='', db='', port=INCEPTION_PORT, charset='utf8')
        cur = conn.cursor()
        ret = cur.execute(exec_sql)
        num_fields = len(cur.description)
        field_names = [i[0] for i in cur.description]
        result = cur.fetchall()
        cur.close()
        conn.close()
        # 第一行为use database，丢弃
        if len(result) > 1:
            result = result[1:]

        data = {
            'field_names': field_names,
            'result': result,
            'sub_module': '2_1',
            'record_id': record_id,
            'sql': submit_sql
        }
        return render(request, 'sql_review/review_before_execute_result.html', data)
    except pymysql.Error as e:
        return HttpResponse('Mysql Error {}: {}'.format(e.args[0], e.args[1]), status=500)


#@login_required(identity=('operation', ))
@login_required()
def sql_execute(request, record_id, ignore_flag):
    s = SQL()
    submit_sql,dbname,instance_ip,instance_port = s.get_db_info_from_record_id(record_id)

    if ignore_flag == 'ignore':
        exec_sql = "/*--user=%s;--password=%s; --enable-execute;--host=%s;--enable-remote-backup;--enable-ignore-warnings;--port=%s;*/\
                        inception_magic_start;\
                        use %s;" % ('root', 'test123',
                                    instance_ip, int(instance_port), dbname)
    else:
        exec_sql = "/*--user=%s;--password=%s; --enable-execute;--host=%s;--enable-remote-backup;--port=%s;*/\
                        inception_magic_start;\
                        use %s;" % ('root', 'test123',
                                    instance_ip, int(instance_port), dbname)

    if str(submit_sql).strip()[-1:] != ";":
        exec_sql = exec_sql + str(submit_sql).strip() + ";"
    else:
        exec_sql = exec_sql + str(submit_sql).strip()
    exec_sql = exec_sql + "inception_magic_commit;"

    try:
        conn = pymysql.connect(host=INCEPTION_IP, user='', passwd='', db='', port=INCEPTION_PORT, charset='utf8')
        cur = conn.cursor()
        ret = cur.execute(exec_sql)
        field_names = [i[0] for i in cur.description]
        result = cur.fetchall()
        cur.close()
        conn.close()
        # 判断结果中是否有执行成功的状态，如果有则将备份信息存入表中，等待给以后做回滚
        for res in result:
            if res[1] == 'EXECUTED' and (res[2] == 0 or res[2] == 1):
                sql_backup_instance = SqlBackupRecord()
                sql_backup_instance.review_record_id = record_id
                sql_backup_instance.backup_db_name = res[8]
                sql_backup_instance.sequence = res[7]
                sql_backup_instance.sql_sha1 = res[10]
                sql_backup_instance.save()
        # 判断结果中是否有error level 为 2 的，如果有，则不做操作，如果没有则将 sql_review_record 记录的 is_executed 设为1
        # 判断结果中是否有error level 为 1 的，如果有，并且忽略标记不为'ignore'，则不做操作，如果有，且忽略标记为'ignore'，则操作和上述一样
        flag = 'success'
        for res in result:
            if res[2] == 2 or (ignore_flag != 'ignore' and res[2] == 1):
                flag = 'failed'

        if flag == 'success':
            is_executed = 1
            s.execute_and_return_status("update t_sql_review_record set is_executed=1 where id = {0}".format(record_id))

        # 第一行为use database，丢弃
        if len(result) > 1:
            result = result[1:]

        data = {
            'field_names': field_names,
            'result': result,
            'sub_module': '2_4',
            'record_id': record_id,
            'sql': submit_sql,
            'flag': flag
        }
        return render(request, 'sql_review/execute_result.html', data)
    except pymysql.Error as e:
        return HttpResponse('Mysql Error {}: {}'.format(e.args[0], e.args[1]), status=500)


def sql_execute_ignore_warning(request, record_id):

    return 's'


#@login_required(request.user.identity=('operation', 'project_manager'))
@login_required
def reviewed_list(request):
    # 取出账号权限下所有的项目经理审核完成列表
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    select_sql = """select a.id,a.for_what,a.user_name,a.submit_time,a.execute_time,a.submit_sql,a.is_checked,
          a.is_submitted,a.is_reviewed,a.is_executed,b.dbname,c.env_name
          from t_sql_review_record a,t_db_basic_info b, t_db_conn_info c
          where  a.db_id=b.id and a.conn_id=c.id and a.is_reviewed in (1,2) order by a.id desc limit 200"""

    with  get_mysql_conn() as conn:
        with conn as cur:
            cur.execute(select_sql)
            record_list = dictFetchall(cur)

    p = Paginator(record_list, 10, request=request)
    try:
        record_list_in_pages = p.page(page)
    except EmptyPage:
        record_list_in_pages = p.page(1)
    data = {
        'record_list': record_list_in_pages,
        'sub_module': '2_3',
    }
    return render(request, 'sql_review/reviewed_list.html', data)


#@login_required(identity=('operation', ))
@login_required()
def finished_list(request):
    # 取出账号权限下所有的执行完成列表
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    with  get_mysql_conn() as conn:
        with conn as cur:
            select_sql = """select a.id,a.for_what,a.user_name,a.submit_time,a.execute_time,a.submit_sql,a.is_checked,
          a.is_submitted,a.is_reviewed,a.is_executed,b.dbname,c.env_name
          from t_sql_review_record a,t_db_basic_info b, t_db_conn_info c
          where  a.db_id=b.id and a.conn_id=c.id and a.is_reviewed=1 order by a.id desc limit 200"""
            cur.execute(select_sql)
            record_list = dictFetchall(cur)
    p = Paginator(record_list, 10, request=request)
    try:
        record_list_in_pages = p.page(page)
    except EmptyPage:
        record_list_in_pages = p.page(1)
    data = {
        'record_list': record_list_in_pages,
        'sub_module': '2_4',
    }
    return render(request, 'sql_review/finished_list.html', data)


#@login_required(identity=('operation', ))
@login_required()
def rollback(request, record_id):
    rollback_list = SqlBackupRecord.objects.filter(review_record_id=record_id)
    for idx, obj in enumerate(rollback_list):
        backup_db = obj.backup_db_name
        sequence = obj.sequence
        sql = 'select * from $_$Inception_backup_information$_$ where `opid_time` = {}'.format(sequence)
        my_logger(level='info', message='执行SQL：' + sql, username=request.user.name, path=request.path)
        result = get_sql_result(BACKUP_HOST_IP, BACKUP_HOST_PORT, BACKUP_USER, BACKUP_PASSWORD, backup_db, sql)
        rollback_list[idx].sql = result[0][5]
        rollback_list[idx].db_host = result[0][6]
        rollback_list[idx].db_name = result[0][7]
        rollback_list[idx].db_table_name = result[0][8]
        rollback_sql = 'select  `rollback_statement` from {} where `opid_time` = {} limit 20'.format(result[0][8], sequence)
        my_logger(level='info', message='执行获取回滚SQL：' + rollback_sql, username=request.user.name, path=request.path)
        rollback_result = get_sql_result(BACKUP_HOST_IP, BACKUP_HOST_PORT, BACKUP_USER, BACKUP_PASSWORD, backup_db,
                                         rollback_sql)
        rollback_statement = str()
        for statement in rollback_result:
            rollback_statement += '{}\n'.format(statement[0])
        rollback_list[idx].rollback_statement = rollback_statement
    data = {
        'rollback_list': rollback_list,
        'sub_module': '2_4'
    }
    return render(request, 'sql_review/rollback.html', data)


def get_sql_result(host_ip, host_port, user, password, database, sql):
    try:
        conn = pymysql.connect(host=host_ip, user=user, passwd=password, db=database, port=host_port, charset='utf8')
        cur = conn.cursor()
        ret = cur.execute(sql)
        result = cur.fetchall()
        cur.close()
        conn.close()
        return result
    except pymysql.Error as e:
        return 'error'


def dml_sql_in_transaction(host_ip, host_port, user, password, database, sql_list):
    conn = pymysql.connect(host=host_ip, user=user, passwd=password, db=database, port=host_port, charset='utf8')
    cur = conn.cursor()
    try:
        for sql in sql_list:
            cur.execute(sql)
        cur.close()
        conn.commit()
        conn.close()
        return 'ok'
    except pymysql.Error as e:
        cur.close()
        conn.rollback()
        conn.close()
        return 'error'


#@login_required(identity=('operation', ))
@login_required()
def ajax_rollback_by_sequence(request):
    sequence = request.POST.get('sequence')
    if sequence:
        sequence_list = sorted(sequence.strip(',').split(','), reverse=True)
    # 获取所有 sequence 的数据库名，进而获取回滚语句
        record = SqlBackupRecord.objects.get(sequence=sequence_list[0])
        backup_database_name = record.backup_db_name
        content = backup_database_name.split('_')
        host_ip = '{0}.{1}.{2}.{3}'.format(content[0], content[1], content[2], content[3])
        host_port = int(content[4])
        mysql_instance = MysqlInstance.objects.get(ip=host_ip, port=host_port)
        user = mysql_instance.login_instance_account
        password = mysql_instance.login_instance_password
        sql_list = list()
        for sequence in sequence_list:
            record = SqlBackupRecord.objects.get(sequence=sequence)
            backup_database_name = record.backup_db_name

            sql = 'select tablename from $_$Inception_backup_information$_$ where opid_time = {} limit 1'.format(sequence)
            result = get_sql_result(BACKUP_HOST_IP, BACKUP_HOST_PORT, BACKUP_USER, BACKUP_PASSWORD,
                                    backup_database_name, sql)
            table_name = result[0][0]
            sql = 'select rollback_statement from {} where opid_time = {}'.format(table_name, sequence)
            sql_result = get_sql_result(BACKUP_HOST_IP, BACKUP_HOST_PORT, BACKUP_USER, BACKUP_PASSWORD,
                                        backup_database_name, sql)
            if sql_result:
                for single_sql in sql_result:
                    sql_list.append(single_sql[0])
        if sql_list:
            result = dml_sql_in_transaction(host_ip, host_port, user, password, '', sql_list)
        else:
            result = 'empty'
        if result == 'ok':
            data = {
                'status': 'success',
                'message': '成功'
            }
        elif result == 'empty':
            data = {
                'status': 'empty',
                'message': '没有需要回滚的语句'
            }
        else:
            data = {
                'status': 'error',
                'message': '回滚语句执行失败'
            }
    else:
        data = {
            'status': 'empty',
            'message': '没有需要回滚的语句'
        }
    return HttpResponse(json.dumps(data), content_type='application/json')


#@login_required(identity=('operation', ))
@login_required()
def osc_process(request, osc_id):
    sql = 'inception get osc_percent "{}"'.format(osc_id)
    try:
        conn = pymysql.connect(host=INCEPTION_IP, user='', passwd='', db='', port=INCEPTION_PORT, charset='utf8')
        cur = conn.cursor()
        ret = cur.execute(sql)
        result = cur.fetchall()
        cur.close()
        conn.close()
        if result:
            result = tuple_to_dict(result[0], ('schema_name', 'table_name', 'sqlsha1', 'percent',
                                               'remain_time', 'info'))
            data = {
                'result': result,
                'osc_id': osc_id,
                'sub_module': '2_4'
            }
        else:
            result = {
                'schema_name': 'Empty',
                'table_name': 'Empty',
                'sqlsha1': osc_id,
                'percent': 'Empty',
                'remain_time': 'Empty',
                'info': 'Empty!!!',
            }
            data = {
                'result': result,
                'osc_id': osc_id,
                'sub_module': '2_4',
            }
        print(result)
        # return render(request, 'sql_review/review_before_execute_result.html', data)
        return render(request, 'sql_review/osc_process.html', data)
    except pymysql.Error as e:
        return HttpResponse('Mysql Error {}: {}'.format(e.args[0], e.args[1]), status=500)


def tuple_to_dict(tuple_arg, name):
    dict_arg = {}
    for index, arg in enumerate(name):
        dict_arg[arg] = tuple_arg[index]
    return dict_arg


#@login_required(identity=('operation', ))
@login_required()
def ajax_osc_percent(request, osc_id):
    sql = 'inception get osc_percent "{}"'.format(osc_id)
    try:
        conn = pymysql.connect(host=INCEPTION_IP, user='', passwd='', db='', port=INCEPTION_PORT, charset='utf8')
        cur = conn.cursor()
        ret = cur.execute(sql)
        result = cur.fetchall()
        cur.close()
        conn.close()
        if result:
            result = tuple_to_dict(result[0], ('schema_name', 'table_name', 'sqlsha1', 'percent',
                                               'remain_time', 'info'))
            result['info'] = result['info'].replace('\n', '<br ''/>')
            data = {
                'status': 'success',
                'process': result['percent'],
                'info': result
            }
        else:
            result = {
                'remain_time': '00:00',
                'info': 'Empty!!!'
            }
            data = {
                'status': 'empty',
                'process': 100,
                'info': result

            }
        return HttpResponse(json.dumps(data), content_type='application/json')
    except pymysql.Error as e:
        print(HttpResponse('Mysql Error {}: {}'.format(e.args[0], e.args[1]), status=500))
        return HttpResponse(json.dumps({'status': 'failed'}), content_type='application/json')


@login_required()
def more_specification(request):
    specification_type = SpecificationTypeForSql.objects.all()
    all_list = []
    for idx, types in enumerate(specification_type):
        tmp_dict = dict()
        tmp_dict['types'] = types
        tmp_dict['content'] = types.specificationcontentforsql_set.all()
        all_list.append(tmp_dict)
    data = {
        'all_list': all_list,
        'sub_module': '2_5'
    }
    return render(request, 'sql_review/specification.html', data)


def message_to_pm(request):
    # 给对应项目经理发邮件，以及站内信通知其审核sql
    record_id = request.POST.get('record_id', 0)
    with get_mysql_conn() as conn:
        with conn as cur:
            cur.execute("select for_what from t_sql_review_record where id ={0}".format(record_id))
            for_what = cur.fetchall()[0][0]

    # record = SqlReviewRecord.objects.get(id=request.POST.get('record_id'))
    from_user = UserProfile.objects.get(id=request.user.id)
#    to_user = UserProfile.objects.get(name=record.pm_name)
    message = MessageRecord()
    message.info = '{0} 希望您能尽快审核该sql（{1}）'.format(request.user.name, for_what)
    message.click_path = '/sql_review/submitted_list'
    message.save()
    message.send_from.add(from_user)
  #  message.send_to.add(to_user)
    message.save()
    return HttpResponse(json.dumps({'status': 'success'}), content_type='application/json')


def message_to_oper(request):
    # 发送给所有的运维
    # record = SqlReviewRecord.objects.get(id=request.POST.get('record_id'))
    record_id = request.POST.get('record_id', 0)
    with get_mysql_conn() as conn:
        with conn as cur:
            cur.execute("select for_what from t_sql_review_record where id ={0}".format(record_id))
            for_what = cur.fetchall()[0][0]
    from_user = UserProfile.objects.get(id=request.user.id)
    to_users = UserProfile.objects.filter(identity='operation')
    for user in to_users:
        message = MessageRecord()
        message.info = '{} 希望您能尽快执行该sql（{}）'.format(request.user.name, for_what)
        message.click_path = '/sql_review/reviewed_list'
        message.save()
        message.send_from.add(from_user)
        message.send_to.add(user)
        message.save()
    return HttpResponse(json.dumps({'status': 'success'}), content_type='application/json')
