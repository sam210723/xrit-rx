"""
products.py
https://github.com/sam210723/xrit-rx

Parsing and assembly functions for downlinked products
"""

class Product:
    """
    Product base class
    """

    def __init__(self, spacecraft, downlink, name):
        self.spacecraft = spacecraft
        self.downlink = downlink
        self.parse_name(name)

        #if self.mode == "FD":
            #self.product = MultiSegmentImage(spacecraft, downlink, name)
    
    def save(self):
        return
    
    def parse_name(self, name):
        """
        Parses xRIT file name
        """

        split = name.split("_")

        self.ftype = split[0]
        self.mode = split[1]
        self.seq = split[2]

        if self.ftype == "IMG":
            self.spec = split[3]
            self.txDate = split[4]
            self.txTime = split[5]
            self.seg = split[6][:2]
        elif self.ftype == "ADD":
            self.spec = None
            self.txDate = split[3]
            self.txTime = split[4]
            self.segNum = split[5][:2]
    
    def parse_date(self):
        d = self.txDate[6:]
        m = self.txDate[4:6]
        y = self.txDate[:4]

        return(d, m, y)

    def parse_time(self):
        h = self.txTime[:2]
        m = self.txTime[2:4]
        s = self.txTime[4:6]

        return (h, m ,s)

    def print_info(self):
        print("  [PRODUCT] {} {} {}/{}/{} {}:{}:{} UTC".format(self.mode, self.seq, *self.parse_date(), *self.parse_time()))

    pass
