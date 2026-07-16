# -*- coding: utf-8 -*-
"""Create GisqTxtEncrypt-compatible .jmtxt files."""

from __future__ import print_function

import os

from gmssl.sm2 import CryptSM2


PUBLIC_KEY_X = "f6e0c3345ae42b51e06bf50b98834988d54ebc7460fe135a48171bc0629eae20"
PUBLIC_KEY_Y = "5eede253a530608178a98f1e19bb737302813ba39ed3fa3c51639d7a20c7391a"
PUBLIC_KEY = PUBLIC_KEY_X + PUBLIC_KEY_Y


def encrypt_bytes(data):
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    cipher = CryptSM2(private_key="", public_key=PUBLIC_KEY, mode=0)
    return b"\x04" + cipher.encrypt(data)


def encrypt_file(input_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + "_加密.jmtxt"
    with open(input_path, "rb") as source:
        encrypted = encrypt_bytes(source.read())
    with open(output_path, "w", encoding="ascii", newline="") as target:
        target.write(encrypted.hex())
    return output_path
