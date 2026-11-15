#!/usr/bin/env python3
"""Control4 Vibrant Firmware app: refresh the Zigbee2MQTT OTA index on a timer.

Every check_interval_hours it asks Control4's public driver API for the newest
Vibrant Smart Bulb driver, downloads it only when the version changed, extracts
the bulb firmware and rewrites <zigbee2mqtt_data_dir>/ota/vibrant-ota-index.json
(merged with any indexes listed in merge_indexes).
"""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

OPTIONS = Path("/data/options.json")
CACHE = Path("/data/cache")


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


ICONS = Path("/app/icons")


def install_icons(z2m: Path) -> None:
    """Copy the bulb icons into Zigbee2MQTT's device_icons folder (only if changed)."""
    dest = z2m / "device_icons"
    dest.mkdir(exist_ok=True)
    for src in sorted(ICONS.glob("*.png")):
        target = dest / src.name
        if not target.exists() or target.read_bytes() != src.read_bytes():
            shutil.copyfile(src, target)
            log(f"Installed icon {target}")


def run_once(opts: dict) -> bool:
    z2m = Path(opts["zigbee2mqtt_data_dir"])
    if not (z2m / "configuration.yaml").exists():
        log(f"ERROR: no Zigbee2MQTT configuration.yaml in {z2m}; check zigbee2mqtt_data_dir")
        return False
    try:
        install_icons(z2m)
    except OSError as e:
        log(f"WARNING: could not install icons: {e}")
    cmd = [
        sys.executable, "/app/extract_firmware.py", "--from-control4",
        "--out", str(z2m / "ota"), "--prefix", "ota", "--cache-dir", str(CACHE),
    ]
    for src in opts.get("merge_indexes") or []:
        cmd += ["--merge", src]
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in (result.stdout + result.stderr).splitlines():
        if line.startswith("Copy the folder"):
            break  # the script's manual-install hint doesn't apply inside the app
        if line.strip():
            log(line)
    if result.returncode != 0:
        log(f"ERROR: update failed (exit {result.returncode}); will retry next interval")
        return False
    log("Update list is current. Zigbee2MQTT needs, once, in its configuration.yaml:")
    log("  ota:")
    log("    zigbee_ota_override_index_location: ota/vibrant-ota-index.json")
    return True


def main() -> None:
    opts = json.loads(OPTIONS.read_text())
    hours = int(opts.get("check_interval_hours", 24))
    log(f"Control4 Vibrant Firmware app started; checking every {hours} h")
    while True:
        try:
            run_once(opts)
        except Exception as e:  # keep the app alive across transient errors
            log(f"ERROR: {e}")
        time.sleep(hours * 3600)


if __name__ == "__main__":
    main()
