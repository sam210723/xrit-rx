"""
ccsds.py
https://github.com/sam210723/xrit-rx

Parsing and assembly functions for all CCSDS protocol layers
"""

import colorama
from   colorama import Fore, Back, Style
from   Crypto.Cipher import DES
from   enum import Enum
import os
from   pathlib import Path
import struct
from   collections import namedtuple


class VCDU:
    """
    Parses CCSDS Virtual Channel Data Unit (VCDU)
    """

    def __init__(self, buffer):
        self.payload = buffer[6:]
        
        header = int.from_bytes(buffer[:6], byteorder="big")
        self.version = (header & 0xC00000000000) >> 46      # Virtual Channel version number
        self.scid    = (header & 0x3FC000000000) >> 38      # Spacecraft ID
        self.vcid    = (header & 0x003F00000000) >> 32      # Virtual Channel ID
        self.counter = (header & 0x0000FFFFFF00) >> 8       # Continuity Counter
        self.replay  = (header & 0x000000000080) >> 7       # Replay Flag
        self.spare   = (header & 0x00000000007F)            # Spare Bits

    def print_info(self, info):
        """
        Prints information about the current VCDU to the console
        """

        for sc in info:
            if self.scid == info[sc]["SCID"]: self.sc = sc
        
        self.vc = info[self.sc]["VCID"][self.vcid]

        print(f"\n[VCID {self.vcid}] {self.sc}: {self.vc}")


class M_PDU:
    """
    Parses CCSDS Multiplexing Protocol Data Unit (M_PDU)
    """

    def __init__(self, data):
        self.data = data
        self.tools = Tools()
        self.parse()
    
    def parse(self):
        """
        Parse M_PDU header fields
        """

        header = self.data[:2]

        # Header fields
        #self.SPARE = self.tools.get_bits(header, 0, 5, 16)            # Spare Field (always b00000)
        self.POINTER = self.tools.get_bits_int(header, 5, 11, 16)      # First Pointer Header

        # Detect if M_PDU contains CP_PDU header
        if self.POINTER != 2047:  # 0x07FF
            self.HEADER = True
        else:
            self.HEADER = False
        
        self.PACKET = self.data[2:]
    
    def print_info(self):
        """
        Prints information about the current M_PDU to the console
        """

        if self.HEADER:
            print("    [M_PDU] HEADER: 0x{}".format(hex(self.POINTER)[2:].upper()))
        else:
            print("    [M_PDU]")


class CP_PDU:
    """
    Parses and assembles CCSDS Path Protocol Data Unit (CP_PDU)
    """

    def __init__(self, data):
        self.header = None
        self.tools = Tools()
        self.PARSED = False
        self.PAYLOAD = None
        self.Sequence = Enum('Sequence', 'CONTINUE FIRST LAST SINGLE')

        # Parse header once enough data is present
        if len(data) >= 6:
            self.header = data[:6]
            self.parse()
            
            # Add post-header data to payload
            self.PAYLOAD = data[6:]
        else:
            # Add bytes to header then wait for remaining bytes to be added via append()
            self.header = data
    
    def parse(self):
        """
        Parse CP_PDU header fields
        """

        # Header fields
        self.VER = self.tools.get_bits(self.header, 0, 3, 48)                   # Version (always b000)
        self.TYPE = self.tools.get_bits(self.header, 3, 1, 48)                  # Type (always b0)
        self.SHF = self.tools.get_bits(self.header, 4, 1, 48)                   # Secondary Header Flag
        self.APID = self.tools.get_bits_int(self.header, 5, 11, 48)             # Application Process ID
        self.SEQ = self.tools.get_bits_int(self.header, 16, 2, 48)              # Sequence Flag
        self.COUNTER = self.tools.get_bits_int(self.header, 18, 14, 48)         # Packet Sequence Counter
        self.LENGTH = self.tools.get_bits_int(self.header, 32, 16, 48) + 1      # Packet Length

        # Parse sequence flag
        if self.SEQ == 0:
            self.SEQ = self.Sequence.CONTINUE
        elif self.SEQ == 1:
            self.SEQ = self.Sequence.FIRST
        elif self.SEQ == 2:
            self.SEQ = self.Sequence.LAST
        elif self.SEQ == 3:
            self.SEQ = self.Sequence.SINGLE

        self.PARSED = True
    
    def append(self, data):
        """
        Append data to CP_PDU payload
        """

        # Get number of bytes remaining in header
        rem = 6 - len(self.header)
        if rem != 0:
            self.header += data[:rem]

        # Parse header once enough data is present
        if not self.PARSED and len(self.header) == 6:
            self.parse()
            self.PAYLOAD = data[rem:]
        else:
            # Add data to payload if header already parsed
            self.PAYLOAD += data

    def finish(self, data, crclut):
        """
        Finish CP_PDU by checking length and CRC 
        """

        # Append last chunk of data
        self.append(data)

        # Check payload length against expected length
        plen = len(self.PAYLOAD)
        if plen != self.LENGTH:
            lenok = False
        else:
            lenok = True
        
        # Check payload CRC against expected CRC
        if not self.CRC(crclut):
            crcok = False
        else:
            crcok = True

        return lenok, crcok
    
    def is_EOF(self):
        """
        Checks if CP_PDU is the "EOF marker" CP_PDU of a TP_File.

        After a CP_PDU with the Sequence Flag of LAST, an extra CP_PDU is sent with the following:
            APID: 0
            Counter: 0
            Sequence Flag: CONTINUE (0)
            Length: 1
        """

        if self.COUNTER == 0 and self.APID == 0 and self.LENGTH == 1 and self.SEQ == self.Sequence.CONTINUE:
            return True
        else:
            return False
    
    def CCITT_LUT(self):
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

    def CRC(self, lut):
        """
        Calculate CRC-16/CCITT-FALSE 
        """

        initial = 0xFFFF
        crc = initial
        data = self.PAYLOAD[:-2]
        txCRC = self.PAYLOAD[-2:]

        # Calculate CRC
        for i in range(len(data)):
            lutPos = ((crc >> 8) ^ data[i]) & 0xFFFF
            crc = ((crc << 8) ^ lut[lutPos]) & 0xFFFF

        # Compare CRC from CP_PDU and calculated CRC
        if int(crc) == int.from_bytes(txCRC, byteorder='big'):
            return True
        else:
            return False

    def print_info(self):
        """
        Prints information about the current CP_PDU to the console
        """

        print("  [CP_PDU] APID: {}   SEQ: {}   #{}   LEN: {}".format(self.APID, self.SEQ.name, self.COUNTER, self.LENGTH))


class TP_File:
    """
    Parses and assembles CCSDS Transport Files (TP_File)
    """

    def __init__(self, data):
        self.data = data
        self.tools = Tools()
        self.PAYLOAD = None
        self.parse()
    
    def parse(self):
        """
        Parse TP_File header fields
        """

        header = self.data[:10]

        # Header fields
        self.COUNTER = self.tools.get_bits_int(header, 0, 16, 80)                # File Counter #FIXME: Update for GK-2A
        self.LENGTH = int(self.tools.get_bits_int(header, 16, 64, 80)/8)         # File Length

        # Add post-header data to payload
        self.PAYLOAD = self.data[10:]
    
    def append(self, data):
        """
        Append data to TP_File payload
        """

        self.PAYLOAD += data

    def finish(self, data):
        """
        Finish CP_PDU by checking length
        """

        # Append last chunk of data
        self.append(data)

        # Check payload length against expected length
        plen = len(self.PAYLOAD)
        if plen != self.LENGTH:
            lenok = False
        else:
            lenok = True
        
        return lenok
    
    def print_info(self):
        """
        Prints information about the current TP_File to the console
        """

        # Get image band based on file counter
        if 0 <= self.COUNTER <= 9:
            band = "VI006"
            num = self.COUNTER + 1
        elif 10 <= self.COUNTER <= 19:
            band = "SW038"
            num = self.COUNTER - 9
        elif 20 <= self.COUNTER <= 29:
            band = "WV069"
            num = self.COUNTER - 19
        elif 30 <= self.COUNTER <= 39:
            band = "IR105"
            num = self.COUNTER - 29
        elif 40 <= self.COUNTER <= 49:
            band = "IR123"
            num = self.COUNTER - 39
        else:
            band = "Other"
            num = "?"
        
        countType = " ({}, SEGMENT: {})".format(band, num)

        print("  [TP_File] COUNTER: {}{}   LENGTH: {}".format(self.COUNTER, countType, self.LENGTH))


class S_PDU:
    """
    Decrypts CCSDS Session Protocol Data Unit (S_PDU)
    """

    def __init__(self, data, keys):
        self.header_field = None    # xRIT header field
        self.data_field = None      # xRIT data field
        self.keys = keys            # Encryption key list
        self.key_index = None       # Encryption key index
        self.payload = None         # xRIT payload

        # Parse xRIT headers
        self.parse(data)

        if self.keys == {} or self.key_index == 0:
            # No keys or file unencrypted
            self.payload = self.header_field + self.data_field
        else:
            # Get key from list
            try:
                self.key = self.keys[self.key_index]
            except KeyError:
                log(f"  UNKNOWN ENCRYPTION KEY INDEX ({self.key_index:02X})", style="error")
                self.key = 0

            # Setup DES cipher
            cipher = DES.new(self.key, DES.MODE_ECB)

            # Check block boundary alignment
            mod = len(self.data_field) % 8

            # Payload is not aligned to ECB block boundary
            if mod > 0:
                log("PAYLOAD NOT ALIGNED WITH DES ECB BLOCK BOUNDARY\n", style="error")

                # Add padding bytes to end of payload
                self.data_field = bytearray(self.data_field)
                self.data_field.extend(bytes(8 - mod))
                self.data_field = bytes(self.data_field)

                # Decrypt payload
                decrypted = cipher.decrypt(self.data_field)

                # Strip padding bytes
                self.data_field = decrypted[:8 - mod]
            else:
                # Decrypt payload
                decrypted = cipher.decrypt(self.data_field)

            # Add header field to unencrypted payload
            self.payload = self.header_field + decrypted


    def parse(self, data):
        """
        Parses xRIT primary header and key header
        """
        
        # Parse primary header
        primary_header = namedtuple(
            'xrit_primary_header',
            'type length file_type header_length data_length'
        )(*struct.unpack(">BHBIQ", data[:16]))

        # Get data field
        self.header_field = data[:primary_header.header_length]
        self.data_field = data[primary_header.header_length : primary_header.header_length + primary_header.data_length]

        # Get key header offset
        offset = self.skip(self.header_field, 7)

        # Parse key header
        key_header = namedtuple(
            'xrit_key_header',
            'type length index'
        )(*struct.unpack(">BHI", self.header_field[offset : offset + 7]))

        # Get encryption key index
        self.key_index = key_header.index

        # Set key index to zero
        self.header_field = self.header_field[:offset] + struct.pack(">BHI", 7, 7, 0) + self.header_field[offset + 7:]


    def skip(self, header_field, header_type):
        """
        Get offset of header type in header field
        """

        offset = 0
        while True:
            # Check enough data left in header field
            if offset > (len(header_field) - 3): return -1

            # Get header type and length
            header = struct.unpack(">BH", header_field[offset : offset + 3])

            # Return offset of header
            if header[0] == header_type: return offset
            offset += header[1]


class xRIT:
    """
    Parses and assembles CCSDS xRIT Files (xRIT_Data)
    """

    def __init__(self, data):
        self.data = data
        self.tools = Tools()
        self.parse()
    
    def parse(self):
        """
        Parse xRIT headers
        """

        primaryHeader = self.data[:16]

        # Header fields
        self.HEADER_TYPE = self.tools.get_bits_int(primaryHeader, 0, 8, 128)               # Header Type (always 0x00)
        self.HEADER_LEN = self.tools.get_bits_int(primaryHeader, 8, 16, 128)               # Header Length (always 0x10)
        self.FILE_TYPE = self.tools.get_bits_int(primaryHeader, 24, 8, 128)                # File Type
        self.TOTAL_HEADER_LEN = self.tools.get_bits_int(primaryHeader, 32, 32, 128)        # Total xRIT Header Length
        self.DATA_LEN = self.tools.get_bits_int(primaryHeader, 64, 64, 128)                # Data Field Length

        # Get file type
        if self.FILE_TYPE == 0:
            self.FILE_TYPE = "Image Data"
        elif self.FILE_TYPE == 1:
            self.FILE_TYPE = "GTS Message"
        elif self.FILE_TYPE == 2:
            self.FILE_TYPE = "Alphanumeric Text"
        elif self.FILE_TYPE == 3:
            self.FILE_TYPE = "Encryption Key Message"
        elif self.FILE_TYPE == 255:     # Not in specification
            self.FILE_TYPE = "Additional Data"
        else:
            self.FILE_TYPE = str(self.FILE_TYPE) + " (UNKNOWN)"

        # Loop through headers until Annotation Text header (type 4)
        offset = self.HEADER_LEN
        nextHeader = self.get_next_header(offset)

        while nextHeader != 4:
            offset += self.get_header_len(offset)
            nextHeader = self.get_next_header(offset)
        
        # Parse Annotation Text header (type 4)
        athLen = self.get_header_len(offset)
        self.FILE_NAME = self.data[offset + 3 : offset + athLen].decode('utf-8')

        # Get data field
        self.DATA_FIELD = self.data[self.TOTAL_HEADER_LEN : self.TOTAL_HEADER_LEN + self.DATA_LEN]
    
    def get_next_header(self, offset):
        """
        Returns type of next header
        """
        return int.from_bytes(self.data[offset : offset + 1], byteorder='big')
    
    def get_header_len(self, offset):
        """
        Returns length of current header
        """
        return int.from_bytes(self.data[offset + 1 : offset + 3], byteorder='big')
    
    def get_save_path(self, root):
        """
        Parses xRIT file name
        """

        # Split file name into components
        fnameSplit = self.FILE_NAME.split("_")

        fType = fnameSplit[0]

        if fType == "IMG":
            obMode = fnameSplit[1]
            seqNum = fnameSplit[2]
            specCh = fnameSplit[3]
            txDate = fnameSplit[4]
            txTime = fnameSplit[5]
            segNum = fnameSplit[6][:2]
            fExt = self.FILE_NAME.split(".")[1]
        elif fType == "ADD":
            obMode = fnameSplit[1]
            seqNum = fnameSplit[2]
            txDate = fnameSplit[3]
            txTime = fnameSplit[4]
            segNum = fnameSplit[5][:2]
            fExt = self.FILE_NAME.split(".")[1]
        
        # Check output directories exist
        if root:
            file_path = root / txDate / obMode
            file_path.mkdir(parents=True, exist_ok=True)
            file_path = (file_path / self.FILE_NAME).absolute()
        else:
            file_path = f"{txDate}/{obMode}/{self.FILE_NAME}"

        return file_path

    def save(self, root):
        """
        Saves xRIT file to disk
        """

        # Save file to disk
        outPath = self.get_save_path(root)
        outFile = open(outPath, mode="wb")
        outFile.write(self.data)
        outFile.close()

    def print_info(self, verbose):
        """
        Prints information about the current xRIT file to the console
        """

        print("  [XRIT] \"{}\"".format(self.FILE_NAME))

        if verbose:
            print("    HEADER LEN: {}".format(self.TOTAL_HEADER_LEN))
            print("    DATA LEN:   {}".format(self.DATA_LEN))
            print("    TOTAL LEN:  {}".format(self.TOTAL_HEADER_LEN + self.DATA_LEN))


class Tools:
    """
    Various utility functions
    """

    def get_bits(self, data, start, length, count):
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


    def get_bits_int(self, data, start, length, count):
        """
        Get bits from bytes as integer

        :param data: Bytes to get bits from
        :param start: Start offset in bits
        :param length: Number of bits to get
        :param count: Total number of bits in bytes (accounts for leading zeros)
        """

        bits = self.get_bits(data, start, length, count)

        return int(bits, 2)



def log(msg, style="none"):
        """
        Writes to console
        """

        # Colorama styles
        styles = {
            "none":   "",
            "ok":    f"{colorama.Fore.GREEN}{colorama.Style.BRIGHT}",
            "error": f"{colorama.Fore.WHITE}{colorama.Back.RED}{colorama.Style.BRIGHT}"
        }
        
        print(f"{styles[style]}{msg}")
