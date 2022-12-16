import os

import bson
from Crypto.Cipher import AES
from dotenv import load_dotenv

load_dotenv()

# read CHAT_MASK from .env file
CHAT_MASK = os.getenv('CHAT_MASK')
AES_KEY_LENGTH = 16
AES_IV_LENGTH = 16


def decrypt(text_asset_file) -> dict:
    data = text_asset_file.script
    raw = _text_asset_decrypt(data)
    return bson.loads(raw)


def _unpad(s): return s[0:(len(s) - s[-1])]


def _rijndael_decrypt(data, key, iv):
    aes_obj = AES.new(key, AES.MODE_CBC, iv)
    decrypt_buf = aes_obj.decrypt(data)
    return _unpad(decrypt_buf)


def _text_asset_decrypt(data):
    aes_key = CHAT_MASK[:AES_KEY_LENGTH].encode()
    aes_iv = bytearray(AES_IV_LENGTH)
    # 文件头16字节异或CHAT_MASK后16字节, 得到aes加密iv
    buf = data[128:128+AES_IV_LENGTH]
    mask = CHAT_MASK[AES_KEY_LENGTH:].encode()
    for i in range(len(buf)):
        aes_iv[i] = buf[i] ^ mask[i]
    # 对剩余数据aes解密
    game_data = _rijndael_decrypt(
        data[AES_KEY_LENGTH+128:], aes_key, aes_iv)
    return game_data
