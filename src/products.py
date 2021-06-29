"""
products.py
https://github.com/sam210723/xrit-rx

Parsing and assembly functions for downlinked products
"""

import collections
from colorama import Fore, Back, Style
import io
import numpy as np
from   pathlib import Path
from   PIL import Image, UnidentifiedImageError
import subprocess


def new(config, name):
    """
    Get new product class
    """

    types = {
        "GK-2A": {
            "LRIT": {
                "FD": MultiSegmentImage,
                "ANT": AlphanumericText
            },
            "HRIT": {
                "FD": MultiSegmentImage
            }
        }
    }

    # Observation mode
    mode = name.split("_")[1]

    try:
        # Get product type from dict
        pclass = types[config.spacecraft][config.downlink][mode]
    except KeyError:
        # Treat all other products as single segment images
        pclass = SingleSegmentImage
    
    return pclass(config, name)


class Product:
    """
    Product base class
    """

    def __init__(self, config, name):
        self.config = config                # Configuration tuple
        self.name = self.parse_name(name)   # Product name
        self.alias = "PRODUCT"              # Product type alias
        self.complete = False               # Completed product flag
        self.last = None                    # Path to last file saved
    
    def parse_name(self, n):
        """
        Parse file name into namedtuple
        """

        name = collections.namedtuple("name", "type mode sequence date time full")
        parts = n.split("_")
        full = n.split(".")[0][:-3]

        if parts[0] == "IMG":
            # Generalise filename for multi-channel HRIT images
            if self.config.downlink == "HRIT":
                gen = n.split("_")
                gen[3] = "<CHANNEL>"
                full = "_".join(gen).split(".")[0][:-3]
            
            tup = name(
                parts[0],
                parts[1],
                int(parts[2]),
                self.parse_date(parts[4]),
                self.parse_time(parts[5]),
                full
            )
        else:
            tup = name(
                parts[0],
                parts[1],
                int(parts[2]),
                self.parse_date(parts[3]),
                self.parse_time(parts[4]),
                full
            )
        
        return tup

    def parse_date(self, date):
        d = date[6:]
        m = date[4:6]
        y = date[:4]

        return (d, m, y)

    def parse_time(self, time):
        h = time[:2]
        m = time[2:4]
        s = time[4:6]

        return (h, m ,s)

    def get_save_path(self, channel=None, suffix=None, extension=None):
        """
        Get save path of product
        """

        date = "{2}{1}{0}".format(*self.name.date)
        name = self.name.full

        # Replace channel placeholder for multichannel HRIT images
        if channel: name = name.replace("<CHANNEL>", channel)

        # Add suffix to file name
        if suffix: name += suffix

        # Add date and observation mode to path
        path = self.config.output / date / self.name.mode

        # Create folders for product
        path.mkdir(parents=True, exist_ok=True)

        # Add product name to path
        path = path / name
        
        # Add file extension
        if extension: path = path.with_suffix(f".{extension}")

        return path

    def print_info(self):
        """
        Print product info
        """

        print("  [PRODUCT] {} #{}    {}:{}:{} UTC    {}/{}/{}".format(
            self.name.mode,
            self.name.sequence,
            *self.name.time,
            *self.name.date
        ))


class MultiSegmentImage(Product):
    """
    Multi-segment image products (e.g. Full Disk)
    """

    def __init__(self, config, name):
        # Call parent class init method
        Product.__init__(self, config, name)
        
        # Product specific setup
        self.counter = 0                    # Segment counter
        self.images = {}                    # Image list
        self.ext = "jpg"                    # Output file extension
        self.lastproglen = 0                # Last number of lines in progress indicator

    def add(self, xrit):
        """
        Add data to product
        """

        # Get channel and segment number
        chan = xrit.FILE_NAME.split("_")[3]
        num = int(xrit.FILE_NAME.split(".")[0][-2:])

        # Check object for current channel exists
        try:
            self.images[chan]
        except:
            self.images[chan] = {}

        if self.config.downlink == "LRIT":
            # Get image from JPG payload
            buf = io.BytesIO(xrit.DATA_FIELD)
            
            try:
                img = Image.open(buf)
            except UnidentifiedImageError:
                print("    " + Fore.WHITE + Back.RED + Style.BRIGHT + "NO IMAGE FOUND IN XRIT FILE")
                return
        else:
            # Get image from J2K payload
            img = self.convert_to_img(self.get_save_path(channel=chan), xrit.DATA_FIELD)

        # Add segment to channel object
        self.images[chan][num] = img
        self.counter += 1

        # Update progress bar
        if not self.config.verbose: self.progress()

        # Mark product as complete
        total_segs = { "LRIT": 10, "HRIT": 50 }
        if self.counter == total_segs[self.config.downlink]: self.complete = True

    def save(self):
        """
        Save product to disk
        """

        for c in self.images:
            # Create output image
            img = Image.new("RGB", self.get_res(c))

            # Combine segments into final image
            for s in self.images[c]:
                height = self.images[c][s].size[1]
                offset = height * (s - 1)

                try:
                    img.paste(
                        self.images[c][s],
                        ( 0, offset )
                    )
                except OSError:
                    print("    " + Fore.WHITE + Back.RED + Style.BRIGHT + "SKIPPING TRUNCATED IMAGE SEGMENT")

            # Get image output path
            path = self.get_save_path(channel=c, extension="jpg")

            # Save assembled image
            img.save(path, format='JPEG', subsampling=0, quality=100)
            log(f"    Saved \"{path}\"", style="ok")
            self.last = str(path.relative_to(self.config.output))

            # Optional LRIT IR105 image enhancement
            if self.config.enhance and c == "IR105" and self.config.downlink == "LRIT":
                path = self.get_save_path(channel=c, suffix="_ENHANCED", extension="jpg")

                enh = EnhanceIR105(img)
                enh.save(path)

                self.last = str(path.relative_to(self.config.output))

    def convert_to_img(self, path, data):
        """
        Converts J2K to Pillow Image object via PPM using libjpeg

        Arguments:
            path {string} -- Path for temporary files
            data {bytes} -- JPEG2000 image

        Returns:
            Pillow.Image -- Pillow Image object
        """

        # Get JP2 and PPM file names
        jp2 = path.with_suffix(".jp2")
        ppm = path.with_suffix(".ppm")

        # Save JP2 to disk
        f = open(jp2, "wb")
        f.write(data)
        f.close()

        # Convert J2P to PPM then delete JP2
        subprocess.call(["tools\\libjpeg\\jpeg", jp2, ppm], stdout=subprocess.DEVNULL)
        Path(jp2).unlink()
        
        # Load 16-bit PPM and convert to 8-bit image then delete PPM
        #TODO: Save as native 16-bit PNG
        img = Image.open(ppm)
        iarr = np.uint8(np.array(img) / 4)
        img = Image.fromarray(iarr)
        Path(ppm).unlink()
        
        return img
    
    def get_res(self, channel):
        """
        Returns the horizontal and vertical resolution of the given satellte, downlink, observation mode and channel
        """

        res = {
            "GK-2A": {
                "LRIT": {
                    "FD": {
                        "IR105": (2200, 2200)
                    }
                },
                "HRIT": {
                    "FD": {
                        "IR105": (2750, 2750),
                        "IR123": (2750, 2750),
                        "SW038": (2750, 2750),
                        "WV069": (2750, 2750),
                        "VI006": (11000, 11000)
                    }
                }
            }
        }

        try:
            return res[self.config.spacecraft][self.config.downlink][self.name.mode][channel]
        except:
            return (None, None)

    def progress(self):
        """
        Renders progress bar for multi-segment mult-wavelength images
        """

        # Clear previous console lines
        for i in range(self.lastproglen):
            print("\33[2K\r", end="", flush=True)
            print("\033[1A", end="", flush=True)

        line = ""
        self.lastproglen = 0

        # Loop through channels
        for c in self.images:
            line += "    {}  {}{}{}{}{}{}{}{}{}{}  {}/{}\n".format(
                c,
                "\u2588\u2588" if 1 in self.images[c].keys() else "\u2591\u2591",
                "\u2588\u2588" if 2 in self.images[c].keys() else "\u2591\u2591",
                "\u2588\u2588" if 3 in self.images[c].keys() else "\u2591\u2591",
                "\u2588\u2588" if 4 in self.images[c].keys() else "\u2591\u2591",
                "\u2588\u2588" if 5 in self.images[c].keys() else "\u2591\u2591",
                "\u2588\u2588" if 6 in self.images[c].keys() else "\u2591\u2591",
                "\u2588\u2588" if 7 in self.images[c].keys() else "\u2591\u2591",
                "\u2588\u2588" if 8 in self.images[c].keys() else "\u2591\u2591",
                "\u2588\u2588" if 9 in self.images[c].keys() else "\u2591\u2591",
                "\u2588\u2588" if 10 in self.images[c].keys() else "\u2591\u2591",
                len(self.images[c]),
                10
            )
            self.lastproglen += 1
        
        print(line, end="", flush=True)


class SingleSegmentImage(Product):
    """
    Single segment image products (e.g. Additional Data)
    """

    def __init__(self, config, name):
        # Call parent class init method
        Product.__init__(self, config, name)
        
        # Product specific setup
        self.payload = None

    def add(self, xrit):
        """
        Add data to product
        """

        self.payload = xrit.DATA_FIELD
        self.complete = True

    def save(self):
        """
        Save product to disk
        """

        self.ext = self.get_ext()
        path = self.get_save_path(extension=self.ext)

        outf = open(path, mode="wb")
        outf.write(self.payload)
        outf.close()

        print("    " + Fore.GREEN + Style.BRIGHT + "Saved \"{}\"".format(path))
        self.last = self.get_save_path(with_root=False, ext=self.ext)
        self.last = str(path.relative_to(self.config.output))

    def get_ext(self):
        """
        Detects output extension based on file signature
        """

        ext = "bin"
        if self.payload[:3] == b'GIF':
            ext = "gif"
        elif self.payload[1:4] == b'PNG':
            ext = "png"

        return ext


class AlphanumericText(Product):
    """
    Plain text products (e.g. Transmission Schedule)
    """

    def __init__(self, config, name):
        # Call parent class init method
        Product.__init__(self, config, name)
        
        # Product specific setup
        self.payload = None
        self.ext = "txt"

    def add(self, xrit):
        """
        Add data to product
        """

        self.payload = xrit.DATA_FIELD
        self.complete = True

    def save(self):
        """
        Save product to disk
        """

        path = self.get_save_path(extension=self.ext)
        
        outf = open(path, mode="wb")
        outf.write(self.payload)
        outf.close()

        # Detect GK-2A LRIT DOP
        if self.payload[:40].decode('utf-8') == "GK-2A AMI LRIT DOP(Daily Operation Plan)":
            print("    GK-2A LRIT Daily Operation Plan")

        print("    " + Fore.GREEN + Style.BRIGHT + "Saved \"{}\"".format(path))
        self.last = self.get_save_path(with_root=False, ext=self.ext)
        self.last = str(path.relative_to(self.config.output))


class EnhanceIR105:
    """
    Apply infrared colour enhancement to IR105 channel imagery
    """

    def __init__(self, img):
        lut = [
            (  0,   0,   0), (  1,   1,   1), (  2,   2,   2), (  3,   3,   3), (  4,   4,   4), (  5,   5,   5), (  6,   6,   6), (  7,   7,   7),
            (  8,   8,   8), (  9,   9,   9), ( 10,  10,  10), ( 11,  11,  11), ( 12,  12,  12), ( 13,  13,  13), ( 14,  14,  14), ( 15,  15,  15),
            ( 16,  16,  16), ( 17,  17,  17), ( 18,  18,  18), ( 19,  19,  19), ( 20,  20,  20), ( 21,  21,  21), ( 22,  22,  22), ( 23,  23,  23),
            ( 24,  24,  24), ( 25,  25,  25), ( 26,  26,  26), ( 27,  27,  27), ( 28,  28,  28), ( 29,  29,  29), ( 30,  30,  30), ( 31,  31,  31),
            ( 32,  32,  32), ( 33,  33,  33), ( 34,  34,  34), ( 35,  35,  35), ( 36,  36,  36), ( 37,  37,  37), ( 38,  38,  38), ( 39,  39,  39),
            ( 40,  40,  40), ( 41,  41,  41), ( 42,  42,  42), ( 43,  43,  43), ( 44,  44,  44), ( 45,  45,  45), ( 46,  46,  46), ( 47,  47,  47),
            ( 48,  48,  48), ( 49,  49,  49), ( 50,  50,  50), ( 51,  51,  51), ( 52,  52,  52), ( 53,  53,  53), ( 54,  54,  54), ( 55,  55,  55),
            ( 56,  56,  56), ( 57,  57,  57), ( 58,  58,  58), ( 59,  59,  59), ( 60,  60,  60), ( 61,  61,  61), ( 62,  62,  62), ( 63,  63,  63),
            ( 64,  64,  64), ( 65,  65,  65), ( 66,  66,  66), ( 67,  67,  67), ( 68,  68,  68), ( 69,  69,  69), ( 70,  70,  70), ( 71,  71,  71),
            ( 72,  72,  72), ( 73,  73,  73), ( 74,  74,  74), ( 75,  75,  75), ( 76,  76,  76), ( 77,  77,  77), ( 78,  78,  78), ( 79,  79,  79),
            ( 80,  80,  80), ( 81,  81,  81), ( 82,  82,  82), ( 83,  83,  83), ( 84,  84,  84), ( 85,  85,  85), ( 86,  86,  86), ( 87,  87,  87),
            ( 88,  88,  88), ( 89,  89,  89), ( 90,  90,  90), ( 91,  91,  91), ( 92,  92,  92), ( 93,  93,  93), ( 94,  94,  94), ( 95,  95,  95),
            ( 96,  96,  96), ( 97,  97,  97), ( 98,  98,  98), ( 99,  99,  99), (100, 100, 100), (101, 101, 101), (102, 102, 102), (103, 103, 103),
            (104, 104, 104), (105, 105, 105), (106, 106, 106), (107, 107, 107), (108, 108, 108), (109, 109, 109), (110, 110, 110), (111, 111, 111),
            (112, 112, 112), (113, 113, 113), (114, 114, 114), (115, 115, 115), (116, 116, 116), (117, 117, 117), (118, 118, 118), (119, 119, 119),
            (120, 120, 120), (121, 121, 121), (122, 122, 122), (123, 123, 123), (124, 124, 124), (125, 125, 125), (126, 126, 126), (127, 127, 127),
            (128, 128, 128), (129, 129, 129), (130, 130, 130), (131, 131, 131), (132, 132, 132), (133, 133, 133), (134, 134, 134), (135, 135, 135),
            (136, 136, 136), (137, 137, 137), (138, 138, 138), (139, 139, 139), (140, 140, 140), (141, 141, 141), (142, 142, 142), (143, 143, 143),
            (144, 144, 144), (145, 145, 145), (146, 146, 146), (147, 147, 147), (148, 148, 148), (149, 149, 149), (150, 150, 150), (151, 151, 151),
            (152, 152, 152), (153, 153, 153), (154, 154, 154), (155, 155, 155), (156, 156, 156), (157, 157, 157), (158, 158, 158), (159, 159, 159),
            (160, 160, 160), (161, 161, 161), (162, 162, 162), (163, 163, 163), (164, 164, 164), (165, 165, 165), (166, 166, 166), (167, 167, 167),
            (168, 168, 168), (169, 169, 169), (170, 170, 170), (171, 171, 171), (172, 172, 172), (173, 173, 173), (174, 174, 174), (175, 175, 175),
            (176, 176, 176), (177, 177, 177), (160, 160, 174), (143, 143, 174), (125, 125, 176), (108, 108, 182), ( 91,  91, 192), ( 73,  73, 204),
            ( 55,  55, 216), ( 37,  37, 234), ( 18,  20, 247), (  0,  19, 255), (  0,  31, 255), (  0,  47, 255), (  0,  63, 255), (  0,  79, 255),
            (  0,  91, 255), (  0, 107, 255), (  0, 123, 255), (  0, 139, 255), (  0, 155, 255), (  0, 167, 255), (  0, 183, 255), (  0, 199, 255),
            (  0, 215, 255), (  0, 227, 255), (  0, 243, 255), (  0, 255, 255), ( 15, 255, 239), ( 27, 255, 227), ( 43, 255, 211), ( 59, 255, 195),
            ( 75, 255, 179), ( 87, 255, 167), (103, 255, 151), (119, 255, 135), (135, 255, 119), (151, 255, 103), (163, 255,  91), (179, 255,  75),
            (195, 255,  59), (211, 255,  43), (223, 255,  31), (239, 255,  15), (255, 255,   0), (255, 239,   0), (255, 227,   0), (255, 211,   0),
            (255, 195,   0), (255, 179,   0), (255, 167,   0), (255, 151,   0), (255, 135,   0), (255, 119,   0), (255, 103,   0), (255,  91,   0),
            (255,  75,   0), (255,  59,   0), (255,  43,   0), (255,  31,   0), (255,  15,   0), (255,   0,   0), (237,   0,   0), (224,   0,   0),
            (206,   0,   0), (189,   0,   0), (171,   0,   0), (158,   0,   0), (140,   0,   0), (131,   0,   0), (131,   0,   0), (131,   0,   0),
            (131,   0,   0), (131,   0,   0), (131,   0,   0), (131,   0,   0), (131,   0,   0), (131,   0,   0), (131,   0,   0), (131,   0,   0)
        ]

        # Create empty NumPy arrays for each channel
        nplutR = np.zeros(len(lut), dtype=np.uint8)
        nplutG = np.zeros(len(lut), dtype=np.uint8)
        nplutB = np.zeros(len(lut), dtype=np.uint8)

        # Convert LUT channels into separate NumPy arrays
        for i, c in enumerate(lut):
            nplutR[i] = c[0]
            nplutG[i] = c[1]
            nplutB[i] = c[2]
        
        # Get grayscale values from input image
        gray = np.array(img)
        
        # Apply each channel of LUT to grayscale image
        enhR = nplutR[gray]
        enhG = nplutG[gray]
        enhB = nplutB[gray]

        # Convert enhanced arrays to images
        iR = Image.fromarray(enhR).convert('L')
        iG = Image.fromarray(enhG).convert('L')
        iB = Image.fromarray(enhB).convert('L')

        # Combine enhanced channels into an RGB(A) image
        self.output = Image.merge("RGB", (iR, iG, iB))

    def save(self, path):
        self.output.save(path, format='JPEG', subsampling=0, quality=100)
        print(f"    {Fore.GREEN}{Style.BRIGHT}Saved \"{path}\"")
