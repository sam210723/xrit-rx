"""
demuxer.py
https://github.com/sam210723/xrit-rx

CCSDS demultiplexer
"""

from collections import deque, namedtuple
import colorama
from colorama import Fore, Back, Style
from time import sleep
from threading import Thread

import ccsds as CCSDS
import products

# Colorama styles
STYLE_ERR = f"{Fore.WHITE}{Back.RED}{Style.BRIGHT}"
STYLE_OK  = f"{Fore.GREEN}{Style.BRIGHT}"


class Demuxer:
    """
    Coordinates demultiplexing of CCSDS virtual channels into xRIT and image files
    """

    def __init__(self, config):
        """
        Initialises demuxer class
        """

        # Configure instance globals
        self.config = config        # Configuration tuple
        self.rxq = deque()          # Data receive queue
        self.core_ready = False     # Core thread ready flag
        self.core_stop = False      # Core thread stop flag
        self.channels = {}          # Channel handler instances
        self.status = {}            # Demuxer status dictionary

        # Set core loop delay
        bitrate = self.config.info[self.config.spacecraft][self.config.downlink][2]
        cadu_len = 1024 * 8
        cadu_period = 1 / (bitrate / cadu_len)
        self.core_wait = cadu_period / 2

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
        prev_vcid = None

        while not self.core_stop:
            # Pull next packet from queue
            buffer = self.pull()

            if buffer:
                # Parse VCDU in buffer
                vcdu = CCSDS.VCDU(buffer, self.config.info)
                self.status['vcid'] = vcdu.vcid

                # Dump VCDU to file
                if self.config.dump:
                    # Write packet to file (except fill packets)
                    if vcdu.vcid != 63:
                        self.config.dump.write(buffer)
                    else:
                        # Write single fill packet to file
                        if prev_vcid != 63: self.config.dump.write(buffer)

                # Check SCID is supported
                if not vcdu.sc:
                    if self.config.verbose: self.log(f"SPACECRAFT \"{vcdu.scid}\" NOT SUPPORTED", style="error")
                    continue

                # Check for VCID change
                if vcdu.vcid != prev_vcid:
                    prev_vcid = vcdu.vcid

                    # Notify channel handlers of VCID change
                    for c in self.channels:
                        self.channels[c].notify(vcdu.vcid)

                    # Print VCID info
                    if self.config.verbose: print()
                    vcdu.print_info()

                    if vcdu.vcid in self.config.ignored:
                        self.log(f"SKIPPING DATA (CHANNEL IS IGNORED IN CONFIG)", style="error", indent=2)

                # Discard fill packets and ignored VCIDs
                if vcdu.vcid == 63 or vcdu.vcid in self.config.ignored:
                    self.status["progress"] = 100
                    continue
                
                # Create channel handlers for new VCIDs
                if vcdu.vcid not in self.channels:
                    #FIXME: Probably a better way to do this
                    ccfg = namedtuple('ccfg', 'spacecraft downlink verbose dump output images xrit enhance ignored keys info VCID')
                    self.channels[vcdu.vcid] = Channel(ccfg(*self.config, vcdu.vcid), self)
                    if self.config.verbose: print(f"  {STYLE_OK}CREATED NEW CHANNEL HANDLER\n")

                # Push VCDU to appropriate channel handler
                self.channels[vcdu.vcid].push(vcdu)

            else:
                # Sleep thread when no VCDU available
                sleep(self.core_wait)


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


    def log(self, msg, style="none", indent=0):
        """
        Writes to console
        """

        # Colorama styles
        styles = {
            "none":   "",
            "ok":    f"{colorama.Fore.GREEN}{colorama.Style.BRIGHT}",
            "error": f"{colorama.Fore.WHITE}{colorama.Back.RED}{colorama.Style.BRIGHT}"
        }

        # Create indent string
        indent = "".join(" " for _ in range(indent))
        
        print(f"{indent}{styles[style]}{msg}")


class Channel:
    """
    Virtual channel data handler
    """

    def __init__(self, config, parent):
        """
        Initialises virtual channel data handler
        """

        self.config = config        # Configuration tuple
        self.counter = None         # VCDU continuity counter
        self.cppdu = None           # Current CP_PDU object
        self.tpfile = None          # Current TP_File object
        self.product = None         # Current Product object
        self.demuxer = parent       # Demuxer class instance (parent)
        self.crc_lut = CCSDS.CP_PDU.CCITT_LUT(None)  # CP_PDU CRC LUT


    def push(self, vcdu):
        """
        Takes in VCDUs for the channel handler to process
        """

        # Check VCDU continuity counter
        self.continuity(vcdu)
        self.counter = vcdu.counter

        # Parse M_PDU
        mpdu = CCSDS.M_PDU(vcdu.payload)
        
        # If M_PDU contains CP_PDU header
        if mpdu.HEADER:
            # No current TP_File and CP_PDU header is at the start of M_PDU
            if self.tpfile == None and mpdu.POINTER == 0:
                # Create CP_PDU for new TP_File
                self.cppdu = CCSDS.CP_PDU(mpdu.PACKET)
            
            # Continue unfinished TP_File
            else:
                # Split M_PDU at pointer
                pre_ptr = mpdu.PACKET[:mpdu.POINTER]
                post_ptr = mpdu.PACKET[mpdu.POINTER:]

                # Finish current CP_PDU
                try:
                    len_ok, crc_ok = self.cppdu.finish(pre_ptr, self.crc_lut)
                    if self.config.verbose:
                        # Show length error
                        if len_ok:
                            print(f"\n    {STYLE_OK}LENGTH:     OK")
                        else:
                            diff = len(self.cppdu.PAYLOAD) - self.cppdu.LENGTH
                            print(f"\n    {STYLE_ERR}LENGTH:     ERROR", end='')
                            print(f"{STYLE_ERR} (EXPECTED: {self.cppdu.LENGTH}, ACTUAL: {len(self.cppdu.PAYLOAD)}, DIFF: {diff})")

                        # Show CRC error
                        print(f"    {STYLE_OK if crc_ok else STYLE_ERR}CRC:        {'OK' if crc_ok else 'ERROR'}\n")

                    # Handle finished CP_PDU
                    self.handle_CPPDU(self.cppdu)
                except AttributeError:
                    if self.config.verbose: print(f"  {STYLE_ERR}NO CP_PDU TO FINISH (DROPPED PACKETS?)")
                
                # Create new CP_PDU
                self.cppdu = CCSDS.CP_PDU(post_ptr)

                # Not enough data to parse CP_PDU header
                if not self.cppdu.PARSED: return

                # Handle CP_PDUs less than one M_PDU in length
                if 1 < self.cppdu.LENGTH < 886 and len(self.cppdu.PAYLOAD) > self.cppdu.LENGTH:
                    # Remove trailing null bytes (M_PDU padding)
                    self.cppdu.PAYLOAD = self.cppdu.PAYLOAD[:self.cppdu.LENGTH]
                    
                    # Finish current CP_PDU
                    try:
                        len_ok, crc_ok = self.cppdu.finish(b'', self.crc_lut)
                        if self.config.verbose:
                            # Show length error
                            if len_ok:
                                print(f"\n    {STYLE_OK}LENGTH:     OK")
                            else:
                                diff = len(self.cppdu.PAYLOAD) - self.cppdu.LENGTH
                                print(f"\n    {STYLE_ERR}LENGTH:     ERROR", end='')
                                print(f"{STYLE_ERR} EXPECTED: {self.cppdu.LENGTH}, ACTUAL: {len(self.cppdu.PAYLOAD)}, DIFF: {diff})")

                            # Show CRC error
                            print(f"    {STYLE_OK if crc_ok else STYLE_ERR}CRC:        {'OK' if crc_ok else 'ERROR'}\n")

                        # Handle finished CP_PDU
                        self.handle_CPPDU(self.cppdu)
                    except AttributeError:
                        if self.config.verbose: print(f"  {STYLE_ERR}NO CP_PDU TO FINISH (DROPPED PACKETS?)")

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
                if self.config.verbose: print(f"  {STYLE_ERR}NO CP_PDU TO APPEND M_PDU TO (DROPPED PACKETS?)")
        
        # VCDU indicator
        if self.config.verbose: print(".", end="", flush=True)
    

    def continuity(self, vcdu):
        """
        Checks VCDU packet continuity
        """

        # Skip if first VCDU packet
        if not self.counter: return False

        # Handle counter reset
        if self.counter == 0xFFFFFF and vcdu.COUNTER == 0: return True
        
        # Check counter difference
        diff = vcdu.counter - self.counter - 1
        if diff > 0:
            if self.config.verbose:
                print(f"  {STYLE_ERR}DROPPED {diff} PACKET{'S' if diff > 1 else ''}    ({vcdu.COUNTER} -> {self.counter})")
            else:
                print(f"    {STYLE_ERR}DROPPED {diff} PACKET{'S' if diff > 1 else ''}")
            return False
        return True


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

            # Update dashboard progress indicator
            if type(self.product) != products.MultiSegmentImage:
                ac = len(self.tpfile.PAYLOAD)
                ex = self.tpfile.LENGTH
                self.demuxer.progress = round((ac/ex) * 100)

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
                if self.config.verbose: print(f"    KEY INDEX:  0x{spdu.key_index:02X}\n")

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
        xrit = CCSDS.xRIT(spdu.payload)

        # Save xRIT file if enabled
        if self.config.xrit:
            xrit.save(self.config.output)
            self.demuxer.status["xrit"] = xrit.get_save_path(None)

        # Save image file if enabled
        if self.config.images:
            # Create new product
            if self.product == None:
                self.product = products.new(self.config, xrit.FILE_NAME)
                self.product.print_info()
            
            # Add data to current product
            self.product.add(xrit)

            # Update dashboard progress indicator
            if type(self.product) == products.MultiSegmentImage:
                total = 0
                for c in self.product.images:
                    total += len(self.product.images[c])

                if self.config.downlink == "LRIT":
                    self.demuxer.progress = round((total / 10) * 100)
                else:
                    self.demuxer.progress = round((total / 50) * 100)

            # Save and clear complete product
            if self.product.complete:
                self.product.save()

                self.demuxer.status["image"] = self.product.last
                self.demuxer.progress = 0
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

                self.demuxer.status["image"] = self.product.last
                self.demuxer.progress = 0
                self.product = None
