# Control4 Vibrant Firmware

Keeps Zigbee2MQTT's firmware update list current for Control4 Vibrant smart bulbs.

Once a day (configurable) the app asks Control4's public driver site for the newest
**Vibrant Smart Bulb** driver, downloads it only when a new version is out, extracts the bulb
firmware and writes `ota/vibrant-ota-index.json` into your Zigbee2MQTT folder. Zigbee2MQTT then
shows firmware updates for your Vibrant bulbs like any other update in Home Assistant.

The firmware comes straight from Control4's servers to your system; it is never stored in this
repository.

## Setup

1. Install and start this app.
2. Check the app log: it should say `Update list is current`.
3. Add this to Zigbee2MQTT's `configuration.yaml` (once), then restart Zigbee2MQTT:

   ```yaml
   ota:
     zigbee_ota_override_index_location: ota/vibrant-ota-index.json
   ```

   If you already have a `zigbee_ota_override_index_location` (for example for custom switch
   firmware), put that URL into this app's `merge_indexes` option instead, so both keep working.

The app also copies two bulb icons into Zigbee2MQTT's `device_icons` folder. To use one, open
the bulb in the Zigbee2MQTT frontend, go to **Settings** and set **Icon** to
`device_icons/control4-vibrant-ftw.png` (tunable white) or
`device_icons/control4-vibrant-rgbtw.png` (color).

You also need the Vibrant converters from this repository until they are part of Zigbee2MQTT.

## Options

| Option | Default | Meaning |
|---|---|---|
| `zigbee2mqtt_data_dir` | `/homeassistant/zigbee2mqtt` | Folder holding Zigbee2MQTT's `configuration.yaml` |
| `check_interval_hours` | `24` | How often to check Control4 for a new driver |
| `merge_indexes` | empty | Other OTA index URLs or files to include (Zigbee2MQTT allows only one) |

## Notes

- Updating takes about 35 minutes per bulb; keep the lamp powered.
- Updating through a non-Control4 controller may affect Control4 warranty support.
- Not affiliated with Control4 or Snap One.
