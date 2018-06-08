#coding: utf8
import sys
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import configparser

config = configparser.ConfigParser()
cfgfile = open('../conf/setting.cnf', 'r')
config.readfp(cfgfile)
key = config.get('key', 'encrypt_iv')


class prpcrypt():
    def __init__(self):
        self.key = key
        self.mode = AES.MODE_CBC
     
    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        print ("111111111")
        length = 32
        count = len(text)
        add = length - (count % length)
        text = text + ('\0' * add)
        self.ciphertext = cryptor.encrypt(text)
        return b2a_hex(self.ciphertext)

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        plain_text = cryptor.decrypt(a2b_hex(text))
        return plain_text.rstrip('\0')


if __name__ == '__main__':
    pp = prpcrypt()
    e = pp.encrypt("test123")
    d = pp.decrypt('e835b3eb4e5a60f8c184b3d77bbc3d40356cbdc9fbdf0d0660bc0c76864e1de4')                     
    print (e, d)
    e = pp.encrypt("000000000000000000000")
    d = pp.decrypt(e)                  
    print (e, d)
