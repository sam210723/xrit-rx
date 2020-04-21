"""
enhance-ir.py
https://github.com/sam210723/xrit-rx

GK-2A Infrared Colour Enhancement
"""

import argparse
import glob
import ntpath
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

### GK-2A Calibration Table ###
cal = [
    330.05254,
    319.99371,
    309.08976,
    297.08050,
    283.54929,
    267.75568,
    248.14399,
    220.17763
]

### Colour Look-up Table ###
clut = [
    (0,0,131), (0,0,131), (0,0,135), (0,0,139), (0,0,143), (0,0,147), (0,0,151), (0,0,155), (0,0,159), (0,0,163), (0,0,167), (0,0,171), (0,0,175), (0,0,179), (0,0,183),
    (0,0,187), (0,0,191), (0,0,195), (0,0,199), (0,0,203), (0,0,207), (0,0,211), (0,0,215), (0,0,219), (0,0,223), (0,0,227), (0,0,231), (0,0,235), (0,0,239), (0,0,243),
    (0,0,247), (0,0,251), (0,0,255), (0,0,255), (0,3,255), (0,7,255), (0,11,255), (0,15,255), (0,19,255), (0,23,255), (0,27,255), (0,31,255), (0,35,255), (0,39,255), (0,43,255),
    (0,47,255), (0,51,255), (0,55,255), (0,59,255), (0,63,255), (0,67,255), (0,71,255), (0,75,255), (0,79,255), (0,83,255), (0,87,255), (0,91,255), (0,95,255), (0,99,255),
    (0,103,255), (0,107,255), (0,111,255), (0,115,255), (0,119,255), (0,123,255), (0,127,255), (0,131,255), (0,135,255), (0,139,255), (0,143,255), (0,147,255), (0,151,255),
    (0,155,255), (0,159,255), (0,163,255), (0,167,255), (0,171,255), (0,175,255), (0,179,255), (0,183,255), (0,187,255), (0,191,255), (0,195,255), (0,199,255), (0,203,255),
    (0,207,255), (0,211,255), (0,215,255), (0,219,255), (0,223,255), (0,227,255), (0,231,255), (0,235,255), (0,239,255), (0,243,255), (0,247,255), (0,251,255), (0,255,255),
    (0,255,255), (3,255,251), (7,255,247), (11,255,243), (15,255,239), (19,255,235), (23,255,231), (27,255,227), (31,255,223), (35,255,219), (39,255,215), (43,255,211),
    (47,255,207), (51,255,203), (55,255,199), (59,255,195), (63,255,191), (67,255,187), (71,255,183), (75,255,179), (79,255,175), (83,255,171), (87,255,167), (91,255,163),
    (95,255,159), (99,255,155), (103,255,151), (107,255,147), (111,255,143), (115,255,139), (119,255,135), (123,255,131), (127,255,127), (131,255,123), (135,255,119), (139,255,115),
    (143,255,111), (147,255,107), (151,255,103), (155,255,99), (159,255,95), (163,255,91), (167,255,87), (171,255,83), (175,255,79), (179,255,75), (183,255,71), (187,255,67),
    (191,255,63), (195,255,59), (199,255,55), (203,255,51), (207,255,47), (211,255,43), (215,255,39), (219,255,35), (223,255,31), (227,255,27), (231,255,23), (235,255,19),
    (239,255,15), (243,255,11), (247,255,7), (251,255,3), (255,255,0), (255,251,0), (255,247,0), (255,243,0), (255,239,0), (255,235,0), (255,231,0), (255,227,0), (255,223,0),
    (255,219,0), (255,215,0), (255,211,0), (255,207,0), (255,203,0), (255,199,0), (255,195,0), (255,191,0), (255,187,0), (255,183,0), (255,179,0), (255,175,0), (255,171,0),
    (255,167,0), (255,163,0), (255,159,0), (255,155,0), (255,151,0), (255,147,0), (255,143,0), (255,139,0), (255,135,0), (255,131,0), (255,127,0), (255,123,0), (255,119,0),
    (255,115,0), (255,111,0), (255,107,0), (255,103,0), (255,99,0), (255,95,0), (255,91,0), (255,87,0), (255,83,0), (255,79,0), (255,75,0), (255,71,0), (255,67,0), (255,63,0),
    (255,59,0), (255,55,0), (255,51,0), (255,47,0), (255,43,0), (255,39,0), (255,35,0), (255,31,0), (255,27,0), (255,23,0), (255,19,0), (255,15,0), (255,11,0), (255,7,0),
    (255,3,0), (255,0,0), (250,0,0), (246,0,0), (241,0,0), (237,0,0), (233,0,0), (228,0,0), (224,0,0), (219,0,0), (215,0,0), (211,0,0), (206,0,0), (202,0,0), (197,0,0),(193,0,0),
    (189,0,0), (184,0,0), (180,0,0), (175,0,0), (171,0,0), (167,0,0), (162,0,0), (158,0,0), (153,0,0), (149,0,0), (145,0,0), (140,0,0), (136,0,0), (131,0,0), (131,0,0)
]

### Arguments ###
argparser = argparse.ArgumentParser(description="GK-2A Infrared Colour Enhancement")
argparser.add_argument("INPUT", action="store", help="Input image path")
argparser.add_argument("--hot", action="store", help="Hotter limit in Kelvin (275K by default)", default=275)
argparser.add_argument("--cold", action="store", help="Colder limit in Kelvin (230K by default)", default=230)
argparser.add_argument("-s", action="store_true", help="Disable drawing of LUT and text", default=False)
argparser.add_argument("-o", action="store_true", help="Overwrite existing enhanced images", default=False)
argparser.add_argument("-t", action="store_true", help="Output only enhanced areas as a transparent PNG", default=False)
args = argparser.parse_args()


### Globals ###
input = None                # Input image
output = None               # Output image
outext = "_ENHANCED.jpg"    # Output extension
files = []                  # Multi-file list
lut = []                    # Final LUT
kelvin = []                 # Kelvin conversion table
alpha = []                  # Alpha mask
gradh = 50                  # Gradient height
hotI = None                 # Hot temperature index
coldI = None                # Cold temperature index


def init():
    gen_luts()

    # Output PNG in transparent mode
    if args.t:
        global outext
        outext = "_ENHANCED.png"

    handle_input(args.INPUT)


def gen_luts():
    """
    Generates gradient and Kelvin lookup tables
    """

    global kelvin
    global lut
    global hotI
    global coldI
    global alpha

    # Generate base 8-bit grayscale LUT
    for i in range(256):
        lut.append((i, i, i))
    
    # Setup interpolation points
    xp = []
    for i in range(len(cal)):
        m = 256 / len(cal)
        xp.append((i+1) * m)
    
    # Interpolate conversion table
    for i in range(256):
        k = round(np.interp(i, xp, cal), 3)
        kelvin.append(k)
    
    # Find nearest Kelvin CLUT bounds indicies
    hotI = get_nearest(float(args.hot), kelvin)
    coldI = get_nearest(float(args.cold), kelvin)

    # Get scale factor for CLUT
    scale = (len(clut) / (coldI - hotI))

    # Scale CLUT
    sclut = []
    for i in range(coldI - hotI):
        idx = round(i * scale)
        if idx > 255: idx = 255
        sclut.append(clut[idx])
    
    # Insert CLUT into LUT
    for i in range(len(sclut)):
        cf = 10
        if i <= cf:
            # Crossfade LUTs
            r = int(sclut[i][0] * (i / cf)) + int(lut[hotI + i][0] * ((cf - i) / cf))
            g = int(sclut[i][1] * (i / cf)) + int(lut[hotI + i][1] * ((cf - i) / cf))
            b = int(sclut[i][2] * (i / cf)) + int(lut[hotI + i][2] * ((cf - i) / cf))
            lut[hotI + i] = (r, g, b)
        else:
            lut[hotI + i] = sclut[i]
    
    # Generate alpha mask
    if args.t:
        for i in range(len(lut)):
            if i < hotI:
                alpha.append(0)
            elif hotI <= i <= coldI:
                alpha.append(255)
            elif i > coldI:
                alpha.append(0)


def handle_input(path):
    """
    Load input image/path
    """

    global input

    if (os.path.isdir(path)):  # Input is folder
        # Find IMG files in input folder
        for f in glob.glob(args.INPUT + "/IMG_*.jpg"):
            if outext not in f: files.append(f)
        files.sort()

        # Warn when no files found
        if files.__len__() <= 0:
            print("No \"IMG_*.jpg\" files found")
            exit(1)

        # Print file list
        print("Found {} files: ".format(len(files)))
        for f in files:
            print("  {}".format(f))
        print("-----------------------------------------\n")

        # Process files
        for f in files:
            name = os.path.splitext(f)[0]
            print("Processing {}...".format(name))

            # Check image has not already been generated
            if os.path.isfile(name + outext) and not args.o:
                print("  FILE ALREADY GENERATED...SKIPPING (use -o to overwrite existing files)\n")
                continue

            # Process image file
            input = Image.open(open(f, mode="rb")).convert('L')
            process(input)
            output.save(name + outext)
            print("  Saved {}".format(name + outext))
            print()

    else:  # Input is file
        name = os.path.splitext(ntpath.basename(path))[0]
        print("Processing {}...".format(name))
        
        input = Image.open(open(path, mode="rb")).convert('L')
        process(input)

        output.save(name + outext)
        print("  Saved {}".format(name + outext))
        print()


def process(img):
    """
    Processes input image
    """
    
    global output

    # Get dimensions of output image
    if args.s:
        h = img.height
    else:
        h = img.height + (gradh * 3)
    w = img.width

    # Create output image
    if args.t:
        # Transparent PNG
        output = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    else:
        # Normal JPEG
        output = Image.new("RGB", (w, h), (0, 0, 0))

    # Not simple mode
    if not args.s:
        draw = ImageDraw.Draw(output)
        scale = int(output.width / len(lut)) - 1
        dlen = len(lut) * scale
        xoff = (output.width - dlen) / 2

        # Draw LUT below image
        for i in range(len(lut)):
            for j in range(scale):
                start = (xoff + (i * scale) + j, img.height + (gradh / 2))
                end = (xoff + (i * scale) + j, img.height + (gradh * 1.5))
                draw.line([start, end], fill=lut[i])

        # Draw LUT border
        rmar = 6
        p1 = (xoff - rmar, img.height + (gradh / 2) - rmar)
        p2 = (xoff + dlen + rmar, output.height - (gradh * 1.5) + rmar)
        draw.rectangle((p1, p2), outline=(0xFF, 0xFF, 0xFF), width=3)

        # Try load Arial Bold font
        try:
            fnt = ImageFont.truetype("arialbd.ttf", size=38)
        except OSError:
            print("  UNABLE TO LOAD FONT \"arialbd.ttf\"")
            fnt = None

        if fnt:
            # Draw LUT text
            col = (0xFF, 0xFF, 0xFF, 0xFF)
            text = "{}K".format(round(cal[0]))
            draw.text((xoff / 2 - 10, img.height + (gradh / 2) + 3), text, fill=col, font=fnt)   # Start
            text = "{}K".format(round(cal[7]))
            draw.text((w - xoff + 30, img.height + (gradh / 2) + 3), text, fill=col, font=fnt)   # End
            text = "{}K".format(args.hot)
            draw.text((xoff + (hotI * scale) - 40, output.height - gradh - rmar), text, fill=col, font=fnt)   # Hot
            text = "{}K".format(args.cold)
            draw.text((xoff + (coldI * scale) - 40, output.height - gradh - rmar), text, fill=col, font=fnt)   # Cold

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
    gray = np.array(input)
    
    # Apply each channel of LUT to grayscale image
    enhR = nplutR[gray]
    enhG = nplutG[gray]
    enhB = nplutB[gray]

    # Convert enhanced arrays to images
    iR = Image.fromarray(enhR).convert('L')
    iG = Image.fromarray(enhG).convert('L')
    iB = Image.fromarray(enhB).convert('L')
    
    # Combine enhanced channels into an RGB(A) image
    if args.t:
        # Convert alpha list to np array
        nplutA = np.asarray(alpha)
        
        # Apply alpha mask to image
        enhA = nplutA[gray]

        # Convert alpha mask to image
        iA = Image.fromarray(enhA).convert('L')

        # Merge channels
        i = Image.merge("RGBA", (iR, iG, iB, iA))
    else:
        # Merge channels
        i = Image.merge("RGB", (iR, iG, iB))


    # Paste enhanced image in output image
    output.paste(i)


def show_lut(lut):
    """
    Renders an image of LUT
    """

    image = Image.new("RGB", (len(lut), 40), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    for x in range(len(lut)):
        draw.line([(x, 0), (x, 40)], fill=lut[x])
    
    image.show()


def get_nearest(v, l):
    """
    Returns the index of the nearest value in a list
    """

    for i in range(len(l)):
        if l[i] < v:
            prev = l[i - 1]
            prevDiff = prev - v

            curr = l[i]
            currDiff = v - curr

            if prevDiff < currDiff:
                return i-1
            else:
                return i
    
    # If value larger than list values, return last list index
    return len(l) - 1


try:
    init()
except KeyboardInterrupt:
    print("Exiting...")
    exit()
