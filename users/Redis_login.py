#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
host = "192.168.175.130"
port = 7001

class Redis:
    def __init__(self, host=host, port=port):
        self.host = host
        self.port = port

    def get_redis_conn(self):
        try:
            pool = redis.ConnectionPool(host=self.host, port=self.port)
            conn = redis.Redis(connection_pool=pool)
            conn.ping()
        # except redis.ConnectionError, e:
        except:
            return None
        return conn

    def get_value(self, key):
        conn = self.get_redis_conn()
        if conn:
            result = conn.get(key)
            return result
        else:
            return ""


    def set_value(self, key, value):
        conn = self.get_redis_conn()
        if conn:
            conn.set(key, value)
