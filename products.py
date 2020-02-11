"""
products.py
https://github.com/sam210723/xrit-rx

Parsing and assembly functions for downlinked products
"""

import os
import PIL


def new(spacecraft, downlink, name, root):
    """
    Select product class
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
        self.name = name
        self.root = root


class MultiSegmentImage(Product):
    """
    Multi-segment image products (e.g. Full Disk)
    """

    pass


class SingleSegmentImage(Product):
    """
    Single segment image products (e.g. Additional Data)
    """

    pass


class AlphanumericText(Product):
    """
    Plain text products (e.g. Transmission Schedule)
    """

    pass
