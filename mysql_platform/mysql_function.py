# -*- coding: utf-8 -*-
from contextlib import contextmanager
import chardet
import pymysql
from users.endecrypt import endeCrypt

ende = endeCrypt()
# default mysql host and user
host = "127.0.0.1"
port = 3306
user, password = ende.get_mysqltool_user_pass()
schema = "platform"

class SQL():
    def __init__(self, host=host, port=port, schema=schema, user=user, password=password, charset="utf8mb4"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.schema= schema
        self.charset = charset

    @contextmanager
    def get_mysql_conn(self):
        conn = pymysql.connect(
            host = self.host,
            port = self.port,
            user = self.user,
            passwd = self.password,
            db = self.schema,
            charset = self.charset
        )
        try:
            yield conn
        finally:
            conn.close()

    def dictfetchall(self, cursor):
        desc = cursor.description
        return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
        ]


    def get_db_info_from_record_id(self, record_id):
        s_sql = """select a.submit_sql,b.dbname,c.host,c.port from
            t_sql_review_record a,t_db_basic_info b, t_db_conn_info c where
        a.db_id=b.id and a.conn_id=c.id  and a.id = {0}"""
        try:
            with self.get_mysql_conn() as conn:
                with conn as cur:
                    cur.execute(s_sql.format(record_id))
            rows = cur.fetchall()
            submit_sql = rows[0][0]
            dbname = rows[0][1]
            instance_ip = rows[0][2]
            instance_port = rows[0][3]
            return submit_sql, dbname, instance_ip, instance_port
        except:
            return "", "", "" ,""


    def execute_and_return_dict(self, sql):
        try:
            with self.get_mysql_conn() as conn:
                with conn as cur:
                    cur.execute(sql)
            row_dict = self.dictfetchall(cur)
            return row_dict
        except:
            return dict({})

    def execute_and_return_value(self, sql):
        try:
            with self.get_mysql_conn() as conn:
                with conn as cur:
                    cur.execute(sql)
            row = cur.fetchall()
            return row[0][0]
        except:
            return ""

    def execute_and_fetchall(self, sql):
        try:
            with self.get_mysql_conn() as conn:
                with conn as cur:
                    cur.execute(sql)
            rows = cur.fetchall()
            return rows
        except:
            return dict({})
    def execute_and_return_cursor(self, sql):
        try:
            with self.get_mysql_conn() as conn:
                with conn as cur:
                    cur.execute(sql)
            return cur
        except:
            return ""


    def execute_and_return_status(self, sql):
        try:
            with self.get_mysql_conn() as conn:
                with conn as cur:
                    cur.execute(sql)
            return 'ok'
        except:
            return 'nok'

