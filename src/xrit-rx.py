"""
xrit-rx.py
https://github.com/sam210723/xrit-rx

Frontend for CCSDS demultiplexer and image generator
"""

import ast
from argparse import ArgumentParser
from collections import namedtuple
import colorama
from colorama import Fore, Back, Style
from configparser import ConfigParser, NoOptionError, NoSectionError
from os import mkdir, path
import socket
from time import time, sleep

from demuxer import Demuxer
import ccsds as CCSDS
from dash import Dashboard

# Colorama styles
STYLE_ERR = f"{Fore.WHITE}{Back.RED}{Style.BRIGHT}"
STYLE_OK  = f"{Fore.GREEN}{Style.BRIGHT}"

# Globals
args = None             # Parsed CLI arguments
config = None           # Config parser object
start_time = None       # Processing start time
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
sck = None              # TCP/UDP socket object
buflen = 892            # Input buffer length (1 VCDU)
demux = None            # Demuxer class object
dash = None             # Dashboard class object
dashe = None            # Dashboard enabled flag
dashp = None            # Dashboard HTTP port
dashi = None            # Dashboard refresh interval (sec)
ver = "1.3.1+dev"       # xrit-rx version


def init():
    print("┌──────────────────────────────────────────────┐")
    print("│                   xrit-rx                    │")
    print("│         LRIT/HRIT Downlink Processor         │")
    print("├──────────────────────────────────────────────┤")
    print("│     @sam210723         vksdr.com/xrit-rx     │")
    print("└──────────────────────────────────────────────┘\n")
    
    global args
    global config
    global start_time
    global output
    global demux
    global dash

    # Initialise Colorama
    colorama.init(autoreset=True)

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
    demux_config = namedtuple('demux_config', 'spacecraft downlink verbose dump output images xrit blacklist keys')
    output += "/" + downlink + "/"
    demux = Demuxer(
        demux_config(
            spacecraft,
            downlink,
            args.v,
            args.dump,
            output,
            output_images,
            output_xrit,
            blacklist,
            keys
        )
    )

    # Start dashboard server
    if dashe:
        dash_config = namedtuple('dash_config', 'port interval spacecraft downlink output images xrit blacklist version')
        dash = Dashboard(
            dash_config(
                dashp,
                dashi,
                spacecraft,
                downlink,
                output,
                output_images,
                output_xrit,
                blacklist,
                ver
            ),
            demux
        )

    # Check demuxer thread is ready
    if not demux.core_ready:
        print(f"{STYLE_ERR}DEMUXER CORE THREAD FAILED TO START")
        safe_stop()

    print("──────────────────────────────────────────────────────────────────────────────────\n")

    # Get processing start time
    start_time = time()

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
                print(Fore.WHITE + Back.RED + Style.BRIGHT + "LOST CONNECTION TO GOESRECV")
                safe_stop()

            if len(data) == buflen + 8:
                demux.push(data[8:])
        
        elif source == "OSP":
            try:
                data = sck.recv(buflen)
            except ConnectionResetError:
                print(Fore.WHITE + Back.RED + Style.BRIGHT + "LOST CONNECTION TO OPEN SATELLITE PROJECT")
                safe_stop()
            
            demux.push(data)
        
        elif source == "UDP":
            try:
                data, address = sck.recvfrom(buflen)
            except Exception as e:
                print(e)
                safe_stop()
            
            demux.push(data)

        elif source == "FILE":
            global packetf
            global start_time

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
                    run_time = round(time() - start_time, 3)
                    print(f"\nPROCESSED FILE IN {run_time:.03f}s")
                    safe_stop()
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
    
    elif source == "UDP":
        sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        ip = config.get('udp', 'ip')
        port = int(config.get('udp', 'vchan'))
        addr = (ip, port)
        
        print("Binding UDP socket ({}:{})...".format(ip, port), end='')
        try:
            sck.bind(addr)
            print(Fore.GREEN + Style.BRIGHT + "SUCCESS")
        except socket.error as e:
            print(Fore.WHITE + Back.RED + Style.BRIGHT + "FAILED")
            print(e)
            safe_stop()

    elif source == "FILE":
        global packetf

        # Check VCDU file exists
        if not path.exists(args.file):
            print(Fore.WHITE + Back.RED + Style.BRIGHT + "INPUT FILE DOES NOT EXIST")
            safe_stop()
        
        packetf = open(args.file, 'rb')
        print(Fore.GREEN + Style.BRIGHT + "OPENED PACKET FILE")

    else:
        print(Fore.WHITE + Back.RED + Style.BRIGHT + "UNKNOWN INPUT MODE: \"{}\"".format(source))
        safe_stop()


def connect_socket(addr):
    """
    Connects TCP socket to address and handle exceptions
    """

    try:
        sck.connect(addr)
        print(Fore.GREEN + Style.BRIGHT + "CONNECTED")
    except socket.error as e:
        if e.errno == 10061:
            print(Fore.WHITE + Back.RED + Style.BRIGHT + "CONNECTION REFUSED")
        else:
            print(e)
    
        safe_stop()


def nanomsg_init():
    """
    Sets up nanomsg publisher in goesrecv to send VCDUs over TCP
    """

    global sck

    sck.send(b'\x00\x53\x50\x00\x00\x21\x00\x00')
    nmres = sck.recv(8)

    # Check nanomsg response
    if nmres != b'\x00\x53\x50\x00\x00\x20\x00\x00':
        print(Fore.WHITE + Back.RED + Style.BRIGHT + "  ERROR CONFIGURING NANOMSG (BAD RESPONSE)")
        safe_stop()


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
        except OSError as e:
            print(Fore.WHITE + Back.RED + Style.BRIGHT + "ERROR CREATING OUTPUT FOLDERS\n{}".format(e))
            safe_stop()
    
    if not path.isdir(absp + "/" + downlink + "/"):
        try:
            mkdir(absp + "/" + downlink + "/")

            print(Fore.GREEN + Style.BRIGHT + "CREATED OUTPUT FOLDERS")
        except OSError as e:
            print(Fore.WHITE + Back.RED + Style.BRIGHT + "ERROR CREATING OUTPUT FOLDERS\n{}".format(e))
            safe_stop()


def load_keys():
    """
    Loads key file and parses keys
    """

    global keypath
    global keys
    global output_images
    global output_xrit

    # Check key file exists
    if not path.exists(keypath):
        print(Fore.WHITE + Back.RED + Style.BRIGHT + "KEY FILE NOT FOUND: ONLY ENCRYPTED XRIT FILES WILL BE SAVED")
        
        # Only output xRIT files
        output_images = False
        output_xrit = True
        
        return False

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

    print(Fore.GREEN + Style.BRIGHT + "DECRYPTION KEYS LOADED")
    return True


def parse_args():
    """
    Parses command line arguments
    """
    
    argp = ArgumentParser()
    argp.add_argument("--config", action="store", help="Configuration file path (.ini)", default="xrit-rx.ini")
    argp.add_argument("--file", action="store", help="Path to VCDU packet file", default=None)
    argp.add_argument("-v", action="store_true", help="Enable verbose console output (only useful for debugging)", default=False)
    argp.add_argument("--dump", action="store", help="Dump VCDUs (except fill) to file (only useful for debugging)", default=None)
    argp.add_argument("--no-exit", action="store_true", help="Pause main thread before exiting (only useful for debugging)", default=False)

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
    global dashe
    global dashp
    global dashi

    cfgp = ConfigParser()
    cfgp.read(path)

    if args.file == None:
        source = cfgp.get('rx', 'input').upper()
    else:
        source = "FILE"
    
    try:
        spacecraft = cfgp.get('rx', 'spacecraft').upper()
        downlink = cfgp.get('rx', 'mode').upper()
        output = cfgp.get('output', 'path')
        output_images = cfgp.getboolean('output', 'images')
        output_xrit = cfgp.getboolean('output', 'xrit')
        bl = cfgp.get('output', 'channel_blacklist')
        keypath = cfgp.get('rx', 'keys')
        dashe = cfgp.getboolean('dashboard', 'enabled')
        dashp = cfgp.get('dashboard', 'port')
        dashi = round((float(cfgp.get('dashboard', 'interval'))), 1)
    except (NoSectionError, NoOptionError) as e:
        print(Fore.WHITE + Back.RED + Style.BRIGHT + "ERROR PARSING CONFIG FILE: " + str(e).upper())
        safe_stop()

    # Limit dashboard refresh interval
    if dashi < 1: dashi = 1

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

    print("SPACECRAFT:       {}".format(spacecraft))

    #FIXME
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
    
    if dashe:
        ip = socket.gethostbyname(socket.gethostname())
        print("DASHBOARD:        http://{}:{}".format(ip, dashp))
    else:
        print("DASHBOARD:        DISABLED")
    
    print("VERSION:          {}\n".format(ver))
    
    if args.dump:
        print(Fore.GREEN + Style.BRIGHT + "WRITING PACKETS TO: \"{}\"".format(args.dump))


def safe_stop(message=True):
    """
    Safely kill threads and exit
    """

    # Pause main thread if --no-exit is set
    if args.no_exit:
        print("PAUSING MAIN THREAD (--no-exit)")
        
        try:
            while True:
                sleep(0.5)
        except KeyboardInterrupt:
            pass
    
    # Stop child threads
    if demux != None: demux.stop()
    if dash != None: dash.stop()

    if message: print("\nExiting...")
    exit()


try:
    init()
except KeyboardInterrupt:
    safe_stop()
