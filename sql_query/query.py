# -*- coding: utf-8 -*-

from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from contextlib import contextmanager
import json
import re
import time
import pymysql
from .models import QueryLog
from mysql_platform.mysql_function import SQL
from users.endecrypt import endeCrypt
from .extend_json_encoder import ExtendJSONEncoder

s = SQL()
# 或者读写用户
en = endeCrypt()
review_user, review_password = en.get_ro_user_pass()


def dictFetchall(cursor):
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]



@contextmanager
def get_mysql_conn(Host, Port):
    conn_args = dict(host=Host, 
                    port=Port, 
                    db='', 
                    user=review_user, 
                    password=review_password, 
                    charset="utf8mb4")
    conn = pymysql.connect(**conn_args)
    try:
        yield conn
    finally:
        conn.close()



# SQL在线查询
@csrf_exempt
@login_required()
def sqlquery(request):
    data = {}
    sql = "select dbid, dbname from sqltools_user_db"
    dbs = s.execute_and_return_dict(sql)
    db_list = [db for db in dbs]

    data['listAllClusterName'] = ['暂时无用选项，不用点']
    data['db_list'] = db_list
    # context = {'listAllClusterName': data}


    return render(request, 'sql_query/sqlquery.html', data)


@csrf_exempt
@login_required()
def getTableNameList(request):
    clusterName = request.POST.get('cluster_name')
    db_name = request.POST.get('db_name', 'xxxxxx')
    is_master = request.POST.get('is_master')
    result = {'status': 0, 'msg': 'ok', 'data': []}
    sql_table = "select table_name  from information_schema.tables where table_schema='{0}'".format(db_name)
    slave_info = s.execute_and_fetchall("select host,port from sqltools_db_conninfo where type='R' and dbname='{0}'".format(db_name))
    if slave_info:
        slave_host = slave_info[0][0]
        slave_port = slave_info[0][1]
        ss = SQL(slave_host, slave_port)
        with get_mysql_conn(slave_host, slave_port) as conn:
            with conn as cur:
                cur.execute(sql_table)
                tables = cur.fetchall()
        listTb = [row[0] for row in tables]
        result['data'] = listTb
    else:
        result['data'] = ['无法找到对应表']

    return HttpResponse(json.dumps(result), content_type='application/json')


# 获取SQL查询结果
@csrf_exempt
@login_required()
def query(request):
    cluster_name = request.POST.get('cluster_name')
    sqlContent = request.POST.get('sql_content')
    dbName = request.POST.get('db_name')
    limit_num = request.POST.get('limit_num')

    finalResult = {'status': 0, 'msg': 'ok', 'data': {}}

    # 服务器端参数验证
    if sqlContent is None or dbName is None or cluster_name is None or limit_num is None:
        finalResult['status'] = 1
        finalResult['msg'] = '页面提交参数可能为空'
        return HttpResponse(json.dumps(finalResult), content_type='application/json')

    sqlContent = sqlContent.strip()
    if sqlContent[-1] != ";":
        finalResult['status'] = 1
        finalResult['msg'] = 'SQL语句结尾没有以;结尾，请重新修改并提交！'
        return HttpResponse(json.dumps(finalResult), content_type='application/json')

    # 获取用户信息
    loginUser = request.user.name
    # loginUserOb = users.objects.get(username=loginUser)

    # 过滤注释语句和非查询的语句
    sqlContent = ''.join(
        map(lambda x: re.compile(r'(^--.*|^/\*.*\*/;[\f\n\r\t\v\s]*$)').sub('', x, count=1),
            sqlContent.splitlines(1))).strip()
    # 去除空行
    sqlContent = re.sub('[\r\n\f]{2,}', '\n', sqlContent)

    sql_list = sqlContent.strip().split('\n')
    for sql in sql_list:
        if re.match(r"^select|^show.*create.*table|^explain", sql.lower()):
            break
        else:
            finalResult['status'] = 1
            finalResult['msg'] = '仅支持^select|^show.*create.*table|^explain语法，请联系管理员！'
            return HttpResponse(json.dumps(finalResult), content_type='application/json')

    # 取出该集群的连接方式,查询只读账号,按照分号截取第一条有效sql执行
    # slave_info = slave_config.objects.get(cluster_name=cluster_name)
    slave_info = s.execute_and_fetchall("select host,port from sqltools_db_conninfo where type='R' and dbname='{0}'".format(dbName))
    if not slave_info:
        msgg = "没有找到对应的db链接信息"
        return HttpResponse(json.dumps({"status":1, "msg": msgg}), content_type='application/json')
    slave_host = slave_info[0][0]
    slave_port = slave_info[0][1]
    sqlContent = sqlContent.strip().split(';')[0]

    # # 查询权限校验，以及limit_num获取
    # priv_check_info = query_priv_check(loginUserOb, cluster_name, dbName, sqlContent, limit_num)

    # if priv_check_info['status'] == 0:
    #     limit_num = priv_check_info['data']
    # else:
    #     return HttpResponse(json.dumps(priv_check_info), content_type='application/json')

    if re.match(r"^explain", sqlContent.lower()):
        limit_num = 0

    # 对查询sql增加limit限制
    if re.match(r"^select", sqlContent.lower()):
        if re.search(r"limit[\f\n\r\t\v\s]+(\d+)$", sqlContent.lower()) is None:
            if re.search(r"limit[\f\n\r\t\v\s]+\d+[\f\n\r\t\v\s]*,[\f\n\r\t\v\s]*(\d+)$", sqlContent.lower()) is None:
                sqlContent = sqlContent + ' limit ' + str(limit_num)

    sqlContent = sqlContent + ';'

    # 执行查询语句,统计执行时间
    t_start = time.time()
    sql_result = mysql_query(slave_host, slave_port, str(dbName), sqlContent, limit_num)
    t_end = time.time()
    cost_time = "%5s" % "{:.4f}".format(t_end - t_start)

    sql_result['cost_time'] = cost_time

    # 数据脱敏，同样需要检查配置，是否开启脱敏，语法树解析是否允许出错继续执行
    t_start = time.time()
    # if settings.DATA_MASKING_ON_OFF:
    #     # 仅对查询语句进行脱敏
    #     if re.match(r"^select", sqlContent.lower()):
    #         try:
    #             masking_result = datamasking.data_masking(cluster_name, dbName, sqlContent, sql_result)
    #         except Exception:
    #             if settings.CHECK_QUERY_ON_OFF:
    #                 finalResult['status'] = 1
    #                 finalResult['msg'] = '脱敏数据报错,请联系管理员'
    #                 return HttpResponse(json.dumps(finalResult), content_type='application/json')
    #         else:
    #             if masking_result['status'] != 0:
    #                 if settings.CHECK_QUERY_ON_OFF:
    #                     return HttpResponse(json.dumps(masking_result), content_type='application/json')

    # t_end = time.time()
    # masking_cost_time = "%5s" % "{:.4f}".format(t_end - t_start)

    # sql_result['masking_cost_time'] = masking_cost_time

    finalResult['data'] = sql_result

    # 成功的查询语句记录存入数据库
    if sql_result.get('Error'):
        pass
    else:
        query_log = QueryLog()
        query_log.username = loginUser
        query_log.db_name = dbName
        query_log.cluster_name = "暂时无用字段"
        query_log.sqllog = sqlContent
        if int(limit_num) == 0:
            limit_num = int(sql_result['effect_row'])
        else:
            limit_num = min(int(limit_num), int(sql_result['effect_row']))
        query_log.effect_row = limit_num
        query_log.cost_time = cost_time
        # sql_insert = """insert into query_log(cluster_name,db_name,sqllog,effect_row,cost_time,username) 
        #     values ('{0}','{1}','{2}','{3}','{4}','{5}')"""
        # sql_format = sql_insert.format(cluster_name, db_name, sqllog, effect_row, cost_time, username)
        # status = s.execute_and_return_status(sql_format)
        # 防止查询超时
        try:
            query_log.save()
        except:
            connection.close()
            query_log.save()

    # 返回查询结果
    return HttpResponse(json.dumps(finalResult, cls=ExtendJSONEncoder, bigint_as_string=True),
                        content_type='application/json')



def mysql_query(Host, Port, dbName, sql, limit_num=0):
        result = {}
        conn = None
        cursor = None
        try:
            conn = pymysql.connect(host=Host, port=Port, user=review_user, passwd=review_password, db=dbName,
                                   charset='utf8mb4')
            cursor = conn.cursor()
            effect_row = cursor.execute(sql)
            if int(limit_num) > 0:
                rows = cursor.fetchmany(size=int(limit_num))
            else:
                rows = cursor.fetchall()
            fields = cursor.description

            column_list = []
            if fields:
                for i in fields:
                    column_list.append(i[0])
            result = {}
            result['column_list'] = column_list
            result['rows'] = rows
            result['effect_row'] = effect_row

        except pymysql.Warning as w:
            print(str(w))
            result['Warning'] = str(w)
        except pymysql.Error as e:
            print(str(e))
            result['Error'] = str(e)
        except UnicodeDecodeError as e:
            print(str(e))
            result['Error'] = "返回字段有特殊字符，请联系DBA手动查询"
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                try:
                    conn.rollback()
                    conn.close()
                except:
                    conn.close()
        return result


@csrf_exempt
@login_required()
def querylog(request):
    # 获取用户信息
    loginUser = request.user.name
    # print(request.session.get("username"))
    # loginUserOb = users.objects.get(username=loginUser)

    # limit = int(request.POST.get('limit'))
    limit = 10
    offset = int(request.POST.get('offset'))
    limit = offset + limit

    # 获取搜索参数
    search = request.POST.get('search')
    if search is None:
        search = ''

    # 查询个人记录，超管查看所有数据
     # if loginUserOb.is_superuser == 1 or loginUserOb.role == 'DBA':
    sql_log_count = QueryLog.objects.all().filter(Q(sqllog__contains=search) | Q(username__contains=search)).count()
    sql_log_list = QueryLog.objects.all().filter(
        Q(sqllog__contains=search) | Q(username__contains=search)).order_by(
        '-id')[offset:limit]
    # else:
    #     sql_log_count = QueryLog.objects.filter(username=loginUser).filter(
    #         Q(sqllog__contains=search) | Q(username__contains=search)).count()
    #     sql_log_list = QueryLog.objects.filter(username=loginUser).filter(
    #         Q(sqllog__contains=search) | Q(username__contains=search)).order_by('-id')[offset:limit]
    # sql_log_count = ss[0][0]
    # sql_log_list = s.execute_and_fetchall("select * from query_log limit 10")
    # print(sql_log_list)

    # QuerySet 序列化
    sql_log_list = serializers.serialize("json", sql_log_list)
    sql_log_list = json.loads(sql_log_list)
    sql_log = [log_info['fields'] for log_info in sql_log_list]

    result = {"total": sql_log_count, "rows": sql_log}
    # 返回查询结果
    return HttpResponse(json.dumps(result), content_type='application/json')


# 获取集群里面的数据库集合
@csrf_exempt
def getdbNameList(request):
    clusterName = request.POST.get('cluster_name', "abcxxx")
    is_master = request.POST.get('is_master')
    result = {'status': 0, 'msg': 'ok', 'data': []}
    sql = "select dbname from sqltools_user_db"
    db_names = s.execute_and_fetchall(sql)
    db_list = [dbname for dbname in db_names]
    result = {'status': 0, 'msg': 'ok', 'data': db_list}
    print(result)
    return HttpResponse(json.dumps(result), content_type='application/json')
    # if is_master:
    #     try:
    #         master_info = master_config.objects.get(cluster_name=clusterName)
    #     except Exception:
    #         result['status'] = 1
    #         result['msg'] = '找不到对应的主库配置信息，请配置'
    #         return HttpResponse(json.dumps(result), content_type='application/json')

    #     try:
    #         # 取出该集群主库的连接方式，为了后面连进去获取所有databases
    #         listDb = dao.getAlldbByCluster(master_info.master_host, master_info.master_port, master_info.master_user,
    #                                        prpCryptor.decrypt(master_info.master_password))
    #         # 要把result转成JSON存进数据库里，方便SQL单子详细信息展示
    #         result['data'] = listDb
    #     except Exception as msg:
    #         result['status'] = 1
    #         result['msg'] = str(msg)

    # else:
    #     try:
    #         slave_info = slave_config.objects.get(cluster_name=clusterName)
    #     except Exception:
    #         result['status'] = 1
    #         result['msg'] = '找不到对应的从库配置信息，请配置'
    #         return HttpResponse(json.dumps(result), content_type='application/json')

    #     try:
    #         # 取出该集群的连接方式，为了后面连进去获取所有databases
    #         listDb = dao.getAlldbByCluster(slave_info.slave_host, slave_info.slave_port, slave_info.slave_user,
    #                                        prpCryptor.decrypt(slave_info.slave_password))
    #         # 要把result转成JSON存进数据库里，方便SQL单子详细信息展示
    #         result['data'] = listDb
    #     except Exception as msg:
    #         result['status'] = 1
    #         result['msg'] = str(msg)

    # return HttpResponse(json.dumps(result), content_type='application/json')



@csrf_exempt
def sqlquery_and_return(request):
    db_name = request.POST.get('db_name', "")
    table_name = request.POST.get('tb_name', "")
    sql = request.POST.get('sql_content', "")
    limit_num = request.POST.get('limit_num', 10)
    status = 0
    data = "sasadasdsad"
    context={
        'form':form,
         'title':'在线查询',
         'errorSqlList':'exec_errors',
         'sqlResultDict':'sqlResultDict',
         'field_desc':'field_desc',
         'width':str(100/len(field_desc)) +'%',
         'dblist':'dblist',
         'databaseId': 'databaseId'
        }
    return render(request, 'sql_query/sqlquery.html',context) 
