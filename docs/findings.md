# Findings: VB-FTW-A19 on Zigbee2MQTT

Test bulb: IEEE `0x000fff000057f639`, Zigbee2MQTT 2.14.3, 14 Nov 2026.

## Identity

- Manufacturer `Control4`, model ID `C4-VB-FTW-A19`, hardware version 0.
- Shipped firmware 6.3.18 (`0x06030012`, file version 100859922), older than the driver's first
  release candidate (6.7.34).

## Endpoints and clusters

Endpoints **1** and **196** (0xC4) expose the same clusters:

- Input: genBasic, genIdentify, genGroups, genScenes, genOnOff, genLevelCtrl, haDiagnostic,
  lightingColorCtrl, msTemperatureMeasurement, and manufacturer-specific 64512, 64514, 64516,
  64517, 64519, 64767.
- Output: genTime, genOta, keepAlive.

Zigbee2MQTT's generated definition turned endpoint 196 into a second light. The converter
uses endpoint 1 only.

## Brightness: 0–100 scale

- `moveToLevelWithOnOff` above 100 is ignored (no error, level unchanged). A transition time
  does not change this.
- Turning on from off goes to level 100, which is full brightness.
- Level 50 looks about half; 50 → 80 works. Confirmed on 6.3.18 and 6.9.134.

## Color

- `colorCapabilities` = 24 (XY + color temperature). The FTW bulb is exposed as color
  temperature only.
- `colorTempPhysicalMin/Max` reads fail; the range comes from the spec sheet (1800–6500 K).
- 555, 153 and 370 mireds were all set and read back correctly.

## Other behavior

- Binding `msTemperatureMeasurement` returns `NOT_AUTHORIZED`, so configuration failed until
  the temperature sensor was removed from the definition.
- On 6.3.18 the bulb sent a device announce every 50–80 s (not reboots: an OTA transfer ran
  through them). This stopped after the update to 6.9.134.

## Firmware

- Images live in the driver's `www/` folder as standard Zigbee OTA files: magic `0x0BEEF11E`,
  manufacturer code `0x1040`, header string = model ID.
- Version encoding: major.minor.build as `0xMMmmBBBB` (6.9.134 = `0x06090086`).
- A19 update over Zigbee2MQTT: 5,223 blocks, about 37 minutes, applied and rebooted on its own.
- The Lua in the driver is encrypted; the XML and documentation are readable.

# Findings: VB-RGBTW-A19

Test bulb: IEEE `0x000fff0000581281`, Zigbee2MQTT 2.14.3, 14 Nov 2026.

- Model ID `C4-VB-RGBTW-A19`; shipped on firmware 6.3.18, same endpoint layout as the FTW
  (endpoints 1 and 196, same clusters, same `msTemperatureMeasurement` bind refusal).
- Same 0–100 brightness scale as the FTW; the same converter fix works (100% = 254, 50% = 127).
- XY color uses standard values: red 0.701/0.299, green 0.172/0.747, blue 0.136/0.040 were set and
  read back. Switching from color back to color temperature (370 mireds) works.
- Reading `enhancedCurrentHue` / `currentSaturation` returns `UNSUPPORTED_ATTRIBUTE`, so the
  converter exposes XY only. With hue/saturation declared, Zigbee2MQTT's combined color reads fail.
- On 6.3.18 the bulb answered Zigbee2MQTT's manual update check; the update to 6.9.134 was offered
  from the app-generated index and installed in about 40 minutes (5,199 blocks).
- After the update, like the FTW, the bulb ignores the manual update check
  (`Not supported (Router)` at Zigbee2MQTT startup).

# Firmware via the Home Assistant app

- Control4's public driver API
  (`drivers.control4.com/api/v1/public/drivers/by-filename/control4_smart_bulb.c4z`) returns the
  driver version and a short-lived signed CloudFront download URL; no login is needed.
- The app downloads the driver only when the version changes, extracts all seven images and writes
  the index (merged with any existing override index). Tested on Home Assistant OS 18.4.
