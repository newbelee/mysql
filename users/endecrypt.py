#coding: utf8
import sys
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import configparser
import base64

config = configparser.ConfigParser()
cfgfile = open('/data/mysql_platform/conf/setting.cnf', 'r')
config.readfp(cfgfile)
key = base64.decodebytes(bytes(config.get('key', 'encrypt_key'), encoding='utf-8'))
iv = base64.decodebytes(bytes(config.get('key', 'encrypt_iv'), encoding='utf-8'))



class endeCrypt:
    def __init__(self, key=key, iv=iv):
        self.key = key
        self.mode = AES.MODE_CBC
        self.iv = iv


    def encrypt(self, text):
        PADDING='\0'
        cryptor = AES.new(self.key, self.mode, self.iv)
        data = lambda text: text + bytes((16 - len(text)%16) * PADDING, encoding='utf-8')
        ciphertext = cryptor.encrypt(data(text))
        return b2a_hex(ciphertext)

    def decrypt(self, ciphertext):
        cryptor = AES.new(self.key, self.mode, self.iv)
        text = cryptor.decrypt(a2b_hex(ciphertext))
        return str(text, encoding='utf-8').rstrip('\x00')

    def get_rw_user_pass(self):
        user = config.get('mysqllogin', 'admin_user')
        password_bytes = bytes(config.get('mysqllogin', 'admin_passwd'), encoding='utf-8')
        password = self.decrypt(password_bytes)
        return user, password

    def get_ro_user_pass(self):
        user = config.get('mysqllogin', 'review_user')
        password_bytes = bytes(config.get('mysqllogin', 'review_passwd'), encoding='utf-8')
        password = self.decrypt(password_bytes)
        return user, password

    def get_mysqltool_user_pass(self):
        user = config.get('mysqltool', 'admin_user')
        password_bytes = bytes(config.get('mysqltool', 'admin_passwd'), encoding='utf-8')
        password = self.decrypt(password_bytes)
        return user, password



# en = endeCrypt()
# in_str = "test123"
# test = bytes(in_str, encoding='utf-8')
# user, password = en.get_ro_user_pass()
#
# print(user, password)
