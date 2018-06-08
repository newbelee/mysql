#!/usr/bin/python
#-*-coding: utf-8-*-
from contextlib import contextmanager
import pymysql
from mysql_platform.mysql_function import SQL
from users.endecrypt import endeCrypt

en = endeCrypt()
review_user, review_password = en.get_ro_user_pass()
# Inception host
inc_host = "127.0.0.1"
inc_port = 6669
inc_user = ""
inc_password = ""
inc_schema = ""


class Inception:
    """
    manual_audit_execution 函数主要是给update提示行数超过10000行再次判断的，
    后面函数主要是给手工审核通过不走inception使用，直接连后端db更新

    """
    def __init__(self, default_user=review_user, default_password=review_password):
        self.db_user = default_user
        self.db_pass = default_password

    @contextmanager
    def get_inception_conn(self):
        conn = pymysql.connect(
            host=inc_host,
           user=inc_user,
           passwd=inc_password,
           port=inc_port,
           db=inc_schema,
           charset="utf8mb4")
        try:
            yield conn
        finally:
            conn.close()


    def dictFetchall(self, cursor):
        desc = cursor.description
        return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
            ]


    def get_inception_sql(self, opt, exec_sql, db_host, db_port, db_name, db_user, db_password):
        if not (db_user or db_password):
            db_user = self.db_user
            db_password = self.db_pass
        sql = """/*--user={0};--password={1};--host={2};{3};--port={4};*/
                                inception_magic_start;
                                use {5};
                                {6};
                                inception_magic_commit;""".format(db_user, db_password, db_host, opt, db_port,
                                                                  db_name, exec_sql)
        return sql


    def get_query_print_sql(self, sql, db_host=None, db_port=None, db_name=None, db_user=None, db_password=None):
        if str(sql).strip()[-1:] != ";":
            sub_sql = str(sql).strip() + ";"
        else:
            sub_sql = str(sql).strip()
        opt = "--enable-query-print"
        exec_sql = self.get_inception_sql(opt, sub_sql, db_host, db_port, db_name, db_user, db_password)
        return exec_sql

    def get_enable_check_sql(self, sql, db_host=None, db_port=None, db_name=None, db_user=None, db_password=None):
        if str(sql).strip()[-1:] != ";":
            sub_sql = str(sql).strip() + ";"
        else:
            sub_sql = str(sql).strip()
        opt = "--enable-check"
        exec_sql = self.get_inception_sql(opt, sub_sql, db_host, db_port, db_name, db_user, db_password)
        return exec_sql

    def get_enable_execute_sql(self, sql, db_host=None, db_port=None, db_name=None, db_user=None, db_password=None):
        if str(sql).strip()[-1:] != ";":
            sub_sql = str(sql).strip() + ";"
        else:
            sub_sql = str(sql).strip()
        opt = "--enable-execute"
        exec_sql = self.get_inception_sql(opt, sub_sql, db_host, db_port, db_name, db_user, db_password)
        return exec_sql

    def get_ignore_warnings_sql(self, sql, db_host=None, db_port=None, db_name=None, db_user=None, db_password=None):
        if str(sql).strip()[-1:] != ";":
            sub_sql = str(sql).strip() + ";"
        else:
            sub_sql = str(sql).strip()
        opt = "--enable-execute;--enable-ignore-warnings"
        exec_sql = self.get_inception_sql(opt, sub_sql, db_host, db_port, db_name, db_user, db_password)
        return exec_sql

    def execute_on_inception(self, sql):
        try:
            with self.get_inception_conn() as cur:
                ret = cur.execute(sql)
                result = self.dictFetchall(cur)
                return 0, result
        except:
            return -1, dict({})

    def get_rows_from_real(self, sql):
        result = SQL.execute_and_fetchall(sql)
        if result:
            return result[0][0]
        else:
            return ""


    def get_select_sql(self, exec_sql):
        select_count = "select count(*) from "
        where_param = ""
        try:
            if exec_sql.strip().lower().startswith("delete"):
                where_param = lower().split("from" ,1)[1].strip()
            if exec_sql.strip().lower().startswith("update"):
                tables, params = exec_sql.lower().split("update", 1)[1].split("set", 1)
                where_param = tables + " where " + params.lower().split("where", 1)[1]
            else:
                return ""
            sql = select_count + where_param
            return sql
        except:
            return ""


    def get_manual_audit_result(self, sql):
        select_sql = self.get_select_sql(sql)
        if select_sql:
            rows = self.get_rows_from_real(select_sql)
            return rows
        return ""

Inception = Inception()