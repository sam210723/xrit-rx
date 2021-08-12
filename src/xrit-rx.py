"""
xrit-rx.py
https://github.com/sam210723/xrit-rx

Receive images from geostationary weather satellites
"""

import argparse
import colorama
from   collections import namedtuple
import configparser
import os
from   pathlib import Path
import requests
import socket
import struct
import time

from   demuxer import Demuxer
import ccsds as CCSDS
from   dash import Dashboard


class Main:
    def __init__(self):
        print("┌──────────────────────────────────────────────┐\n"
              "│                   xrit-rx                    │\n"
              "│         LRIT/HRIT Downlink Processor         │\n"
              "├──────────────────────────────────────────────┤\n"
              "│     @sam210723         vksdr.com/xrit-rx     │\n"
              "└──────────────────────────────────────────────┘\n")

        # Set instance variables
        self.demuxer = None         # Demuxer class instance
        self.dashboard = None       # Dashboard class instance
        self.keys = None            # Encryption key list
        self.packet_file = None     # Packet input file
        self.dump_file = None       # Packet output file
        self.version = "1.4"        # Application version

        # Initialise Colorama
        colorama.init(autoreset=True)

        # Information dictionary
        self.satellites = {
            "GK-2A": {
                "name": "GEO-KOMPSAT-2A (GK-2A)",
                "LRIT": [1692.14, "64 kbps", 64e3],
                "HRIT": [1695.4,   "3 Mbps",  3e6],
                "SCID": 195,
                "VCID": {
                     0: "FULL DISK",
                     4: "ALPHA-NUMERIC TEXT",
                     5: "ADDITIONAL DATA",
                    63: "IDLE"
                }
            }
        }

        # Configure xrit-rx
        self.configure()

        # Setup input source
        self.setup_input()


    def configure(self):
        """
        Configures xrit-rx (args, input file, output file, cwd, config file, keys, updates)
        """

        # Get command line arguments
        argp = argparse.ArgumentParser()
        argp.add_argument("-v", "--verbose", action="store_true", help="Enable verbose console output (only useful for debugging)")
        argp.add_argument("--config",        action="store",      help="Path to configuration file (*.ini)", default="xrit-rx.ini")
        argp.add_argument("--file",          action="store",      help="Path to VCDU packet file")
        argp.add_argument("--dump",          action="store",      help="Write VCDU packets to file (only useful for debugging)")
        argp.add_argument("--no-exit",       action="store_true", help="Pause main thread before exiting (only useful for debugging)")
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
            self.args.dump = Path(self.args.dump)
            
            try:
                self.dump_file = open(self.args.dump, "wb+")
            except OSError as e:
                self.log(f"UNABLE TO OPEN PACKET DUMP FILE\"{self.args.dump.absolute()}\"", style="error")
                self.stop(code=1)

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
        self.config['output']['enhance'] = self.config['output']['enhance'] == "true"
        self.config['dashboard']['enabled'] = self.config['dashboard']['enabled'] == "true"

        # Parse ignored channel list
        if self.config['output']['ignored']:
            self.config['output']['ignored'] = self.config['output']['ignored'].split(',')
            self.config['output']['ignored'] = [int(c) for c in self.config['output']['ignored']]
            self.config['output']['ignored'] = set(self.config['output']['ignored'])
        else:
            self.config['output']['ignored'] = set()

        # Create ignored VCID string
        spacecraft = self.config['rx']['spacecraft']
        ignored = ", ".join(f"{c} ({self.satellites[spacecraft]['VCID'][c]})" for c in self.config['output']['ignored'])

        # Limit dashboard refresh rate
        self.config['dashboard']['interval'] = round(float(self.config['dashboard']['interval']), 1)
        self.config['dashboard']['interval'] = max(1, self.config['dashboard']['interval'])

        # Check spacecraft is valid
        if spacecraft not in self.satellites:
            self.log(f"INVALID SPACECRAFT \"{spacecraft}\"", style="error")
            self.stop(code=1)
        
        # Check downlink is valid
        downlink = self.config['rx']['mode']
        if downlink not in self.satellites[spacecraft]:
            self.log(f"INVALID DOWNLINK \"{downlink}\"", style="error")
            self.stop(code=1)
        
        # Check input type is valid
        if self.config['rx']['input'] not in ['nng', 'tcp', 'udp']:
            self.log(f"INVALID INPUT TYPE \"{self.config['rx']['input']}\"", style="error")
            self.stop(code=1)
        
        # Get dashboard URL
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            s.close()
        except socket.error:
            ip = "127.0.0.1"
        dashboard_url = f"http://{ip}:{self.config['dashboard']['port']}"

        # Get input path
        if not self.args.file:
            input_path =  f"{self.config['rx']['input']}"
            input_path += f" ({self.config[self.config['rx']['input']]['ip']}:{self.config[self.config['rx']['input']]['port']})"
        else:
            input_path = self.args.file.name
            self.config['rx']['input'] = "file"
        
        # Print configuration info
        self.log(f"SPACECRAFT:   {self.satellites[spacecraft]['name'] if spacecraft in self.satellites else spacecraft}")
        self.log(f"DOWNLINK:     {downlink.upper()} ({self.satellites[spacecraft][downlink][0]} MHz, {self.satellites[spacecraft][downlink][1]})")
        self.log(f"INPUT:        {input_path}")
        self.log(f"OUTPUT:       {self.config['output']['path'].absolute()}")
        self.log(f"KEY FILE:     {self.config['rx']['keys'].name}")
        self.log(f"IGNORED:      {ignored if len(ignored) > 0 else 'None'}")
        self.log(f"DASHBOARD:    {dashboard_url if self.config['dashboard']['enabled'] else 'DISABLED'}")
        self.log(f"VERSION:      v{self.version}\n")

        # Load encryption keys
        self.keys = self.load_keys(self.config['rx']['keys'])

        # Dump file status
        if self.args.dump: self.log(f"WRITING PACKETS TO \"{self.args.dump.absolute()}\"", style="ok")

        # Check for new version on GitHub
        try:
            r = requests.get("https://api.github.com/repos/sam210723/xrit-rx/releases/latest")
            if r.status_code == 200:
                latest_tag = r.json()['tag_name']
                if f"v{self.version}" != latest_tag:
                    self.log(f"\nA new version of xrit-rx is available on GitHub", style="ok")
                    self.log("https://github.com/sam210723/xrit-rx/releases/latest\n", style="ok")
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
            self.log(f"Encrypted xRIT files will be saved to disk", style="error")
            self.log(f"See https://vksdr.com/xrit-rx#keys for more information\n", style="error")
            return {}
        
        # Load key file
        key_file = open(path, "rb")

        # Get number of keys
        key_count = int.from_bytes(key_file.read(2), byteorder="big")

        # Loop through keys
        keys = {}
        for _ in range(key_count):
            # Get key index and key value
            key = struct.unpack(">H8s", key_file.read(10))

            # Add key to dict
            keys[key[0]] = key[1]

        key_file.close()
        self.log("DECRYPTION KEYS LOADED", style="ok")
        return keys


    def setup_input(self):
        """
        Sets up the selected input source
        """

        if self.config['rx']['input'] == "nng":
            # Create socket and address
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            addr = (self.config['nng']['ip'], int(self.config['nng']['port']))

            # Connect socket
            print(f"Connecting to {addr[0]}:{addr[1]}...", end='', flush=True)
            self.connect_socket(self.socket, addr)

            # Setup nanomsg publisher in goesrecv
            self.socket.send(b'\x00\x53\x50\x00\x00\x21\x00\x00')
            if self.socket.recv(8) != b'\x00\x53\x50\x00\x00\x20\x00\x00':
                self.log("ERROR CONFIGURING NANOMSG", style="error")
                self.stop(code=1)

        elif self.config['rx']['input'] == "tcp":
            # Create socket and address
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            addr = (self.config['tcp']['ip'], int(self.config['tcp']['port']))

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
        demux_config = namedtuple('demux_config', 'spacecraft downlink verbose dump output images xrit enhance ignored keys satellite')
        self.demuxer = Demuxer(
            demux_config(
                self.config['rx']['spacecraft'],
                self.config['rx']['mode'],
                self.args.verbose,
                self.dump_file,
                self.config['output']['path'],
                self.config['output']['images'],
                self.config['output']['xrit'],
                self.config['output']['enhance'],
                self.config['output']['ignored'],
                self.keys,
                self.satellites[self.config['rx']['spacecraft']]
            )
        )

        # Create dashboard instance
        if self.config['dashboard']['enabled']:
            dash_config = namedtuple('dash_config', 'port interval spacecraft downlink output images xrit ignored version')
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

        # Packet length (1 VCDU)
        buflen = 892

        while True:
            if self.config['rx']['input'] == "nng":
                # Get packet from nanomsg source
                try:
                    data = self.socket.recv(buflen + 8)
                except ConnectionResetError:
                    self.log("LOST CONNECTION TO NANOMSG SOURCE", style="error")
                    self.stop(code=1)

                # Push packet to demuxer
                if len(data) == buflen + 8: self.demuxer.push(data[8:])
            
            elif self.config['rx']['input'] == "tcp":
                # Get packet from TCP source
                try:
                    data = self.socket.recv(buflen)
                except ConnectionResetError:
                    self.log("LOST CONNECTION TO TCP SOURCE", style="error")
                    self.stop(code=1)

                # Push packet to demuxer
                if len(data) == buflen: self.demuxer.push(data)

            elif self.config['rx']['input'] == "udp":
                # Get packet from UDP source
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
