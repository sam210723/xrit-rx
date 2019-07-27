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
    print("  Type: {}".format(get_name(mode)))

    # Load file
    headerField, dataField = load_lrit(fpath)

    # Check output extension
    outext = get_output_ext(mode)
    if outext == ".bin":
        print("  UNKNOWN OBSERVATION MODE (dumping as .bin file)")

    # Save data to disk
    outFName = fpath + outext
    outFile = open(outFName, mode="wb")
    outFile.write(dataField)
    outFile.close()
    print("  Saved data: \"{}\"".format(outFName))


def load_lrit(fpath):
    """
    Load LRIT file and return data field
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


def parse_fname(fpath):
    """
    Parse LRIT file name into components
    """

    split = fpath.split("_")
    mode = split[1]
    name = fpath.replace(args.ext, "")[:-3]
    name = "ADD_" + name.split("ADD_")[1]

    return name, mode


def get_output_ext(mode):
    """
    Returns output extenstion of given observation mode
    """

    exts = {}
    exts['ANT'] = '.txt'        # Alpha-numeric Text
    exts['GWW3F'] = '.gif'      # Global Wave Model
    exts['RWW3A'] = '.gif'      # Regional Wave Analysis
    exts['SICEA'] = '.png'      # Sea Ice
    exts['SSTA'] = '.gif'       # Sea Surface Temperature Analysis
    exts['SSTF24'] = '.png'     # Sea Surface Temperature Forecast 24hrs
    exts['SSTF48'] = '.png'     # Sea Surface Temperature Forecast 48hrs
    exts['SSTF72'] = '.png'     # Sea Surface Temperature Forecast 72hrs
    exts['SUFA03'] = '.gif'     # Regional Synoptic
    exts['UP50A'] = '.gif'      # Synoptic
    
    try:
        return exts[mode]
    except KeyError:
        return '.bin'


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
