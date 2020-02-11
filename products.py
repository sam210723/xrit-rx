"""
products.py
https://github.com/sam210723/xrit-rx

Parsing and assembly functions for downlinked products
"""

import collections
import os
import PIL


def new(spacecraft, downlink, name, root):
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
        pclass = types[spacecraft][downlink][mode]
    except KeyError:
        # Treat all other products as single segment images
        pclass = SingleSegmentImage
    
    return pclass(spacecraft, downlink, name, root)


class Product:
    """
    Product base class
    """

    def __init__(self, spacecraft, downlink, name, root):
        self.spacecraft = spacecraft
        self.downlink = downlink
        self.name = self.parse_name(name)
        self.root = root
    
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

    def get_path(self):
        """
        Get save path of product (without extension)
        """

        date = "{2}{1}{0}".format(*self.name.date)
        path = "{}/{}/".format(date, self.name.mode)

        # Check output directories exist
        if not os.path.exists("{}/{}".format(self.root, date)): os.mkdir(self.root + "/" + date)
        if not os.path.exists("{}/{}/{}".format(self.root, date, self.name.mode)): os.mkdir(self.root + "/" + date + "/" + self.name.mode)

        return self.root + path + self.name.full

    def print_info(self):
        """
        Print product info
        """

        print("  [PRODUCT] {}{} #{} {}/{}/{} {}:{}:{} UTC".format(
            self.name.mode,
            "" if not self.name.channel else " {}".format(self.name.channel),
            self.name.sequence,
            *self.name.date,
            *self.name.time
        ))


class MultiSegmentImage(Product):
    """
    Multi-segment image products (e.g. Full Disk)
    """

    def save(self):
        """
        Save product to disk
        """

        path = self.get_path()


class SingleSegmentImage(Product):
    """
    Single segment image products (e.g. Additional Data)
    """

    def save(self):
        """
        Save product to disk
        """

        path = self.get_path()


class AlphanumericText(Product):
    """
    Plain text products (e.g. Transmission Schedule)
    """

    def save(self):
        """
        Save product to disk
        """

        path = self.get_path()
