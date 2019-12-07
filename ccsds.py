"""
ccsds.py
https://github.com/sam210723/xrit-rx

Parsing and assembly functions for all CCSDS protocol layers
"""

from Crypto.Cipher import DES
from enum import Enum
import os


class VCDU:
    """
    Parses CCSDS Virtual Channel Data Unit (VCDU)
    """

    def __init__(self, data):
        self.data = data
        self.tools = Tools()
        self.parse()
    
    def parse(self):
        """
        Parse VCDU header fields
        """

        header = self.data[:6]

        # Header fields
        self.VER = self.tools.get_bits_int(header, 0, 2, 48)           # Virtual Channel Version
        self.SCID = self.tools.get_bits_int(header, 2, 8, 48)          # Spacecraft ID
        self.VCID = self.tools.get_bits_int(header, 10, 6, 48)         # Virtual Channel ID
        self.COUNTER = self.tools.get_bits_int(header, 16, 24, 48)     # VCDU Counter
        self.REPLAY = self.tools.get_bits_int(header, 40, 1, 48)       # Replay Flag
        self.SPARE = self.tools.get_bits_int(header, 41, 7, 48)        # Spare (always b0000000)

        # Spacecraft and virtual channel names
        self.SC = self.get_SC(self.SCID)
        self.VC = self.get_VC(self.VCID)

        # M_PDU contained in VCDU
        self.MPDU = self.data[6:]
    
    def get_SC(self, scid):
        """
        Get name of spacecraft by ID
        """

        scname = {}
        scname[195] = "GK-2A"

        try:
            return scname[scid]
        except KeyError:
            return "UNKNOWN"
    
    def get_VC(self, vcid):
        """
        Get name of Virtual Channel by ID
        """
        vcname = {}
        vcname[0] = "FULL DISK"
        vcname[4] = "ALPHA-NUMERIC TEXT"
        vcname[5] = "ADDITIONAL DATA"
        vcname[63] = "FILL"

        try:
            return vcname[vcid]
        except KeyError:
            return "UNKNOWN"

    def print_info(self):
        """
        Prints information about the current VCDU to the console
        """

        print("\n[VCID {}] {}: {}".format(self.VCID, self.SC, self.VC))


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
        self.COUNTER = self.tools.get_bits_int(header, 0, 16, 80)                # File Counter
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
        #TODO: Update when GK-2A specification available
        if 1 <= self.COUNTER <= 10:
            band = "VIS"
            num = self.COUNTER
        elif 11 <= self.COUNTER <= 20:
            band = "SWIR"
            num = self.COUNTER - 10
        elif 21 <= self.COUNTER <= 30:
            band = "WV"
            num = self.COUNTER - 20
        elif 31 <= self.COUNTER <= 40:
            band = "IR1"
            num = self.COUNTER - 30
        elif 41 <= self.COUNTER <= 50:
            band = "IR2"
            num = self.COUNTER - 40
        else:
            band = "Other"
            num = "?"
        
        countType = " ({}, SEGMENT: {})".format(band, num)

        print("  [TP_File] COUNTER: {}{}   LENGTH: {}".format(self.COUNTER, countType, self.LENGTH))


class S_PDU:
    """
    Decrypts CCSDS Session Protocol Data Unit (S_PDU)
    """

    def __init__(self, data, k):
        self.data = data
        self.tools = Tools()
        self.keys = k
        self.key = None
        self.headerField = None
        self.dataField = None
        self.PLAINTEXT = None

        # Check keys have been loaded
        if self.keys != {}:
            self.parse()

            # Check encryption is applied to file
            if self.key != 0:
                self.decrypt()
            else:
                self.PLAINTEXT = self.data
        else:
            self.PLAINTEXT = self.data
    
    def parse(self):
        """
        Parses xRIT primary and key headers
        """
        
        primaryHeader = self.data[:16]

        # Header fields
        self.HEADER_TYPE = self.tools.get_bits_int(primaryHeader, 0, 8, 128)               # Header Type (always 0x00)
        self.HEADER_LEN = self.tools.get_bits_int(primaryHeader, 8, 16, 128)               # Header Length (always 0x10)
        self.FILE_TYPE = self.tools.get_bits_int(primaryHeader, 24, 8, 128)                # File Type
        self.TOTAL_HEADER_LEN = self.tools.get_bits_int(primaryHeader, 32, 32, 128)        # Total xRIT Header Length
        self.DATA_LEN = self.tools.get_bits_int(primaryHeader, 64, 64, 128)                # Data Field Length

        #print("  Header Length: {} bits ({} bytes)".format(self.TOTAL_HEADER_LEN, self.TOTAL_HEADER_LEN/8))
        #print("  Data Length: {} bits ({} bytes)".format(self.DATA_LEN, self.DATA_LEN/8))

        self.headerField = self.data[:self.TOTAL_HEADER_LEN]
        self.dataField = self.data[self.TOTAL_HEADER_LEN: self.TOTAL_HEADER_LEN + self.DATA_LEN]
        
        # Loop through headers until Key header (type 7)
        offset = self.HEADER_LEN
        nextHeader = self.get_next_header(offset)

        while nextHeader != 7:
            offset += self.get_header_len(offset)
            nextHeader = self.get_next_header(offset)

        # Parse Key header (type 7)
        keyHLen = int.from_bytes(self.headerField[offset + 1 : offset + 3], byteorder='big')
        index = self.headerField[offset + 5 : offset + keyHLen]

        # Catch wrong key index
        try:
            self.key = self.keys[index]
        except KeyError:
            if index != b'\x00\x00': print("  UNKNOWN ENCRYPTION KEY INDEX")
            self.key = 0
        
        # Check block length if encryption is applied
        if self.key != 0:
            # Append null bytes to data field to fill last 8 byte DES block
            dFMod8 = len(self.dataField) % 8
            if dFMod8 != 0:
                for i in range(dFMod8):
                    self.dataField += b'\x00'
                #print("  Added {} null bytes to fill last DES block".format(dFMod8))
        
        # Set key header to 0x0000
        decHeaderField = self.headerField[: offset + 3]
        decHeaderField += b'\x00\x00\x00\x00'
        decHeaderField += self.headerField[offset + 7:]
        self.headerField = decHeaderField

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
    
    def decrypt(self):
        """
        Decrypts S_PDU data field into a plain text xRIT file
        """

        decoder = DES.new(self.key, DES.MODE_ECB)
        decData = decoder.decrypt(self.dataField)

        self.PLAINTEXT = self.headerField + decData


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
        if not os.path.exists("{}/{}".format(root, txDate)): os.mkdir(root + "/" + txDate)
        if not os.path.exists("{}/{}/{}".format(root, txDate, obMode)): os.mkdir(root + "/" + txDate + "/" + obMode)

        path = "/{}/{}/".format(txDate, obMode)
        return root + path + self.FILE_NAME

    def save(self, root):
        """
        Saves xRIT file to disk
        """

        # Save file to disk
        outPath = self.get_save_path(root)
        outFile = open(outPath, mode="wb")
        outFile.write(self.data)
        outFile.close()

    def print_info(self):
        """
        Prints information about the current xRIT file to the console
        """

        print("  [NEW FILE] {}: \"{}\"".format(self.FILE_TYPE, self.FILE_NAME))


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
