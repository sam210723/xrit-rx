import argparse

argp = argparse.ArgumentParser(description="Converts 1024 byte CADUs to 892 byte VCDUs")
argp.add_argument("cadu", help="Input CADU file")
argp.add_argument("vcdu", help="Output VCDU file")
args = argp.parse_args()

print(f"Opening {args.cadu}...")
caduf = open(args.cadu, "rb")

print(f"Writing {args.vcdu}...")
vcduf = open(args.vcdu, "wb")

while True:
    cadu = caduf.read(1024)
    if cadu == b'': break

    vcdu = cadu[4 : 892 + 4]
    vcduf.write(vcdu)

caduf.close()
vcduf.close()
print("Finished processing\nExiting")
exit(0)
