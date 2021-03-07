"""
demuxer.py
https://github.com/sam210723/xrit-rx
"""

from collections import deque, namedtuple
import colorama
from colorama import Fore, Back, Style
from time import sleep
from threading import Thread
import sys

import ccsds as CCSDS
import products

# Colorama styles
STYLE_ERR = f"{Fore.WHITE}{Back.RED}{Style.BRIGHT}"
STYLE_OK  = f"{Fore.GREEN}{Style.BRIGHT}"


class Demuxer:
    """
    Coordinates demultiplexing of CCSDS virtual channels into xRIT files.
    """

    def __init__(self, config):
        """
        Initialises demuxer class
        """

        # Configure instance globals
        self.config = config            # Configuration tuple
        self.rxq = deque()              # Data receive queue
        self.core_ready = False         # Core thread ready state
        self.core_stop = False          # Core thread stop flag
        self.channels = {}              # List of channel handlers
        self.vcid = None                # Current Virtual Channel ID
        self.latest_img = None          # Latest image output by demuxer
        self.latest_xrit = None         # Latest xRIT file output by demuxer

        # Set core loop delay
        bitrate = {
            "GK-2A": {
                "LRIT": 65536,      # 64 kbps
                "HRIT": 3072000     # 3 Mbps
            }
        }
        self.core_wait = (1 / (bitrate[self.config.spacecraft][self.config.downlink] / 8192)) / 2

        # Start core demuxer thread
        demux_thread = Thread()
        demux_thread.name = "DEMUX CORE"
        demux_thread.run = self.demux_core
        demux_thread.start()

    def demux_core(self):
        """
        Distributes VCDUs to channel handlers.
        """
        
        # Indicate core thread has initialised
        self.core_ready = True

        # Thread globals
        last_vcid = None                        # Last VCID seen
        crc_lut = CCSDS.CP_PDU.CCITT_LUT(None)  # CP_PDU CRC LUT
        
        # Open VCDU dump file
        if self.config.dump: dump_file = open(self.config.dump, 'wb+')

        # Thread loop
        while not self.core_stop:
            # Pull next packet from queue
            packet = self.pull()
            
            # If queue is not empty
            if packet:
                # Parse VCDU
                vcdu = CCSDS.VCDU(packet)
                self.vcid = vcdu.VCID

                # Dump raw VCDU to file
                if self.config.dump:
                    # Write packet to file if not fill
                    if vcdu.VCID != 63:
                        dump_file.write(packet)
                    else:
                        # Write single fill packet to file (forces VCDU change on playback)
                        if last_vcid != 63:
                            dump_file.write(packet)

                # Check spacecraft is supported
                if vcdu.SC != "GK-2A":
                    if self.config.verbose: print(f"{STYLE_ERR}SPACECRAFT \"{vcdu.SCID}\" NOT SUPPORTED")
                    continue

                # Check for VCID change
                if last_vcid != vcdu.VCID:
                    # Notify channel handlers of VCID change
                    for c in self.channels:
                        self.channels[c].notify(vcdu.VCID)
                    
                    # Print VCID info
                    if self.config.verbose: print()
                    vcdu.print_info()
                    if vcdu.VCID in self.config.blacklist: print(f"  {STYLE_ERR}IGNORING DATA (CHANNEL IS BLACKLISTED)")
                    last_vcid = vcdu.VCID

                # Discard fill packets and blacklisted VCIDs
                if vcdu.VCID == 63 or vcdu.VCID in self.config.blacklist: continue

                # Create channel handlers for new VCIDs
                if vcdu.VCID not in self.channels:
                    #FIXME: Probably a better way to do this
                    ccfg = namedtuple('ccfg', 'spacecraft downlink verbose dump output images xrit blacklist keys VCID lut')
                    self.channels[vcdu.VCID] = Channel(ccfg(*self.config, vcdu.VCID, crc_lut), self)
                    if self.config.verbose: print(f"  {STYLE_OK}CREATED NEW CHANNEL HANDLER\n")

                # Pass VCDU to appropriate channel handler
                self.channels[vcdu.VCID].data_in(vcdu)
            else:
                # No packet available, sleep thread
                sleep(self.core_wait)
        
        # Gracefully exit core thread
        if self.core_stop:
            if self.config.dump: dump_file.close()
            return

    def push(self, packet):
        """
        Takes in VCDUs for the demuxer to process
        :param packet: 892 byte Virtual Channel Data Unit (VCDU)
        """

        self.rxq.append(packet)

    def pull(self):
        """
        Pull data from receive queue
        """

        try:
            # Return top item
            return self.rxq.popleft()
        except IndexError:
            # Queue empty
            return None

    def complete(self):
        """
        Checks if receive queue is empty
        """

        return len(self.rxq) == 0

    def stop(self):
        """
        Stops the demuxer loop by setting thread stop flag
        """

        self.core_stop = True


class Channel:
    """
    Virtual channel data handler
    """

    def __init__(self, config, parent):
        """
        Initialises virtual channel data handler
        """

        self.config = config        # Configuration tuple
        self.counter = -1           # VCDU continuity counter
        self.cppdu = None           # Current CP_PDU object
        self.tpfile = None          # Current TP_File object
        self.product = None         # Current Product object
        self.demuxer = parent       # Demuxer class instance (parent)


    def data_in(self, vcdu):
        """
        Takes in VCDUs for the channel handler to process
        :param vcdu: Parsed VCDU object
        """

        # Check VCDU continuity counter
        self.continuity(vcdu)

        # Parse M_PDU
        mpdu = CCSDS.M_PDU(vcdu.MPDU)
        
        # If M_PDU contains CP_PDU header
        if mpdu.HEADER:
            # No current TP_File and CP_PDU header is at the start of M_PDU
            if self.tpfile == None and mpdu.POINTER == 0:
                # Create CP_PDU for new TP_File
                self.cppdu = CCSDS.CP_PDU(mpdu.PACKET)
            
            # Continue unfinished TP_File
            else:
                # If M_PDU contains data from previous CP_PDU
                if mpdu.POINTER != 0:
                    # Finish previous CP_PDU
                    preptr = mpdu.PACKET[:mpdu.POINTER]
                else:
                    # No data to append
                    preptr = b''

                try:
                    len_ok, crc_ok = self.cppdu.finish(preptr, self.config.lut)
                    if self.config.verbose: self.check_CPPDU(len_ok, crc_ok)

                    # Handle finished CP_PDU
                    self.handle_CPPDU(self.cppdu)
                except AttributeError:
                    if self.config.verbose:
                        print(f"  {STYLE_ERR}NO CP_PDU TO FINISH (DROPPED PACKETS?)")
                
                # Create new CP_PDU
                postptr = mpdu.PACKET[mpdu.POINTER:]
                self.cppdu = CCSDS.CP_PDU(postptr)

                # Need more data to parse CP_PDU header
                if not self.cppdu.PARSED:
                    return

                # Handle CP_PDUs less than one M_PDU in length
                if 1 < self.cppdu.LENGTH < 886 and len(self.cppdu.PAYLOAD) > self.cppdu.LENGTH:
                    # Remove trailing null bytes (M_PDU padding)
                    self.cppdu.PAYLOAD = self.cppdu.PAYLOAD[:self.cppdu.LENGTH]
                    
                    try:
                        len_ok, crc_ok = self.cppdu.finish(b'', self.config.lut)
                        if self.config.verbose: self.check_CPPDU(len_ok, crc_ok)

                        # Handle finished CP_PDU
                        self.handle_CPPDU(self.cppdu)
                    except AttributeError:
                        if self.config.verbose:
                            print(f"  {STYLE_ERR}NO CP_PDU TO FINISH (DROPPED PACKETS?)")

            # Handle special EOF CP_PDU (by ignoring it)
            if self.cppdu.is_EOF():
                self.cppdu = None
                if self.config.verbose:
                    print(f"    {STYLE_OK}[CP_PDU] EOF MARKER\n")
            else:
                if self.config.verbose:
                    self.cppdu.print_info()
                    print(f"    HEADER:     0x{self.cppdu.header.hex().upper()}")
                    print(f"    OFFSET:     0x{mpdu.POINTER:04X}\n    ", end="")
        else:
            # Append M_PDU payload to current CP_PDU
            try:
                # Check if CP_PDU header has been parsed
                was_parsed = self.cppdu.PARSED

                # Add data from current M_PDU
                self.cppdu.append(mpdu.PACKET)

                # If CP_PDU header was just parsed, print CP_PDU header info
                if was_parsed != self.cppdu.PARSED and self.config.verbose:
                    self.cppdu.print_info()
                    print(f"    HEADER:     0x{self.cppdu.header.hex().upper()}")
                    print(f"    OFFSET:     SPANS MULTIPLE M_PDUs")
            except AttributeError:
                if self.config.verbose:
                    print(f"  {STYLE_ERR}NO CP_PDU TO APPEND M_PDU TO (DROPPED PACKETS?)")
        
        # VCDU indicator
        if self.config.verbose: print(".", end="")
        sys.stdout.flush()
    

    def continuity(self, vcdu):
        """
        Checks VCDU packet continuity by comparing packet counters
        """

        # If at least one VCDU has been received
        if self.counter != -1:
            # Check counter reset
            if self.counter == 0xFFFFFF and vcdu.COUNTER == 0:
                self.counter = vcdu.COUNTER
                return
            
            diff = vcdu.COUNTER - self.counter - 1
            if diff > 0:
                if self.config.verbose:
                    print(f"  {STYLE_ERR}DROPPED {diff} PACKET{'S' if diff > 1 else ''}    (CURRENT: {vcdu.COUNTER}   LAST: {self.counter}   VCID: {vcdu.VCID})")
                else:
                    print(f"    {STYLE_ERR}DROPPED {diff} PACKET{'S' if diff > 1 else ''}")
        
        self.counter = vcdu.COUNTER
    

    def check_CPPDU(self, len_ok, crc_ok):
        """
        Checks length and CRC of finished CP_PDU
        """

        # Show length error
        if len_ok:
            print(f"\n    {STYLE_OK}LENGTH:     OK")
        else:
            ex = self.cppdu.LENGTH
            ac = len(self.cppdu.PAYLOAD)
            diff = ac - ex
            print(f"\n    {STYLE_ERR}LENGTH:     ERROR (EXPECTED: {ex}, ACTUAL: {ac}, DIFF: {diff})")

        # Show CRC error
        if crc_ok:
            print(f"    {STYLE_OK}CRC:        OK")
        else:
            print(f"    {STYLE_ERR}CRC:        ERROR")
        print()


    def handle_CPPDU(self, cppdu):
        """
        Processes complete CP_PDUs to build a TP_File
        """

        if cppdu.SEQ == cppdu.Sequence.FIRST:
            # Create new TP_File
            self.tpfile = CCSDS.TP_File(cppdu.PAYLOAD[:-2])

        elif cppdu.SEQ == cppdu.Sequence.CONTINUE:
            # Add data to TP_File
            self.tpfile.append(cppdu.PAYLOAD[:-2])

        elif cppdu.SEQ == cppdu.Sequence.LAST:
            # Close current TP_File
            len_ok = self.tpfile.finish(cppdu.PAYLOAD[:-2])

            if self.config.verbose: self.tpfile.print_info()
            if len_ok:
                if self.config.verbose: print(f"    {STYLE_OK}LENGTH:     OK\n")
                
                # Handle S_PDU (decryption)
                spdu = CCSDS.S_PDU(self.tpfile.PAYLOAD, self.config.keys)

                # Handle xRIT file
                self.handle_xRIT(spdu)

                # Print key index
                if self.config.verbose:
                    print(f"    KEY INDEX:  0x{int.from_bytes(spdu.index, byteorder='big'):02X}\n")

            elif not len_ok:
                ex = self.tpfile.LENGTH
                ac = len(self.tpfile.PAYLOAD)
                diff = ac - ex

                if self.config.verbose:
                    print(f"    {STYLE_ERR}LENGTH:     ERROR (EXPECTED: {ex}, ACTUAL: {ac}, DIFF: {diff})")
                print(f"    {STYLE_ERR}SKIPPING FILE DUE TO DROPPED PACKETS")
            
            # Clear finished TP_File
            self.tpfile = None

        if self.config.verbose:
            ac = len(self.tpfile.PAYLOAD)
            ex = self.tpfile.LENGTH
            p = round((ac/ex) * 100)
            diff = ex - ac
            print(f"    [TP_File]  CURRENT LEN: {ac} ({p}%)     EXPECTED LEN: {ex}     DIFF: {diff}\n\n\n")


    def handle_xRIT(self, spdu):
        """
        Processes complete S_PDUs to build xRIT and Image files
        """

        # Create new xRIT object
        xrit = CCSDS.xRIT(spdu.PLAINTEXT)

        # Save xRIT file if enabled
        if self.config.xrit:
            xrit.save(self.config.output)
            self.demuxer.latest_xrit = xrit.get_save_path(self.config.output)

        # Save image file if enabled
        if self.config.images:
            # Create new product
            if self.product == None:
                self.product = products.new(self.config, xrit.FILE_NAME)
                self.product.print_info()
            
            # Add data to current product
            self.product.add(xrit)

            # Save and clear complete product
            if self.product.complete:
                self.product.save()
                self.demuxer.latest_img = self.product.last
                self.product = None
        else:
            # Print XRIT file info
            xrit.print_info(self.config.verbose)


    def notify(self, vcid):
        """
        Notifies virtual channel handler of change in VCID
        """

        # No longer the active channel handler
        if vcid != self.config.VCID:
            # Channel has unfinished TP_File
            if self.tpfile != None:
                # Handle S_PDU (decryption)
                spdu = CCSDS.S_PDU(self.tpfile.PAYLOAD, self.config.keys)

                # Handle xRIT file
                self.handle_xRIT(spdu)

                if len(self.tpfile.PAYLOAD) < self.tpfile.LENGTH:
                    print(f"    {STYLE_ERR}FILE IS INCOMPLETE")
                    ac = len(self.tpfile.PAYLOAD)
                    ex = self.tpfile.LENGTH
                    p = round((ac/ex) * 100)
                    print(f"    {STYLE_ERR}{p}% OF EXPECTED LENGTH")

                # Clear finished TP_File
                self.tpfile = None
            elif self.product != None:
                # Save and clear current product
                self.product.save()
                self.product = None
