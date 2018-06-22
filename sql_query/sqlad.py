
from django.shortcuts import render
from mysql_platform.mysql_function import SQL
from users.endecrypt import endeCrypt
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http.response import HttpResponse, HttpResponseRedirect
import json

s = SQL()
# 获取读用户
en = endeCrypt()
review_user, review_password = en.get_ro_user_pass()

# SQL优化工具
def sqladvisor(request):
    # 获取所有集群主库名称
    # masters = master_config.objects.all().order_by('cluster_name')
    # if len(masters) == 0:
    #     return HttpResponseRedirect('/admin/sql/master_config/add/')
    # cluster_name_list = [master.cluster_name for master in masters]
    data = {}
    sql = "select dbid, dbname from sqltools_user_db"
    dbs = s.execute_and_return_dict(sql)
    db_list = [db for db in dbs]

    data['listAllClusterName'] = ['暂时无用选项，不用点']
    data['db_list'] = db_list

    # context = {'currentMenu': 'sqladvisor', 'listAllClusterName': ['aaa','bbb']}
    return render(request, 'sql_query/sqladvisor.html', data)


# 获取SQLAdvisor的优化结果
@csrf_exempt
def sqladvisorcheck(request):
    if request.is_ajax():
        sqlContent = request.POST.get('sql_content')
        clusterName = request.POST.get('cluster_name')
        dbName = request.POST.get('db_name')
        verbose = request.POST.get('verbose')
    else:
        sqlContent = request.POST['sql_content']
        clusterName = request.POST['cluster_name']
        dbName = request.POST.POST['db_name']
        verbose = request.POST.POST['verbose']
    finalResult = {'status': 0, 'msg': 'ok', 'data': []}

    # 服务器端参数验证
    if sqlContent is None or clusterName is None:
        finalResult['status'] = 1
        finalResult['msg'] = '页面提交参数可能为空'
        return HttpResponse(json.dumps(finalResult), content_type='application/json')

    sqlContent = sqlContent.rstrip()
    if sqlContent[-1] != ";":
        finalResult['status'] = 1
        finalResult['msg'] = 'SQL语句结尾没有以;结尾，请重新修改并提交！'
        return HttpResponse(json.dumps(finalResult), content_type='application/json')

    if verbose is None or verbose == '':
        verbose = 1

    # 取出主库的连接信息
    # cluster_info = master_config.objects.get(cluster_name=clusterName)
    slave_info = s.execute_and_fetchall("select host,port from sqltools_db_conninfo where type='R' and dbname='{0}'".format(dbName))
    if slave_info:
        slave_host = slave_info[0][0]
        slave_port = slave_info[0][1]

    # 提交给sqladvisor获取审核结果
    sqladvisor_path = getattr(settings, 'SQLADVISOR')
    sqlContent = sqlContent.rstrip().replace('"', '\\"').replace('`', '\`').replace('\n', ' ')
    try:
        p = subprocess.Popen(sqladvisor_path + ' -h "%s" -P "%s" -u "%s" -p "%s\" -d "%s" -v %s -q "%s"' % (
            slave_host, slave_port, review_user, review_password, str(dbName), verbose, sqlContent),
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
        stdout, stderr = p.communicate()
        finalResult['data'] = stdout
    except Exception:
        finalResult['data'] = 'sqladvisor运行报错，请联系管理员'
    return HttpResponse(json.dumps(finalResult), content_type='application/json')
