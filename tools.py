"""
tools.py
https://github.com/sam210723/xrit-rx

Various utility functions
"""

import errno
import os

def get_bits(data, start, length, count):
    """
    Get bits from bytes

    :param data: Bytes to get bits from
    :param start: Start offset in bits
    :param length: Number of bits to get
    :param count: Total number of bits in bytes (accounts for leading zeros)
    """

    dataInt = int.from_bytes(data, byteorder='big')
    dataBin = format(dataInt, '0' + str(count) + 'b')
    end = start + length
    bits = dataBin[start : end]

    return bits


def get_bits_int(data, start, length, count):
    """
    Get bits from bytes as integer

    :param data: Bytes to get bits from
    :param start: Start offset in bits
    :param length: Number of bits to get
    :param count: Total number of bits in bytes (accounts for leading zeros)
    """

    bits = get_bits(data, start, length, count)

    return int(bits, 2)


def CCITT_LUT():
    """
    Creates Lookup Table for CRC-16/CCITT-FALSE calculation
    """

    crcTable = []
    poly = 0x1021
    
    for i in range(256):
        crc = 0
        c = i << 8

        for j in range(8):
            if (crc ^ c) & 0x8000:
                crc = (crc << 1) ^ poly
            else:
                crc = crc << 1

            c = c << 1
            crc = crc & 0xFFFF

        crcTable.append(crc)

    return crcTable
