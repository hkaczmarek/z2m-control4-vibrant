// Control4 Vibrant RGB tunable white A19 lamp (VB-RGBTW-A19)
//
// Same code as the built-in definition merged into zigbee-herdsman-converters
// (Koenkk/zigbee-herdsman-converters#13829, release 26.133.0). Only needed until
// your Zigbee2MQTT version includes that release; then delete this file.
//
// The bulb's genLevelCtrl uses a 0-100 scale instead of 0-254, and a plain "on"
// makes it jump to full brightness instead of its previous level.
import * as fz from 'zigbee-herdsman-converters/converters/fromZigbee';
import * as tz from 'zigbee-herdsman-converters/converters/toZigbee';
import * as m from 'zigbee-herdsman-converters/lib/modernExtend';
import * as utils from 'zigbee-herdsman-converters/lib/utils';

// genLevelCtrl uses a 0-100 scale instead of 0-254 (moveToLevel above 100 is ignored)
const vibrantLight = (args) => {
    const scale = (value, from, to) => (value == null ? value : Math.round((Number(value) * to) / from));
    const tzBrightness = {
        ...tz.light_onoff_brightness,
        convertSet: async (entity, key, value, meta) => {
            const {brightness_percent: percent, ...message} = meta.message;
            if (percent != null) message.brightness = utils.mapNumberRange(Number(percent), 0, 100, 0, 254);
            // A plain "on" makes the bulb go to full brightness instead of its previous level
            const onOff = typeof message.state === 'string' ? message.state.toUpperCase() : undefined;
            if (
                message.brightness == null &&
                meta.state.brightness != null &&
                (onOff === 'ON' || (onOff === 'TOGGLE' && meta.state.state === 'OFF'))
            ) {
                message.state = 'ON';
                message.brightness = meta.state.brightness;
            }
            message.brightness = scale(message.brightness, 254, 100);
            const state = {...meta.state, brightness: scale(meta.state.brightness, 254, 100)};
            const result = await tz.light_onoff_brightness.convertSet(entity, key, value, {...meta, message, state});
            if (result && result.state?.brightness != null) result.state.brightness = scale(result.state.brightness, 100, 254);
            return result;
        },
    };
    const fzBrightness = {
        ...fz.brightness,
        convert: (model, msg, publish, options, meta) => {
            const result = fz.brightness.convert(model, msg, publish, options, meta);
            if (result?.brightness != null) result.brightness = scale(result.brightness, 100, 254);
            return result;
        },
    };
    const extend = m.light(args);
    extend.toZigbee = extend.toZigbee.map((c) => (c === tz.light_onoff_brightness ? tzBrightness : c));
    extend.fromZigbee = extend.fromZigbee.map((c) => (c === fz.brightness ? fzBrightness : c));
    return extend;
};

export default {
    zigbeeModel: ['C4-VB-RGBTW-A19'],
    model: 'VB-RGBTW-A19',
    vendor: 'Control4',
    description: 'Vibrant RGB tunable white A19 lamp',
    extend: [m.identify(), vibrantLight({colorTemp: {range: [153, 555]}, color: {modes: ['xy']}})],
    ota: true,
};
