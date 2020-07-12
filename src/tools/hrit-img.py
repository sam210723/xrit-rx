"""
hrit-img.py
https://github.com/sam210723/xrit-rx

Generates JPEG images from HRIT IMG files.
"""

import argparse
import glob
import io
import numpy as np
import os
from PIL import Image, ImageFile
import subprocess
import sys

argparser = argparse.ArgumentParser(description="Generates JPEG images from HRIT IMG files.")
argparser.add_argument("INPUT", action="store", help="HRIT file (or folder) to process")
argparser.add_argument("-s", action="store_true", help="Process incomplete images as individual segments")
argparser.add_argument("-o", action="store_true", help="Overwrite existing images")
argparser.add_argument("--ext", action="store", help="HRIT file extenstion (default \".hrit\")", default=".hrit")
args = argparser.parse_args()
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Globals
files = []
groups = {}

def init():
    """
    Parse arguments then locate images and segments
    """

    # Check if input is a directory
    if os.path.isdir(args.INPUT):
        # Loop through files with specified extension in input folder
        for f in glob.glob(args.INPUT + "/IMG_*{}".format(args.ext)):
            files.append(f)
        files.sort()
        
        if files.__len__() <= 0:
            print("No \"{}\" IMG files found".format(args.ext))
            exit(1)
        
        # Print file list
        print("Found {} \"{}\" files: ".format(len(files), args.ext))
        for f in files:
            print("  {}".format(f))

        # Group image segments
        for f in files:
            img, mode, chan, segment = parse_fname(f)

            # If group exists in group list
            if img not in groups.keys():
                groups[img] = []
            
            # Add file to group
            groups[img].append(f)
        
        # Print image list
        print("\n\nFound {} images:".format(len(groups.keys())))
        for img in list(groups):
            print("  {}".format(img))

            # Check for missing segments
            foundSegments = len(groups[img])
            name, mode, chan, segment = parse_fname(groups[img][0])
            totalSegments = get_total_segments(mode)

            if totalSegments == None:
                print("    Unrecognised observation mode \"{}\"".format(mode))
            
            if foundSegments == totalSegments:
                print("    Found {} of {} segments".format(foundSegments, totalSegments))
            else:
                print("    MISSING {} SEGMENTS".format(totalSegments - foundSegments))

                if args.s:
                    # Process as individual segments
                    print("    PROCESSING AS INDIVIDUAL SEGMENTS")
                else:
                    # Remove image group from list
                    groups.pop(img, None)
                    print("    IMAGE GENERATION WILL BE SKIPPED")
            
            # Check image has not already been generated
            if os.path.isfile(args.INPUT + "\\" + name + ".jpg") and not args.o:
                print("    IMAGE ALREADY GENERATED...SKIPPING (use -o to overwrite existing images)")
                
                # Remove image group from list
                groups.pop(img, None)
            print()

        print("-----------------------------------------\n")

        # Load and combine segments
        for img in groups.keys():
            # Get group details
            name, mode, chan, segment = parse_fname(groups[img][0])

            if args.s:
                for seg in groups[img]:
                    process_single_segment(seg)
                    print()
            else:
                process_group(name, mode, chan, groups[img])
                print("\n")
    else:
        # Load and process single file
        process_single_segment(args.INPUT)


def process_group(name, mode, chan, files):
    """
    Load data field of each segment and combine into one JPEG
    """

    print("Processing {}...".format(name))
    print("  Loading segments", end='')

    segmentDataFields = []

    # Load each segment from disk
    for seg in files:
        # Load file
        headerField, dataField = load_hrit(seg)

        # Skip encrypted files
        if parse_key_header(headerField):
            print("  SKIPPING ENCRYPTED LRIT FILES")
            return

        # Append data field to data field list
        segmentDataFields.append(dataField)
        print(".", end='')
        sys.stdout.flush()
    print()

    # Create new image
    finalResH, finalResV = get_image_resolution(mode, chan)
    outImage = Image.new("RGB", (finalResH, finalResV))

    # Process segments into images
    print("  Joining segments", end='')

    segmentCount = get_total_segments(mode)
    segmentVRes = int(finalResV / segmentCount)
    for i, seg in enumerate(segmentDataFields):
        # Create image object
        img = convert_to_img(files[i], seg)

        # Append image to output image
        vOffset = segmentVRes * i
        outImage.paste(img, (0, vOffset))

        print(".", end='')
        sys.stdout.flush()
    print()

    # Save output image to disk
    outFName = args.INPUT + "/" + name + ".jpg"
    outImage.save(outFName, format='JPEG', subsampling=0, quality=100)
    print("  Saved image: \"{}\"".format(outFName))


def process_single_segment(fpath):
    """
    Processes a single HRIT segment into an image
    """

    name, mode, chan, segment = parse_fname(fpath)
    print("Processing {}...".format(fpath))

    # Load file
    headerField, dataField = load_hrit(fpath)

    # Skip encrypted files
    if parse_key_header(headerField):
        print("  SKIPPING ENCRYPTED HRIT FILE")
        return
    
    img = convert_to_img(fpath, dataField)
    jpgName = fpath.replace(".hrit", "") + ".jpg"
    img.save(jpgName, format='JPEG', subsampling=0, quality=100)
    print("Saved: \"{}\"".format(jpgName))


def convert_to_img(fpath, dataField):
    """
        Converts J2K to Pillow Image object via PPM using libjpeg

        Arguments:
            fpath {string} -- Path for temporary files
            dataField {bytes} -- JPEG2000 image

        Returns:
            Pillow.Image -- Pillow Image object
        """

    # Save JP2 to disk
    jp2Name = fpath.replace(".hrit", "") + ".jp2"
    f = open(jp2Name, "wb")
    f.write(dataField)
    f.close()

    # Convert J2P to PPM
    ppmName = fpath.replace(".hrit", "") + ".ppm"
    subprocess.call(["tools\\jpeg.exe", jp2Name, ppmName], stdout=subprocess.DEVNULL)
    os.remove(jp2Name)
    
    # Load and convert 16-bit PPM to 8-bit image
    img = Image.open(ppmName)
    iarr = np.uint8(np.array(img) / 4)
    img = Image.fromarray(iarr)
    os.remove(ppmName)
    return img


def load_hrit(fpath):
    """
    Load HRIT file and return fields
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
    Parses HRIT primary header to get field lengths
    """

    #print("Parsing primary HRIT header...")

    primaryHeader = data[:16]

    # Header fields
    HEADER_TYPE = get_bits_int(primaryHeader, 0, 8, 128)               # Header Type (always 0x00)
    HEADER_LEN = get_bits_int(primaryHeader, 8, 16, 128)               # Header Length (always 0x10)
    FILE_TYPE = get_bits_int(primaryHeader, 24, 8, 128)                # File Type
    TOTAL_HEADER_LEN = get_bits_int(primaryHeader, 32, 32, 128)        # Total HRIT Header Length
    DATA_LEN = get_bits_int(primaryHeader, 64, 64, 128)                # Data Field Length

    #print("    Header Length: {} bytes".format(TOTAL_HEADER_LEN))
    #print("    Data Length: {} bits ({} bytes)".format(DATA_LEN, DATA_LEN/8))

    return TOTAL_HEADER_LEN, DATA_LEN


def parse_key_header(headerField):
    """
    Parses xRIT key header to get key index
    """

    #print("\nParsing xRIT key header...")

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
    Parse HRIT file name into components
    """

    fname = os.path.basename(fpath)
    
    split = fname.split("_")
    mode = split[1]
    chan = split[3]
    name = fpath.replace(args.ext, "")[:-3]
    name = "IMG_" + name.split("IMG_")[1]
    segment = int(split[6][:2])

    return name, mode, chan, segment


def get_total_segments(mode):
    """
    Returns the total number of segments in the given observation mode
    """

    if mode == "FD":
        totalSegments = 10
    else:
        totalSegments = None
    
    return totalSegments


def get_image_resolution(mode, chan):
    """
    Returns the horizontal and vertical resolution of the given observation mode and channel
    """

    if mode == "FD":
        if chan == "VI006":
            outH = 11000
            outV = 11000
        else:
            outH = 2750
            outV = 2750
    
    return outH, outV


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
