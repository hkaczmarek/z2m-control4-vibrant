#!/usr/bin/env python3
"""Extract Control4 Vibrant bulb firmware from the official driver for Zigbee2MQTT.

The Control4 "Vibrant Smart Bulb" driver (control4_smart_bulb.c4z) ships the
bulbs' Zigbee OTA images in its www/ folder. This script pulls those images
out of a .c4z you downloaded yourself, checks that each one is a valid Zigbee
OTA file, and writes a Zigbee2MQTT override index pointing at them.

No firmware is included in this repository; you supply the .c4z.

Usage:
    python3 extract_firmware.py control4_smart_bulb.c4z [--out DIR] [--prefix PATH]

    --out     where to write the images and index (default: ./ota)
    --prefix  the path Zigbee2MQTT should use for the images, relative to its
              data directory (default: the name of --out, e.g. "ota")

Then copy the output folder into the Zigbee2MQTT data directory (the folder
holding configuration.yaml) and set in configuration.yaml:

    ota:
      zigbee_ota_override_index_location: ota/vibrant-ota-index.json
"""

import argparse
import hashlib
import json
import struct
import sys
import zipfile
from pathlib import Path

OTA_MAGIC = 0x0BEEF11E
CONTROL4_MFR = 0x1040


def parse_header(data: bytes) -> dict:
    if len(data) < 56:
        raise ValueError("file too short for an OTA header")
    magic, _hver, _hlen, _fctl, mfr, itype, fver, _stack = struct.unpack_from("<IHHHHHIH", data, 0)
    if magic != OTA_MAGIC:
        raise ValueError(f"not a Zigbee OTA file (magic 0x{magic:08X})")
    header_string = data[20:52].split(b"\0", 1)[0].decode("utf-8", "replace").strip()
    (total_size,) = struct.unpack_from("<I", data, 52)
    return {
        "manufacturerCode": mfr,
        "imageType": itype,
        "fileVersion": fver,
        "otaHeaderString": header_string,
        "totalImageSize": total_size,
    }


def version_str(v: int) -> str:
    # Control4 encodes 6.9.134 as 0x06090086 (major, minor, 16-bit build)
    return f"{(v >> 24) & 0xFF}.{(v >> 16) & 0xFF}.{v & 0xFFFF}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("c4z", type=Path, help="path to control4_smart_bulb.c4z")
    ap.add_argument("--out", type=Path, default=Path("ota"))
    ap.add_argument("--prefix", default=None)
    args = ap.parse_args()

    prefix = (args.prefix if args.prefix is not None else args.out.name).strip("/")
    args.out.mkdir(parents=True, exist_ok=True)

    index = []
    with zipfile.ZipFile(args.c4z) as z:
        names = sorted(n for n in z.namelist() if n.lower().endswith(".zigbee"))
        if not names:
            print("No .zigbee firmware images found in this driver.", file=sys.stderr)
            return 1
        for name in names:
            data = z.read(name)
            try:
                hdr = parse_header(data)
            except ValueError as e:
                print(f"skip {name}: {e}", file=sys.stderr)
                continue
            if hdr["manufacturerCode"] != CONTROL4_MFR:
                print(f"skip {name}: manufacturer 0x{hdr['manufacturerCode']:04X} is not Control4", file=sys.stderr)
                continue
            if hdr["totalImageSize"] != len(data):
                print(f"skip {name}: header size {hdr['totalImageSize']} != file size {len(data)}", file=sys.stderr)
                continue

            model = hdr["otaHeaderString"]
            ver = version_str(hdr["fileVersion"])
            file_name = f"{model}_{ver}.zigbee"
            (args.out / file_name).write_bytes(data)

            index.append({
                "fileName": file_name,
                "fileVersion": hdr["fileVersion"],
                "fileSize": len(data),
                "url": f"{prefix}/{file_name}",
                "imageType": hdr["imageType"],
                "manufacturerCode": hdr["manufacturerCode"],
                "sha512": hashlib.sha512(data).hexdigest(),
                "otaHeaderString": model,
                "modelId": model,
            })
            print(f"{model:18s} {ver:10s} image type 0x{hdr['imageType']:04X}  -> {args.out / file_name}")

    index_path = args.out / "vibrant-ota-index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    print(f"\nWrote {len(index)} images and {index_path}")
    print("Copy the folder into your Zigbee2MQTT data directory and set:")
    print(f"  ota:\n    zigbee_ota_override_index_location: {prefix}/{index_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
