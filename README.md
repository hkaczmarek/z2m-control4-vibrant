# Control4 Vibrant bulbs on Zigbee2MQTT

Zigbee2MQTT support for Control4 Vibrant Zigbee 3.0 smart bulbs, plus a Home Assistant app that
keeps their firmware updates coming, downloaded straight from Control4's public driver site.

> **Status:** VB-FTW-A19 and VB-RGBTW-A19 are tested on real hardware, including automatic
> firmware updates through the Home Assistant app. The other Vibrant models (BR20, BR30, REC4,
> REC6) are not tested yet; their firmware is already handled by the app.

## What works

| Feature | VB-FTW-A19 | VB-RGBTW-A19 |
|---|---|---|
| On / off | ✅ | ✅ |
| Brightness, both directions (see [why a custom converter](#why-a-custom-converter)) | ✅ | ✅ |
| Color temperature 1800–6500 K (153–555 mireds) | ✅ | ✅ |
| Color (XY) | — | ✅ (the bulb has no hue/saturation attributes) |
| Firmware update via Zigbee2MQTT | ✅ 6.3.18 → 6.9.134 | ✅ 6.3.18 → 6.9.134, offered and installed automatically |
| Control4 extras (Daylight Mode, group scenes, manufacturer clusters) | ❌ | ❌ |

Tested with Zigbee2MQTT 2.14.3.

## 1. Install the converters

Until these bulbs are supported in Zigbee2MQTT itself:

1. Copy the files from `converters/` into the `external_converters` folder next to your
   Zigbee2MQTT `configuration.yaml` (Zigbee2MQTT 2.11+ also needs `advanced.enable_external_js`).
2. Restart Zigbee2MQTT. Bulbs that were already paired pick up the new definition after the restart.

The bulb should show as **Vibrant Fully Tunable White A19 Lamp** (or **Vibrant RGB Tunable White
A19 Lamp**) with a single light.

**Icons (optional):** the app (below) copies two bulb icons into Zigbee2MQTT's `device_icons`
folder; the same files are in `device_icons/` here. In the Zigbee2MQTT frontend open the bulb →
**Settings** → **Icon** and enter `device_icons/control4-vibrant-ftw.png` or
`device_icons/control4-vibrant-rgbtw.png`.

## 2. Firmware updates (Home Assistant app)

Bulbs can ship with old firmware (ours had pre-release 6.3.18). The firmware is **not** in this
repository. The app downloads Control4's **Vibrant Smart Bulb** driver from Control4's public
driver API, extracts the bulb firmware and keeps Zigbee2MQTT's update list current.

1. In Home Assistant: **Settings → Apps → Repositories**, add
   `https://github.com/hkaczmarek/z2m-control4-vibrant`.
2. Install and start **Control4 Vibrant Firmware**. Its log should say `Update list is current`.
3. Add this to Zigbee2MQTT's `configuration.yaml` once, then restart Zigbee2MQTT:

   ```yaml
   ota:
     zigbee_ota_override_index_location: ota/vibrant-ota-index.json
   ```

   Zigbee2MQTT accepts only **one** override index. If you already have one (for example for
   custom switch firmware), put that URL into the app's `merge_indexes` option instead.

Home Assistant then shows Vibrant firmware updates like any other update. An A19 update takes
about 35 minutes; keep the lamp powered. Updating through a non-Control4 controller may affect
Control4 warranty support.

Note: on firmware 6.9.134 the bulb ignores Zigbee2MQTT's manual "check for update" request
(older firmware answers it). Updates are still offered when the bulb asks on its own.

### Without the app

`tools/extract_firmware.py` does the same job by hand:

```sh
# download the newest driver from Control4 and build the list
python3 tools/extract_firmware.py --from-control4 --out ota
# or use a driver you downloaded yourself
python3 tools/extract_firmware.py control4_smart_bulb.c4z --out ota
# keep an existing override index
python3 tools/extract_firmware.py --from-control4 --out ota --merge https://example.com/index.json
```

Copy the `ota` folder into the Zigbee2MQTT data directory and set the config line above. For a
single bulb you can also use the Zigbee2MQTT frontend: **OTA → pick the bulb → Source: Custom
firmware** and upload the `.zigbee` file for your model.

## Why a custom converter

The bulb's Level Control cluster uses a **0–100 scale** instead of the Zigbee standard 0–254.
It silently ignores any `moveToLevel` above 100 and reports `currentLevel` as 0–100, so with a
generic definition the bulb dims down but never up. The converter scales brightness between
0–254 and 0–100 for set, step, move and reports. Color temperature uses standard mireds.

The bulb also jumps to full brightness on a plain "on" command. The converter turns it on at
its last brightness instead, so it comes back where you left it and Home Assistant stays in step.

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
| C4-VB-RGBTW-A19 | Color + tunable white A19 | 0x040A | ✅ tested |
| C4-VB-RGBTW-BR30 | Color + tunable white BR30 | 0x040B | planned |

Not affiliated with Control4 or Snap One. Control4 and Vibrant are trademarks of their owners.
