"""
xrit-decrypt.py
https://github.com/sam210723/xrit-rx

Decrypts xRIT files into a plain-text xRIT file using single layer DES
"""

import argparse
import glob
import os
from Crypto.Cipher import DES

argparser = argparse.ArgumentParser(description="Decrypts xRIT file into a plain-text xRIT file using single layer DES")
argparser.add_argument("KEYS", action="store", help="Decrypted key file")
argparser.add_argument("XRIT", action="store", help="xRIT file (or folder) to decrypt")
args = argparser.parse_args()

xritFile = None
xritBytes = None
files = []
keys = {}

def init():
    # Load key file
    load_keys(args.KEYS)

    # If input is a directory
    if os.path.isdir(args.XRIT):
        # Loop through all .lrit/.hrit files in directory
        print("Finding xRIT segments...\n")

        # Loop through files with .lrit extension in input folder
        for f in glob.glob(args.XRIT + "/*.lrit"):
            files.append(f)
        
        # Loop through files with .hrit extension in input folder
        for f in glob.glob(args.XRIT + "/*.hrit"):
            files.append(f)

        if files.__len__() <= 0:
            print("No LRIT/HRIT files found")
            exit(1)
        
        # Print file list
        print("Found {} files: ".format(len(files)))
        for f in files:
            print("  {}".format(f))
        
        print("\nDecrypting files...")
        print("-----------------------------------------")
        for f in files:
            load_xrit(f)
            
            print("-----------------------------------------")

        print("\nFinished decryption\nExiting...")
        exit(0)

    else:
        # Load and decrypt single file
        load_xrit(args.XRIT)


def load_keys(kpath):
    """
    Load and parse key file
    """
    
    print("Loading decryption keys...")

    p = os.path.abspath(kpath)
    f = open(p, 'rb')
    fbytes = f.read()

    # Parse key count
    count = int.from_bytes(fbytes[:2], byteorder='big')

    # Parse keys
    for i in range(count):
        offset = (i * 10) + 2
        index = fbytes[offset : offset + 2]
        key = fbytes[offset + 2 : offset + 10]

        '''
        i = hex(int.from_bytes(index, byteorder='big')).upper()[2:]
        k = hex(int.from_bytes(key, byteorder='big')).upper()[2:]
        print("{}: {}".format(i, k))
        '''

        # Add key to dictionary
        keys[index] = key


def load_xrit(fpath):
    """
    Loads xRIT file from disk
    """

    print("\nLoading xRIT file \"{}\"...".format(fpath))

    xritFile = open(fpath, 'rb')
    xritBytes = xritFile.read()
    xritFile.close()

    parse_primary_header(xritBytes, fpath)


def parse_primary_header(data, fpath):
    """
    Parses xRIT primary header to get field lengths
    """

    print("Parsing xRIT primary header...")

    primaryHeader = data[:16]

    # Header fields
    HEADER_TYPE = get_bits_int(primaryHeader, 0, 8, 128)               # File Counter (always 0x00)
    HEADER_LEN = get_bits_int(primaryHeader, 8, 16, 128)               # Header Length (always 0x10)
    FILE_TYPE = get_bits_int(primaryHeader, 24, 8, 128)                # File Type
    TOTAL_HEADER_LEN = get_bits_int(primaryHeader, 32, 32, 128)        # Total xRIT Header Length
    DATA_LEN = get_bits_int(primaryHeader, 64, 64, 128)                # Data Field Length

    print("  Header Length: {} bits ({} bytes)".format(TOTAL_HEADER_LEN, TOTAL_HEADER_LEN/8))
    print("  Data Length: {} bits ({} bytes)".format(DATA_LEN, DATA_LEN/8))

    headerField = data[:TOTAL_HEADER_LEN]
    dataField = data[TOTAL_HEADER_LEN: TOTAL_HEADER_LEN + DATA_LEN]

    # Append null bytes to data field to fill last 8 byte DES block
    dFMod8 = len(dataField) % 8
    if dFMod8 != 0:
        for i in range(dFMod8):
            dataField += b'x00'
        print("\nAdded {} null bytes to fill last DES block".format(dFMod8))

    parse_key_header(headerField, dataField, fpath)


def parse_key_header(headerField, dataField, fpath):
    """
    Parses xRIT key header to get key index
    """

    print("\nParsing xRIT key header...")

    # Loop through headers until Key header (type 7)
    offset = 0
    nextHeader = int.from_bytes(headerField[offset : offset + 1], byteorder='big')

    while nextHeader != 7:
        offset += int.from_bytes(headerField[offset + 1 : offset + 3], byteorder='big')
        nextHeader = int.from_bytes(headerField[offset : offset + 1], byteorder='big')
        
    # Parse Key header (type 7)
    keyHLen = int.from_bytes(headerField[offset + 1 : offset + 3], byteorder='big')
    index = headerField[offset + 5 : offset + keyHLen]
    indexStr = hex(int.from_bytes(index, byteorder='big')).upper()[2:]

    if index != b'\x00\x00':
        print("  Key Index: {}".format(indexStr))
        key = keys[index]

        # Set key header to 0x0000
        decHeaderField = headerField[: offset + 3]
        decHeaderField += b'\x00\x00\x00\x00'
        decHeaderField += headerField[offset + 7:]

        decrypt(decHeaderField, dataField, fpath, key)
    else:
        print("  Key Index: 0 (UNENCRYPTED)")
        print("  Skipping unencrypted file")


def decrypt(headers, data, fpath, key):
    print("\nDecrypting...")

    decoder = DES.new(key,DES.MODE_ECB)
    decData = decoder.decrypt(data)
    
    decFile = open(fpath + ".dec", 'wb')
    decFile.write(headers)
    decFile.write(decData)
    decFile.close()
    print("Output file: {}".format(fpath + ".dec"))


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

try:
    init()
except KeyboardInterrupt:
    print("Exiting...")
    exit(0)
