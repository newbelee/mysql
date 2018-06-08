#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from ldap3 import ALL, Server, Connection


ldap_server = "10.10.46.71"#ldap服务器地址
baseDN = "dc=openldap,dc=yonghuivip,dc=com"#根目录


class LDAP:
    def __init__(self, login_user=None, login_password=None):
        self.ldapserer = ldap_server
        self.user = login_user
        self.password = login_password

    def get_dn_info(self, username):
        try:
            server = Server(self.ldapserer, get_info=ALL)
            with Connection(server, user=self.user, password=self.password) as conn:
                search_result = conn.search(
                    search_base="{0}".format(baseDN),
                    search_filter='(cn={0})'.format(username),
                    attributes=["sn"],
                    paged_size=5
                )
            if not search_result:
                return -1, dict({})
            entry = conn.entries[0].entry_to_json()
            entry_dict = json.loads(entry)
            dn = entry_dict["dn"]
            return 0, dn
        except:
            return -1, dict({})

    def auth_login(self, username, user_pass):
        try:
            server = Server(self.ldapserer)
            res, DN = self.get_dn_info(username)
            if res == -1:
                return False
            with Connection(server, DN, user_pass) as conn:
                ret = conn.bind()
            if ret:
                conn.unbind()
                return True
            else:
                return False
        except:
            return False


