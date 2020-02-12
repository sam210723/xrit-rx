"""
products.py
https://github.com/sam210723/xrit-rx

Parsing and assembly functions for downlinked products
"""

import collections
import io
import os
from PIL import Image, ImageFile


def new(config, name):
    """
    Get new product class
    """

    types = {
        "GK-2A": {
            "LRIT": {
                "FD": MultiSegmentImage,
                "ANT": AlphanumericText
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
    
    def parse_name(self, n):
        """
        Parse file name into namedtuple
        """

        name = collections.namedtuple("name", "type mode sequence channel date time full")

        if n.split("_")[0] == "IMG":
            tup = name(
                n.split("_")[0],
                n.split("_")[1],
                int(n.split("_")[2]),
                n.split("_")[3],
                self.parse_date(n.split("_")[4]),
                self.parse_time(n.split("_")[5]),
                n.split(".")[0][:-3]
            )
        else:
            tup = name(
                n.split("_")[0],
                n.split("_")[1],
                int(n.split("_")[2]),
                None,
                self.parse_date(n.split("_")[3]),
                self.parse_time(n.split("_")[4]),
                n.split(".")[0][:-3]
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

    def get_path(self, ext=None):
        """
        Get save path of product (without extension)
        """

        date = "{2}{1}{0}".format(*self.name.date)
        path = "{}/{}/".format(date, self.name.mode)

        # Check output directories exist
        if not os.path.exists("{}/{}".format(self.config.output, date)): os.mkdir(self.config.output + "/" + date)
        if not os.path.exists("{}/{}/{}".format(self.config.output, date, self.name.mode)): os.mkdir(self.config.output + "/" + date + "/" + self.name.mode)

        return "{}{}{}{}".format(self.config.output, path, self.name.full, "" if not ext else ".{}".format(ext))

    def print_info(self):
        """
        Print product info
        """

        print("  [{}] {}{} #{} {}/{}/{} {}:{}:{} UTC\n    ".format(
            self.alias,
            self.name.mode,
            "" if not self.name.channel else " {}".format(self.name.channel),
            self.name.sequence,
            *self.name.date,
            *self.name.time
        ), end="", flush=True)


class MultiSegmentImage(Product):
    """
    Multi-segment image products (e.g. Full Disk)
    """

    def __init__(self, config, name):
        # Call parent class init method
        Product.__init__(self, config, name)
        
        # Product specific setup
        self.alias = "IMAGE"                # Product type alias
        self.segc = 0                       # Segment counter
        self.segi = []                      # Segment image object list

    def add(self, xrit):
        """
        Add data to product
        """

        # Create image from xRIT data field
        buf = io.BytesIO(xrit.DATA_FIELD)
        img = Image.open(buf)
        self.segi.append(img)

        # Increment counter and indicator
        self.segc += 1
        print(".", end="", flush=True)
        
        # Mark as complete after 10 segments
        if self.segc == 10: self.complete = True

    def save(self):
        """
        Save product to disk
        """

        # Create new image
        outI = Image.new("RGB", self.get_res())

        # Combine segments into output image
        for i, seg in enumerate(self.segi):
            outI.paste(seg, (0, seg.size[1] * i))

        # Save image to disk
        path = self.get_path("jpg")
        outI.save(path, format='JPEG', subsampling=0, quality=100)
        print("\n    Saved: \"{}.jpg\"\n".format(self.name.full))
    
    def get_res(self):
        """
        Returns the horizontal and vertical resolution of the given observation mode
        """

        if self.config.spacecraft == "GK-2A":
            if self.name.mode == "FD": outH = outV = 2200
        else:
            outH = outV = None
        
        return outH, outV


class SingleSegmentImage(Product):
    """
    Single segment image products (e.g. Additional Data)
    """

    def __init__(self, config, name):
        # Call parent class init method
        Product.__init__(self, config, name)
        
        # Product specific setup
        self.alias = "IMAGE"                # Product type alias

    def add(self, xrit):
        """
        Add data to product
        """

        self.completed = True

    def save(self):
        """
        Save product to disk
        """

        path = self.get_path()


class AlphanumericText(Product):
    """
    Plain text products (e.g. Transmission Schedule)
    """

    def __init__(self, config, name):
        # Call parent class init method
        Product.__init__(self, config, name)
        
        # Product specific setup
        self.alias = "TEXT"                 # Product type alias

    def add(self, xrit):
        """
        Add data to product
        """

        self.completed = True

    def save(self):
        """
        Save product to disk
        """

        path = self.get_path("txt")
