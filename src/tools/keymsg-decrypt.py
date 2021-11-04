"""
keymsg-decrypt.py
https://github.com/sam210723/xrit-rx

Decrypts KMA Encryption Key Message files for GK-2A xRIT decryption
"""

import argparse
import binascii
from Crypto.Cipher import DES
import struct

argparser = argparse.ArgumentParser(description="Decrypts KMA Encryption Key Message files for GK-2A xRIT decryption")
argparser.add_argument("INPUT", action="store", help="Path to encrypted Key Message file")
argparser.add_argument("MAC", action="store", help="Ground station MAC address")
args = argparser.parse_args()

# Open encrypted Key Message file in binary mode
print(f"Opening \"{args.INPUT}\"...", end="", flush=True)
keyf = open(args.INPUT, mode="rb")

# Split file into fields
kmsg_header = keyf.read(8)
kmsg_table = keyf.read(540)
kmsg_crc = int.from_bytes(keyf.read(2), byteorder="big")
keyf.close()

# Generate CRC-16/CCITT-FALSE lookup table
crc_lut = []
poly = 0x1021
init = 0xFFFF
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
    crc_lut.append(crc)

# Calculate CRC-16/CCITT-FALSE from encrypted Key Message file
crc_data = kmsg_header + kmsg_table
calc_crc = init
for i in range(len(crc_data)):
    lut_pos = ((calc_crc >> 8) ^ crc_data[i]) & 0xFFFF
    calc_crc = ((calc_crc << 8) ^ crc_lut[lut_pos]) & 0xFFFF

# Compare CRC from file and calculated CRC
if calc_crc != kmsg_crc:
    print("CRC ERROR\nExiting...")
    exit(1)
else:
    print("CRC OK!\n")

# Parse and decrypt keys
mac = binascii.unhexlify(args.MAC) + b'\x00\x00'
decoder = DES.new(mac, DES.MODE_ECB)
enc_keys = struct.iter_unpack(">H16s", kmsg_table)
dec_keys = {}
print("       ┌──────────────────────────────────┬──────────────────┐")
print("       │ ENCRYPTED KEY                    │ DECRYPTED KEY    │")
print("┌──────┼──────────────────────────────────┼──────────────────┤")
for key in enc_keys:
    dec_keys[key[0]] = decoder.decrypt(key[1])[:8]
    print(f"│ 0x{key[0]:X} │ {key[1].hex().upper()} │ {dec_keys[key[0]].hex().upper()} │")
print("└──────┴──────────────────────────────────┴──────────────────┘")

# Write decrypted keys to file
keyf = open("EncryptionKeyMessage.bin", mode="wb")
keyf.write(b'\x00\x1E')
for key in dec_keys: keyf.write(struct.pack(">H8s", key, dec_keys[key]))
keyf.close()
print("\nDecrypted keys saved to \"EncryptionKeyMessage.bin\"")
