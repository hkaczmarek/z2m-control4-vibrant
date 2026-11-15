#!/usr/bin/env python3
"""Extract Control4 Vibrant bulb firmware from the official driver for Zigbee2MQTT.

The Control4 "Vibrant Smart Bulb" driver (control4_smart_bulb.c4z) ships the
bulbs' Zigbee OTA images in its www/ folder. This script pulls those images
out of a .c4z you downloaded yourself, checks that each one is a valid Zigbee
OTA file, and writes a Zigbee2MQTT override index pointing at them.

No firmware is included in this repository; you supply the .c4z.

Usage:
    python3 extract_firmware.py control4_smart_bulb.c4z [--out DIR] [--prefix PATH]
                                [--merge URL_OR_FILE ...]
    python3 extract_firmware.py --from-control4 [--out DIR] [--merge ...]

    --out     where to write the images and index (default: ./ota)
    --prefix  the path Zigbee2MQTT should use for the images, relative to its
              data directory (default: the name of --out, e.g. "ota")
    --from-control4
              download the newest driver from Control4's public driver API
              (no login needed); skipped when the cached copy is current
    --merge   include another OTA index (URL or file) in the output. Zigbee2MQTT
              accepts only one override index, so if you already use one, merge
              it here. Re-run the script to pick up changes to merged indexes.

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


DRIVER_API = (
    "https://drivers.control4.com/api/v1/public/drivers/by-filename/"
    "control4_smart_bulb.c4z?osVersion=999999.0.0&fields=downloadUrl%2Cversion"
)


def fetch_driver(cache_dir: Path) -> Path:
    """Download the newest control4_smart_bulb.c4z from Control4's public driver API.

    The API returns a short-lived signed download URL plus the driver version.
    The .c4z and its version are cached in cache_dir; the download is skipped
    when the cached version is already the newest."""
    from urllib.request import Request, urlopen

    headers = {"User-Agent": "z2m-control4-vibrant/extract_firmware"}
    with urlopen(Request(DRIVER_API, headers=headers), timeout=30) as r:
        info = json.load(r)
    version, url = str(info.get("version", "")), info.get("downloadUrl")
    if not version or not url:
        raise SystemExit(f"unexpected answer from Control4 driver API: {info}")

    cached = cache_dir / "control4_smart_bulb.c4z"
    version_file = cache_dir / "control4_smart_bulb.version"
    if cached.exists() and version_file.exists() and version_file.read_text().strip() == version:
        print(f"Control4 driver {version} already downloaded")
        return cached

    print(f"Downloading Control4 driver {version} ...")
    with urlopen(Request(url, headers=headers), timeout=120) as r:
        data = r.read()
    if not zipfile.is_zipfile(__import__("io").BytesIO(data)):
        raise SystemExit("downloaded driver is not a valid .c4z (zip) file")
    tmp = cached.with_suffix(".tmp")
    tmp.write_bytes(data)
    tmp.replace(cached)
    version_file.write_text(version + "\n")
    print(f"Saved {cached} ({len(data)} bytes)")
    return cached


def load_index(source: str) -> list:
    """Load an OTA index from a URL or file. Entries must be self-contained
    (web URL plus imageType/manufacturerCode/fileVersion), as Zigbee2MQTT
    uses web-hosted override entries as-is."""
    if source.startswith(("http://", "https://")):
        from urllib.request import urlopen

        with urlopen(source, timeout=30) as r:
            data = json.load(r)
    else:
        data = json.loads(Path(source).read_text())
    if not isinstance(data, list):
        raise SystemExit(f"{source}: expected a JSON list of OTA entries")
    for i, e in enumerate(data):
        missing = [k for k in ("url", "imageType", "manufacturerCode", "fileVersion") if k not in e]
        if missing:
            raise SystemExit(f"{source}: entry {i} is missing {', '.join(missing)}")
    return data


def version_str(v: int) -> str:
    # Control4 encodes 6.9.134 as 0x06090086 (major, minor, 16-bit build)
    return f"{(v >> 24) & 0xFF}.{(v >> 16) & 0xFF}.{v & 0xFFFF}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("c4z", type=Path, nargs="?", help="path to control4_smart_bulb.c4z (omit with --from-control4)")
    ap.add_argument(
        "--from-control4",
        action="store_true",
        help="download the newest driver from Control4's public driver API instead of using a local .c4z; "
        "the download is skipped when the cached copy is already the newest version",
    )
    ap.add_argument("--out", type=Path, default=Path("ota"))
    ap.add_argument("--prefix", default=None)
    ap.add_argument(
        "--merge",
        action="append",
        default=[],
        metavar="URL_OR_FILE",
        help="another OTA index to include (repeatable). Zigbee2MQTT accepts only one "
        "override index, so use this to keep an index you already rely on.",
    )
    args = ap.parse_args()

    prefix = (args.prefix if args.prefix is not None else args.out.name).strip("/")
    args.out.mkdir(parents=True, exist_ok=True)

    if args.from_control4:
        args.c4z = fetch_driver(args.out)
    elif args.c4z is None:
        ap.error("give a .c4z path or use --from-control4")

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

    vibrant_count = len(index)
    for source in args.merge:
        entries = load_index(source)
        index.extend(entries)
        print(f"merged {len(entries)} entries from {source}")

    index_path = args.out / "vibrant-ota-index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    print(f"\nWrote {vibrant_count} Vibrant images and {index_path} ({len(index)} entries)")
    print("Copy the folder into your Zigbee2MQTT data directory and set:")
    print(f"  ota:\n    zigbee_ota_override_index_location: {prefix}/{index_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
