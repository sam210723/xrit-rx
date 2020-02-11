"""
products.py
https://github.com/sam210723/xrit-rx

Parsing and assembly functions for downlinked products
"""

import os
import PIL


def new(spacecraft, downlink, xrit, root):
    """
    Select product class based on file name
    """
    
    return


class Product:
    """
    Product base class
    """

    pass


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
