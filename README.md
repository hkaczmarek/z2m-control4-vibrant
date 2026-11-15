# Control4 Vibrant bulbs on Zigbee2MQTT

Zigbee2MQTT support for Control4 Vibrant Zigbee 3.0 smart bulbs, plus a tool that pulls
the bulbs' firmware out of Control4's own driver so Zigbee2MQTT can update them.

> Status: work in progress. Only the **VB-FTW-A19** has been tested so far.

## What works (VB-FTW-A19, firmware 6.9.134, Zigbee2MQTT 2.14.3)

| Feature | Status |
|---|---|
| On / off | ✅ |
| Brightness, both directions (see [why a custom converter](#why-a-custom-converter)) | ✅ |
| Color temperature 1800–6500 K (153–555 mireds) | ✅ |
| Power-on behavior, identify, effects | ✅ (exposed, lightly tested) |
| Firmware update via Zigbee2MQTT OTA | ✅ 6.3.18 → 6.9.134 |
| Control4 extras (Daylight Mode, group scenes, manufacturer clusters) | ❌ not supported |

## Install the converter

1. Copy `converters/c4-vb-ftw-a19.mjs` into the `external_converters` folder next to your
   Zigbee2MQTT `configuration.yaml` (Zigbee2MQTT 2.11+ also needs `advanced.enable_external_js`).
2. Restart Zigbee2MQTT. A bulb that was already paired picks up the new definition after the restart.

The bulb should show as **Control4 VB-FTW-A19** with a single color-temperature light.

## Update the firmware

Bulbs can ship with old firmware (ours had pre-release 6.3.18). The firmware is **not** in this
repository; it comes from the Control4 **Vibrant Smart Bulb** driver (`control4_smart_bulb.c4z`),
available from the Control4 driver site.

```sh
python3 tools/extract_firmware.py control4_smart_bulb.c4z --out ota
```

This extracts one OTA image per Vibrant model, verifies each header, and writes
`ota/vibrant-ota-index.json`. Then either:

- **One bulb, by hand:** in the Zigbee2MQTT frontend open **OTA**, pick the bulb, choose
  **Source → Custom firmware**, select the `.zigbee` file for your model and press update; or
- **Through the index:** copy the `ota` folder into the Zigbee2MQTT data directory and set

  ```yaml
  ota:
    zigbee_ota_override_index_location: ota/vibrant-ota-index.json
  ```

  so Zigbee2MQTT's normal update check offers the new version.

  Zigbee2MQTT accepts only **one** override index. If you already use one (for example a
  custom-firmware project's index URL), merge it in instead of replacing it:

  ```sh
  python3 tools/extract_firmware.py control4_smart_bulb.c4z --out ota \
      --merge https://example.com/their/index.json
  ```

  Re-run the script now and then to pick up updates to the merged index.

An A19 update takes about 35 minutes. Leave the lamp powered while it runs. Updating through a
non-Control4 controller may affect Control4 warranty support.

## Why a custom converter

The bulb's Level Control cluster uses a **0–100 scale** instead of the Zigbee standard 0–254.
It silently ignores any `moveToLevel` above 100 and reports `currentLevel` as 0–100, so with a
generic definition the bulb dims down but never up. The converter scales brightness between
0–254 and 0–100 for set, step, move and reports. Color temperature uses standard mireds.

See [docs/findings.md](docs/findings.md) for the full notes.

## Models

From the driver's binding keys and firmware images:

| Model ID | Type | OTA image type | Converter |
|---|---|---|---|
| C4-VB-FTW-A19 | Tunable white A19 | 0x0405 | ✅ tested |
| C4-VB-FTW-REC6 | Tunable white 6" trim | 0x0406 | planned |
| C4-VB-FTW-REC4 | Tunable white 4" trim | 0x0407 | planned |
| C4-VB-FTW-BR30 | Tunable white BR30 | 0x0408 | planned |
| C4-VB-FTW-BR20 | Tunable white BR20 | 0x0409 | planned |
| C4-VB-RGBTW-A19 | Color + tunable white A19 | 0x040A | planned |
| C4-VB-RGBTW-BR30 | Color + tunable white BR30 | 0x040B | planned |

Not affiliated with Control4 or Snap One. Control4 and Vibrant are trademarks of their owners.
