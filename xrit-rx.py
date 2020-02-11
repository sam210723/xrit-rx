"""
xrit-rx.py
https://github.com/sam210723/xrit-rx

Frontend for CCSDS demultiplexer and image generator
"""

import ast
from argparse import ArgumentParser
from collections import namedtuple
from configparser import ConfigParser
from os import mkdir, path
import socket
from time import time, sleep

from demuxer import Demuxer
import ccsds as CCSDS


# Globals
args = None             # Parsed CLI arguments
config = None           # Config parser object
stime = None            # Processing start time
source = None           # Input source type
spacecraft = None       # Spacecraft name
downlink = None         # Downlink type (LRIT/HRIT)
output = None           # Output path root
output_images = None    # Flag for saving Images to disk
output_xrit = None      # Flag for saving xRIT files to disk
blacklist = []          # VCID blacklist
packetf = None          # Packet file object
keypath = None          # Decryption key file path
keys = {}               # Decryption keys
sck = None              # TCP socket object
buflen = 892            # Input buffer length (1 VCDU)
demux = None            # Demuxer class object
ver = "1.0.3"           # xrit-rx version


def init():
    print("┌──────────────────────────────────────────────┐")
    print("│                   xrit-rx                    │")
    print("│         LRIT/HRIT Downlink Processor         │")
    print("├──────────────────────────────────────────────┤")
    print("│     @sam210723         vksdr.com/xrit-rx     │")
    print("└──────────────────────────────────────────────┘\n")
    
    global args
    global config
    global stime
    global downlink
    global output
    global blacklist
    global demux
    global keys

    # Handle arguments and config file
    args = parse_args()
    config = parse_config(args.config)
    print_config()

    # Configure directories and input source
    dirs()
    config_input()

    # Load decryption keys
    load_keys()

    # Create demuxer instance
    dcfg = namedtuple('dcfg', 'spacecraft downlink verbose dump output images xrit blacklist keys')
    output += "/" + downlink + "/"
    demux = Demuxer(dcfg(spacecraft, downlink, args.v, args.dump, output, output_images, output_xrit, blacklist, keys))

    # Check demuxer thread is ready
    if not demux.coreReady:
        print("DEMUXER CORE THREAD FAILED TO START\nExiting...")
        exit()

    print("──────────────────────────────────────────────────────────────────────────────────\n")

    # Get processing start time
    stime = time()

    # Enter main loop
    loop()


def loop():
    """
    Handles data from the selected input source
    """
    global demux
    global source
    global sck
    global buflen

    while True:
        if source == "GOESRECV":
            try:
                data = sck.recv(buflen + 8)
            except ConnectionResetError:
                print("LOST CONNECTION TO GOESRECV\nExiting...")
                demux.stop()
                exit()

            if len(data) == buflen + 8:
                demux.push(data[8:])
        
        elif source == "OSP":
            try:
                data = sck.recv(buflen)
            except ConnectionResetError:
                print("LOST CONNECTION TO OPEN SATELLITE PROJECT\nExiting...")
                demux.stop()
                exit()
            
            demux.push(data)

        elif source == "FILE":
            global packetf
            global stime

            if not packetf.closed:
                # Read VCDU from file
                data = packetf.read(buflen)

                # No more data to read from file
                if data == b'':
                    #print("INPUT FILE LOADED")
                    packetf.close()

                    # Append single fill VCDU (VCID 63)
                    # Triggers TP_File processing inside channel handlers
                    demux.push(b'\x70\xFF\x00\x00\x00\x00')

                    continue
                
                # Push VCDU to demuxer
                demux.push(data)
            else:
                # Demuxer has all VCDUs from file, wait for processing
                if demux.complete():
                    runTime = round(time() - stime, 3)
                    print("\nFINISHED PROCESSING FILE ({}s)\nExiting...".format(runTime))
                    
                    # Stop core thread
                    demux.stop()
                    exit()
                else:
                    # Limit loop speed when waiting for demuxer to finish processing
                    sleep(0.5)


def config_input():
    """
    Configures the selected input source
    """

    global source
    global sck

    if source == "GOESRECV":
        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ip = config.get('goesrecv', 'ip')
        port = int(config.get('goesrecv', 'vchan'))
        addr = (ip, port)

        print("Connecting to goesrecv ({})...".format(ip), end='')
        connect_socket(addr)
        nanomsg_init()
    
    elif source == "OSP":
        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ip = config.get('osp', 'ip')
        port = int(config.get('osp', 'vchan'))
        addr = (ip, port)

        print("Connecting to Open Satellite Project ({})...".format(ip), end='')
        connect_socket(addr)

    elif source == "FILE":
        global packetf

        # Check VCDU file exists
        if not path.exists(args.file):
            print("INPUT FILE DOES NOT EXIST\nExiting...")
            exit()
        
        packetf = open(args.file, 'rb')
        print("Opened input file: \"{}\"".format(args.file))

    else:
        print("UNKNOWN INPUT MODE: \"{}\"".format(source))
        print("Exiting...")
        exit()


def connect_socket(addr):
    """
    Connects TCP socket to address and handle exceptions
    """

    try:
        sck.connect(addr)
        print("CONNECTED")
    except socket.error as e:
        if e.errno == 10061:
            print("CONNECTION REFUSED")
        else:
            print(e)
    
        print("\nExiting...")
        exit()


def nanomsg_init():
    """
    Sets up nanomsg publisher in goesrecv to send VCDUs over TCP
    """

    global sck

    sck.send(b'\x00\x53\x50\x00\x00\x21\x00\x00')
    nmres = sck.recv(8)

    # Check nanomsg response
    if nmres != b'\x00\x53\x50\x00\x00\x20\x00\x00':
        print("  ERROR CONFIGURING NANOMSG (BAD RESPONSE)\n  Exiting...\n")
        exit()


def dirs():
    """
    Configures directories for demuxed files
    """

    global downlink
    global output

    absp = path.abspath(output)
    
    # Create output directory if it doesn't exist already
    if not path.isdir(absp):
        try:
            mkdir(absp)
            mkdir(absp + "/" + downlink + "/")

            print("Created output folders")
        except OSError as e:
            print("Error creating output folders\n{}\n\nExiting...".format(e))
            exit()


def load_keys():
    """
    Loads key file and parses keys
    """

    global keypath
    global keys

    # Check key file exists
    if not path.exists(keypath):
        print("KEY FILE NOT FOUND (will output encrypted files)")
        return

    # Load key file
    keyf = open(keypath, mode='rb')
    fbytes = keyf.read()

    # Parse key count
    count = int.from_bytes(fbytes[:2], byteorder='big')

    # Parse keys
    for i in range(count):
        offset = (i * 10) + 2
        index = fbytes[offset : offset + 2]
        key = fbytes[offset + 2 : offset + 10]

        '''
        # Print keys
        i = hex(int.from_bytes(index, byteorder='big')).upper()[2:]
        k = hex(int.from_bytes(key, byteorder='big')).upper()[2:]
        print("{}: {}".format(i, k))
        '''

        # Add key to dictionary
        keys[index] = key

    print("Decryption keys loaded")


def parse_args():
    """
    Parses command line arguments
    """
    
    argp = ArgumentParser()
    argp.description = "Frontend for CCSDS demultiplexer"
    argp.add_argument("--config", action="store", help="Configuration file path (.ini)", default="xrit-rx.ini")
    argp.add_argument("--file", action="store", help="Path to VCDU packet file", default=None)
    argp.add_argument("-v", action="store_true", help="Enable verbose console output (only useful for debugging)", default=False)
    argp.add_argument("--dump", action="store", help="Dump VCDUs (except fill) to file (only useful for debugging)", default=None)

    return argp.parse_args()


def parse_config(path):
    """
    Parses configuration file
    """

    global source
    global spacecraft
    global downlink
    global output
    global output_images
    global output_xrit
    global blacklist
    global keypath

    cfgp = ConfigParser()
    cfgp.read(path)

    if args.file == None:
        source = cfgp.get('rx', 'input').upper()
    else:
        source = "FILE"
    
    spacecraft = cfgp.get('rx', 'spacecraft').upper()
    downlink = cfgp.get('rx', 'mode').upper()
    output = cfgp.get('output', 'path')
    output_images = cfgp.getboolean('output', 'images')
    output_xrit = cfgp.getboolean('output', 'xrit')
    bl = cfgp.get('output', 'channel_blacklist')
    keypath = cfgp.get('rx', 'keys')

    # If VCID blacklist is not empty
    if bl != "":
        # Parse blacklist string into int or list
        blacklist = ast.literal_eval(bl)

        # If parsed into int, wrap int in list
        if type(blacklist) == int: blacklist = [blacklist]

    return cfgp


def print_config():
    """
    Prints configuration information
    """

    global spacecraft
    global downlink
    global output
    global keypath

    print("SPACECRAFT:       {}".format(spacecraft))

    if downlink == "LRIT":
        rate = "64 kbps"
    elif downlink == "HRIT":
        rate = "3 Mbps"
    print("DOWNLINK:         {} ({})".format(downlink, rate))

    if source == "GOESRECV":
        s = "goesrecv (github.com/sam210723/goestools)"
    elif source == "OSP":
        s = "Open Satellite Project (github.com/opensatelliteproject/xritdemod)"
    elif source == "FILE":
        s = "File ({})".format(args.file)
    else:
        s = "UNKNOWN"

    print("INPUT SOURCE:     {}".format(s))
    
    absp = path.abspath(output)
    absp = absp[0].upper() + absp[1:]  # Fix lowercase drive letter
    print("OUTPUT PATH:      {}".format(absp))

    if (len(blacklist) == 0):
        print("IGNORED VCIDs:    None")
    else:
        blacklist_str = ""
        for i, c in enumerate(blacklist):
            if i > 0: blacklist_str += ", "
            blacklist_str += "{} ({})".format(c, CCSDS.VCDU.get_VC(None, int(c)))
        
        print("IGNORED VCIDs:    {}".format(blacklist_str))
    
    print("KEY FILE:         {}".format(keypath))
    print("VERSION:          {}\n".format(ver))


try:
    init()
except KeyboardInterrupt:
    demux.stop()
    print("Exiting...")
    exit()
