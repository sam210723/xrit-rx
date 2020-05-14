"""
keymsg-decrypt.py
https://github.com/sam210723/xrit-rx

Decrypts KMA Encryption Key Message files for GK-2A xRIT decryption.
"""

import argparse
import binascii
from Crypto.Cipher import DES

argparser = argparse.ArgumentParser(description="Decrypts KMA Encryption Key Message files for GK-2A xRIT decryption.")
argparser.add_argument("PATH", action="store", help="Encrypted Key Message file")
argparser.add_argument("MAC", action="store", help="Ground Station MAC address")
args = argparser.parse_args()

# Define field lengths
headerLen = 8
dataLen = 540
crcLen = 2

print("Loading \"{0}\"...".format(args.PATH))
print("MAC: {0}\n".format(args.MAC))

# Open encrypted Key Message file in binary mode
kmFile = open(args.PATH, mode="rb")
kmBytes = kmFile.read()

# Split file into fields
kmHeader = kmBytes[:headerLen]
kmData = kmBytes[headerLen: headerLen + dataLen]
kmCRC = kmBytes[-crcLen:]

# Parse Application Time header
kmHeaderHex = kmHeader.hex()
appYear = kmHeaderHex[0:4]
appMonth = kmHeaderHex[4:6]
appDay = kmHeaderHex[6:8]
appHour = kmHeaderHex[8:10]
appMin = kmHeaderHex[10:12]
appSec = str(round(int(kmHeaderHex[12:16])/1000))
print("Application Time header: 0x{0} ({1}/{2}/{3} {4}:{5}:{6})\n".format(kmHeader.hex().upper(), appDay, appMonth, appYear, appHour, appMin, appSec.zfill(2)))

# Generate CRC-16/CCITT-FALSE lookup table
print("CRC16 Checksum: 0x{0}".format(kmCRC.hex().upper()))
crcTable = []
poly = 0x1021
initial = 0xFFFF
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

# Print CRC table in hex
#print('[{}]'.format(', '.join(hex(x) for x in crcTable)))

# Calculate CRC-16/CCITT-FALSE from encrypted Key Message file
crcData = kmHeader + kmData
crc = initial

for i in range(len(crcData)):
    lutPos = ((crc >> 8) ^ crcData[i]) & 0xFFFF
    crc = ((crc << 8) ^ crcTable[lutPos]) & 0xFFFF

# Compare CRC from file and calculated CRC
print("Calculated CRC: 0x{0}".format(hex(crc)[2:].upper()))
if int(crc) == int.from_bytes(kmCRC, byteorder='big'):
    print("CRC OK!\n")
else:
    print("CRC ERROR\n")
    exit(0)

# Add encrypted keys to list
indexes = []
encKeys = []
print("[Index]: Encrypted Key")

for i in range(30):     # 30 keys total
    offset = i*18       # 18 bytes per index/key pair
    indexes.append(kmData[offset: offset+2])        # Bytes 0-1: Key index
    encKeys.append(kmData[offset+2:offset+18])      # Bytes 2-17: Encrypted key
    print("[{0}   ]: {1}".format(indexes[i][-1:].hex().upper(), encKeys[i].hex().upper()))

# Decrypt keys and add to list
macBin = binascii.unhexlify(args.MAC) + b'\x00\x00'     # MAC String to binary + two byte padding
decoder = DES.new(macBin, DES.MODE_ECB)
decKeys = []
print("\n[Index]: Decrypted Key")

for i in range(30):
    decKey = decoder.decrypt(encKeys[i])
    decKeys.append(decKey[:8])
    print("[{0}   ]: {1}".format(indexes[i][-1:].hex().upper(), decKeys[i].hex().upper()))

# Write decrypted Key Message file to disk
decPath = args.PATH.split("_" + args.MAC)[0] + ".bin"
print("\nOutput file: {0}".format(decPath))
decKmFile = open(decPath, mode="wb")

decKmFile.write(b'\x00\x1E')  # Number of keys (30/0x1E, 2 bytes)
for i in range(30):
    decKmFile.write(indexes[i])
    decKmFile.write(decKeys[i])

decKmFile.close()
