"""
xrit-rx.py
https://github.com/sam210723/xrit-rx

Receive images from geostationary weather satellites
"""

import argparse
import ast
import colorama
from collections import namedtuple
import configparser
import os
from   pathlib import Path
import requests
import socket
import struct
import time

from demuxer import Demuxer
import ccsds as CCSDS
from dash import Dashboard

class Main:
    def __init__(self):
        print("┌──────────────────────────────────────────────┐")
        print("│                   xrit-rx                    │")
        print("│         LRIT/HRIT Downlink Processor         │")
        print("├──────────────────────────────────────────────┤")
        print("│     @sam210723         vksdr.com/xrit-rx     │")
        print("└──────────────────────────────────────────────┘\n")

        # Set instance variables
        self.demuxer = None         # Demuxer class instance
        self.dashboard = None       # Dashboard class instance
        self.keys = None            # Encryption key list
        self.packet_file = None     # Packet input file
        self.dump_file = None       # Packet output file
        self.version = "1.4"        # Application version

        # Initialise Colorama
        colorama.init(autoreset=True)

        # Configure xrit-rx
        self.configure()

        # Setup input source
        self.setup_input()


    def configure(self):
        """
        Configures xrit-rx
        """

        # Get command line arguments
        argp = argparse.ArgumentParser()
        argp.add_argument("-v", "--verbose", action="store_true", help="Enable verbose console output (only useful for debugging)")
        argp.add_argument("--config", action="store", help="Path to configuration file (*.ini)", default="xrit-rx.ini")
        argp.add_argument("--file", action="store", help="Path to VCDU packet file")
        argp.add_argument("--dump", action="store", help="Write VCDU packets to file (only useful for debugging)")
        argp.add_argument("--no-exit", action="store_true", help="Pause main thread before exiting (only useful for debugging)")
        self.args = argp.parse_args()

        # Open input packet file
        if self.args.file:
            self.args.file = Path(self.args.file)

            # Check packet file exists
            if not self.args.file.is_file():
                self.log(f"PACKET FILE \"{self.args.file.absolute()}\" DOES NOT EXIST", style="error")
                self.stop(code=1)

            self.packet_file = open(self.args.file, "rb")

        # Open packet dump file
        if self.args.dump:
            dump_path = Path(self.args.dump)
            self.dump_file = open(dump_path, "wb+")

        # Change working directory to script location
        os.chdir(Path(__file__).parent.absolute())

        # Load configuration file
        config_path = Path(self.args.config)
        if config_path.is_file():
            confp = configparser.ConfigParser()
            confp.read(config_path)
            self.config = confp._sections
        else:
            self.log(f"CONFIGURATION FILE \"{self.args.config}\" DOES NOT EXIST", style="error")
            self.stop(code=1)
        
        # Create path objects
        self.config['rx']['keys'] = Path(self.config['rx']['keys'])
        self.config['rx']['mode'] = self.config['rx']['mode'].upper()
        self.config['output']['path'] = Path(self.config['output']['path']) / self.config['rx']['mode']
        self.config['output']['path'].mkdir(parents=True, exist_ok=True)

        # Parse boolean options
        self.config['output']['images'] = self.config['output']['images'] == "true"
        self.config['output']['xrit'] = self.config['output']['xrit'] == "true"
        self.config['dashboard']['enabled'] = self.config['dashboard']['enabled'] == "true"

        # Parse ignored channel list
        if self.config['output']['ignored']:
            self.config['output']['ignored'] = ast.literal_eval(self.config['output']['ignored'])
            if type(self.config['output']['ignored']) == int:
                self.config['output']['ignored'] = (self.config['output']['ignored'],)
        else:
            self.config['output']['ignored'] = ()
        ignored = ", ".join(f"{c} ({CCSDS.VCDU.get_VC(None, c)})" for c in self.config['output']['ignored'])

        # Limit dashboard refresh rate
        self.config['dashboard']['interval'] = round(float(self.config['dashboard']['interval']), 1)
        self.config['dashboard']['interval'] = max(1, self.config['dashboard']['interval'])

        # Information dictionary
        info = {
            "GK-2A": {
                "name": "GEO-KOMPSAT-2A (GK-2A)",
                "LRIT": [1692.14, "64 kbps"],
                "HRIT": [1695.4, "3 Mbps"]
            }
        }
        spacecraft = self.config['rx']['spacecraft']
        downlink = self.config['rx']['mode']

        # Check spacecraft is valid
        if spacecraft not in info:
            self.log(f"INVALID SPACECRAFT \"{spacecraft}\"", style="error")
            self.stop(code=1)
        
        # Check downlink is valid
        if downlink not in info[spacecraft]:
            self.log(f"INVALID DOWNLINK \"{downlink}\"", style="error")
            self.stop(code=1)
        
        # Check input type is valid
        if self.config['rx']['input'] not in ['goesrecv', 'osp', 'udp']:
            self.log(f"INVALID INPUT TYPE \"{self.config['rx']['input']}\"", style="error")
            self.stop(code=1)
        
        # Get dashboard URL
        ip = socket.gethostbyname(socket.gethostname())
        dashboard_url = f"https://{ip}:{self.config['dashboard']['port']}"

        # Get input path
        if not self.args.file:
            input_path =  f"{self.config['rx']['input']}"
            input_path += f" ({self.config[self.config['rx']['input']]['ip']}:{self.config[self.config['rx']['input']]['port']})"
        else:
            input_path = self.args.file.name
            self.config['rx']['input'] = "file"
        
        # Print configuration info
        self.log(f"SPACECRAFT:   {info[spacecraft]['name'] if spacecraft in info else spacecraft}")
        self.log(f"DOWNLINK:     {downlink.upper()} ({info[spacecraft][downlink][0]} MHz, {info[spacecraft][downlink][1]})")
        self.log(f"INPUT:        {input_path}")
        self.log(f"OUTPUT:       {self.config['output']['path'].absolute()}")
        self.log(f"KEY FILE:     {self.config['rx']['keys'].name}")
        self.log(f"IGNORED:      {ignored if ignored else 'None'}")
        self.log(f"DASHBOARD:    {dashboard_url if self.config['dashboard']['enabled'] else 'DISABLED'}")
        self.log(f"VERSION:      v{self.version}\n")

        # Load encryption keys
        self.keys = self.load_keys(self.config['rx']['keys'])

        # Dump file status
        self.log(f"WRITING PACKETS TO \"{dump_path.absolute()}\"", style="ok")

        # Check for new version on GitHub
        try:
            r = requests.get("https://api.github.com/repos/sam210723/xrit-rx/releases/latest")
            if r.status_code == 200:
                latest_tag = r.json()['tag_name']
                if f"v{self.version}" != latest_tag:
                    self.log(f"\nA new version of xrit-rx is available on GitHub", style="ok")
                    self.log("https://github.com/sam210723/xrit-rx/releases/latest", style="ok")
        except Exception: pass


    def load_keys(self, path):
        """
        Loads encryption keys from key file
        """

        # Check key file exists
        if not path.is_file():
            # Only output encrypted xRIT files
            self.config['output']['images'] = False
            self.config['output']['xrit'] = True

            self.log(f"KEY FILE \"{path.absolute()}\" DOES NOT EXIST", style="error")
            self.log(f"ENCRYPTED XRIT FILES WILL BE SAVED TO DISK\n", style="error")
            return {}
        
        # Load key file
        key_file = open(path, "rb")

        # Get number of keys
        key_count = int.from_bytes(key_file.read(2), byteorder="big")

        # Loop through keys
        keys = {}
        for _ in range(key_count):
            # Get key index and key value
            key = struct.unpack(">2s8s", key_file.read(10))

            # Add key to dict
            keys[key[0]] = key[1]

        key_file.close()
        self.log("DECRYPTION KEYS LOADED", style="ok")
        return keys


    def setup_input(self):
        """
        Sets up the selected input source
        """

        if self.config['rx']['input'] == "goesrecv":
            # Create socket and address
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            addr = (self.config['goesrecv']['ip'], int(self.config['goesrecv']['port']))

            # Connect socket
            print(f"Connecting to {addr[0]}:{addr[1]}...", end='', flush=True)
            self.connect_socket(self.socket, addr)

            # Setup nanomsg published in goesrecv
            self.socket.send(b'\x00\x53\x50\x00\x00\x21\x00\x00')
            if self.socket.recv(8) != b'\x00\x53\x50\x00\x00\x20\x00\x00':
                self.log("ERROR CONFIGURING NANOMSG", style="error")
                self.stop(code=1)

        elif self.config['rx']['input'] == "osp":
            # Create socket and address
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            addr = (self.config['osp']['ip'], int(self.config['osp']['port']))

            # Connect socket
            print(f"Connecting to {addr[0]}:{addr[1]}...", end='', flush=True)
            self.connect_socket(self.socket, addr)

        elif self.config['rx']['input'] == "udp":
            # Create socket and address
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            addr = (self.config['udp']['ip'], int(self.config['udp']['port']))

            # Bind socket
            print(f"Binding UDP socket to {addr[0]}:{addr[1]}...", end='', flush=True)
            try:
                self.socket.bind(addr)
                self.log("SUCCESS", style="ok")
            except socket.error as e:
                self.log("FAILED", style="error")
                self.log(e)
                self.stop(code=1)


    def connect_socket(self, s, addr):
        """
        Connect a socket and handle exceptions
        """

        try:
            s.connect(addr)
            self.log("CONNECTED", style="ok")
        except socket.error as e:
            if e.errno == 10061: self.log("CONNECTION REFUSED", style="error")
            self.log(e)
            self.stop(code=1)


    def start(self):
        """
        Starts xrit-rx components
        """

        # Create demuxer instance
        demux_config = namedtuple('demux_config', 'spacecraft downlink verbose dump output images xrit blacklist keys')
        self.demuxer = Demuxer(
            demux_config(
                self.config['rx']['spacecraft'],
                self.config['rx']['mode'],
                self.args.verbose,
                self.dump_file,
                self.config['output']['path'],
                self.config['output']['images'],
                self.config['output']['xrit'],
                self.config['output']['ignored'],
                self.keys
            )
        )
        #TODO: Remove configuration tuple

        # Create dashboard instance
        dash_config = namedtuple('dash_config', 'port interval spacecraft downlink output images xrit blacklist version')
        self.dashboard = Dashboard(
            dash_config(
                self.config['dashboard']['port'],
                self.config['dashboard']['interval'],
                self.config['rx']['spacecraft'],
                self.config['rx']['mode'],
                self.config['output']['path'],
                self.config['output']['images'],
                self.config['output']['xrit'],
                self.config['output']['ignored'],
                self.version
            ),
            self.demuxer
        )
        #TODO: Remove configuration tuple

        # Check demuxer thread is ready
        if not self.demuxer.core_ready:
            self.log("DEMUXER CORE THREAD FAILED TO START", style="error")
            self.stop(code=1)

        print("───────────────────────────────────────────────────────────────\n")

        # Get processing start time
        self.start_time = time.time()

        # Enter main loop
        self.loop()


    def loop(self):
        """
        Handles data from the selected input source
        """

        # Packet length (VCDU)
        buflen = 892

        while True:
            if self.config['rx']['input'] == "goesrecv":
                # Get packet from goesrecv
                try:
                    data = self.socket.recv(buflen + 8)
                except ConnectionResetError:
                    self.log("LOST CONNECTION TO GOESRECV", style="error")
                    self.stop(code=1)

                # Push packet to demuxer
                if len(data) == buflen + 8: self.demuxer.push(data[8:])
            
            elif self.config['rx']['input'] == "osp":
                # Get packet from Open Satellite Project
                try:
                    data = self.socket.recv(buflen)
                except ConnectionResetError:
                    self.log("LOST CONNECTION TO OPEN SATELLITE PROJECT", style="error")
                    self.stop(code=1)

                # Push packet to demuxer
                if len(data) == buflen: self.demuxer.push(data)

            elif self.config['rx']['input'] == "udp":
                try:
                    data, _ = self.socket.recvfrom(buflen)
                except Exception as e:
                    self.log(e, style="error")
                    self.stop(code=1)
                
                # Push packet to demuxer
                if len(data) == buflen: self.demuxer.push(data)

            elif self.config['rx']['input'] == "file":
                if not self.packet_file.closed:
                    # Read packet from file
                    data = self.packet_file.read(buflen)

                    # No more data to read from file
                    if data == b'':
                        self.packet_file.close()
                        
                        # Append single fill VCDU (VCID 63)
                        # Triggers TP_File processing inside channel handlers
                        # by changing the currently active VCID
                        self.demuxer.push(b'\x70\xFF\x00\x00\x00\x00')
                        continue
                    
                    # Push packet to demuxer
                    self.demuxer.push(data)
                else:
                    # Demuxer has all packets from file in its queue
                    # Wait for processing to finish
                    if self.demuxer.complete():
                        run_time = round(time.time() - self.start_time, 3)
                        self.log(f"\nPROCESSED FILE IN {run_time:.03f}s", style="ok")
                        self.stop()
                    else:
                        # Limit loop speed when waiting for demuxer to finish processing
                        time.sleep(0.5)


    def stop(self, msg=True, code=0):
        """
        Stops xrit-rx gracefully
        """

        # Close dump file
        if self.dump_file: self.dump_file.close()

        # Keep running until keyboard interrupt
        if self.args.no_exit:
            self.log("PAUSING MAIN THREAD (--no-exit)", style="ok")
            try:
                while True: time.sleep(0.5)
            except KeyboardInterrupt: pass
        
        # Stop child threads
        if self.demuxer: self.demuxer.stop()
        if self.dashboard: self.dashboard.stop()

        # Show message and exit
        if msg: self.log("Exiting...")
        exit(code)


    def log(self, msg, style="none"):
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



# Initialise xrit-rx
instance = Main()
try:
    # Start xrit-rx
    instance.start()
except KeyboardInterrupt:
    # Exit on keyboard interrupt
    instance.stop()
