"""
lrit-add.py
https://github.com/sam210723/xrit-rx

Extracts data from LRIT Additional Data (ADD) files.
"""

import argparse
import glob
import os

argparser = argparse.ArgumentParser(description="Extracts data from LRIT Additional Data (ADD) files.")
argparser.add_argument("INPUT", action="store", help="LRIT file (or folder) to process")
argparser.add_argument("-o", action="store_true", help="Overwrite existing images")
argparser.add_argument("--ext", action="store", help="LRIT file extenstion (default \".lrit\")", default=".lrit")
args = argparser.parse_args()

# Globals
files = []

def init():
    """
    Parse arguments then locate images and segments
    """

    # Check if input is a directory
    if os.path.isdir(args.INPUT):
        # Loop through files with specified extension in input folder
        for f in glob.glob(args.INPUT + "/ADD_*{}".format(args.ext)):
            files.append(f)
        files.sort()
        
        if files.__len__() <= 0:
            print("No \"{}\" ADD files found".format(args.ext))
            exit(1)
        
        # Print file list
        print("Found {} \"{}\" files: ".format(len(files), args.ext))
        for f in files:
            print("  {}".format(f))
        print("-----------------------------------------\n")
        
        # Process files
        for f in files:
            name, mode = parse_fname(f)
            outext = get_output_ext(mode)
            print("Processing {}...".format(name))

            # Check image has not already been generated
            if os.path.isfile(f + outext) and not args.o:
                print("  FILE ALREADY GENERATED...SKIPPING (use -o to overwrite existing files)\n")
                continue
            
            # Process image file
            process_file(f)
            print()
        
    else:
        name, mode = parse_fname(args.INPUT)
        print("Processing {}...".format(name))

        # Load and process single file
        process_file(args.INPUT)


def process_file(fpath):
    """
    Processes LRIT ADD file
    """

    name, mode = parse_fname(fpath)
    print("  Image Type:       {}".format(get_name(mode)))

    # Load file
    headerField, dataField = load_lrit(fpath)

    # Skip encrypted files
    if parse_key_header(headerField):
        print("  SKIPPING ENCRYPTED LRIT FILE")
        return

    # Check output extension
    outext = get_output_ext(dataField)
    if outext == ".bin":
        print("  Output Format:    UNKNOWN FILE SIGNATURE (dumping as .bin file)")
    else:
        print("  Output Format:    {}".format(outext[1:].upper()))

    # Save data to disk
    outFName = fpath + outext
    outFile = open(outFName, mode="wb")
    outFile.write(dataField)
    outFile.close()
    print("  Output Path:     \"{}\"".format(outFName))


def load_lrit(fpath):
    """
    Load LRIT file and return fields
    """

    # Read file bytes from disk
    file = open(fpath, mode="rb")
    fileBytes = file.read()
    headerLen, dataLen = parse_primary(fileBytes)

    # Split file bytes into fields
    headerField = fileBytes[:headerLen]
    dataField = fileBytes[headerLen : headerLen + dataLen]

    return headerField, dataField


def parse_primary(data):
    """
    Parses LRIT primary header to get field lengths
    """

    #print("Parsing primary LRIT header...")

    primaryHeader = data[:16]

    # Header fields
    HEADER_TYPE = get_bits_int(primaryHeader, 0, 8, 128)               # Header Type (always 0x00)
    HEADER_LEN = get_bits_int(primaryHeader, 8, 16, 128)               # Header Length (always 0x10)
    FILE_TYPE = get_bits_int(primaryHeader, 24, 8, 128)                # File Type
    TOTAL_HEADER_LEN = get_bits_int(primaryHeader, 32, 32, 128)        # Total LRIT Header Length
    DATA_LEN = get_bits_int(primaryHeader, 64, 64, 128)                # Data Field Length

    #print("    Header Length: {} bytes".format(TOTAL_HEADER_LEN))
    #print("    Data Length: {} bits ({} bytes)".format(DATA_LEN, DATA_LEN/8))

    return TOTAL_HEADER_LEN, DATA_LEN


def parse_key_header(headerField):
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

    return index != b'\x00\x00'


def parse_fname(fpath):
    """
    Parse LRIT file name into components
    """

    split = fpath.split("_")
    mode = split[1]
    name = fpath.replace(args.ext, "")[:-3]
    name = "ADD_" + name.split("ADD_")[1]

    return name, mode


def get_output_ext(data):
    """
    Detects output extension based on file signature
    """

    ext = ".bin"
    if data[:3] == b'GIF':
        ext = ".gif"
    elif data[1:4] == b'PNG':
        ext = ".png"

    return ext


def get_name(mode):
    """
    Returns name of given observation mode
    """

    names = {}
    names['ANT'] = "Alpha-numeric Text"
    names['GWW3F'] = "Global Wave Model"
    names['RWW3A'] = "Regional Wave Analysis"
    names['SICEA'] = "Sea Ice"
    names['SSTA'] = "Sea Surface Temperature Analysis"
    names['SSTF24'] = "Sea Surface Temperature Forecast 24hrs"
    names['SSTF48'] = "Sea Surface Temperature Forecast 48hrs"
    names['SSTF72'] = "Sea Surface Temperature Forecast 72hrs"
    names['SUFA03'] = "Regional Synoptic"
    names['UP50A'] = "Synoptic"
    names['UP50F24'] = "Synoptic Forecast 24hrs"

    try:
        return names[mode]
    except KeyError:
        return "UNKNOWN"


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
