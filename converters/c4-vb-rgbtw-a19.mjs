// Control4 Vibrant RGB Tunable White A19 Lamp (VB-RGBTW-A19)
//
// The bulb's genLevelCtrl uses a 0-100 (percent) scale instead of the
// standard 0-254: it rejects any moveToLevel above 100 and reports
// currentLevel 0-100. This converter scales brightness between
// Zigbee2MQTT's 0-254 and the bulb's 0-100 in both directions.

import * as m from 'zigbee-herdsman-converters/lib/modernExtend';
import * as tz from 'zigbee-herdsman-converters/converters/toZigbee';
import * as fz from 'zigbee-herdsman-converters/converters/fromZigbee';

const DEV_MAX = 100;
const Z2M_MAX = 254;

// 0-254 -> 0-100 (never round a non-zero level down to 0, which would mean off)
const toDev = (v) => {
    const n = Number(v);
    if (!(n > 0)) return 0;
    return Math.min(DEV_MAX, Math.max(1, Math.round((n * DEV_MAX) / Z2M_MAX)));
};
// 0-100 -> 0-254
const toZ2m = (v) => Math.min(Z2M_MAX, Math.max(0, Math.round((Number(v) * Z2M_MAX) / DEV_MAX)));
// signed step/rate values: scale magnitude, keep sign, keep at least 1
const toDevSigned = (v) => {
    const n = Number(v);
    if (n === 0 || Number.isNaN(n)) return n;
    return Math.sign(n) * Math.max(1, Math.round((Math.abs(n) * DEV_MAX) / Z2M_MAX));
};

function scaleResult(result) {
    if (result && result.state && result.state.brightness != null) {
        result.state.brightness = toZ2m(result.state.brightness);
    }
    return result;
}

// Wrap a toZigbee converter so it sees brightness in the bulb's 0-100 scale.
function scaledTz(conv) {
    return {
        ...conv,
        convertSet: async (entity, key, value, meta) => {
            const message = {...meta.message};
            if (message.brightness_percent != null) {
                message.brightness = Math.min(DEV_MAX, Math.max(0, Math.round(Number(message.brightness_percent))));
                delete message.brightness_percent;
            } else if (message.brightness != null) {
                message.brightness = toDev(message.brightness === 255 ? 254 : message.brightness);
            }
            for (const k of ['brightness_step', 'brightness_step_onoff', 'brightness_move', 'brightness_move_onoff']) {
                if (message[k] != null && message[k] !== 'stop') message[k] = toDevSigned(message[k]);
            }
            const state = {...meta.state};
            if (state.brightness != null) state.brightness = toDev(state.brightness);

            let v = value;
            if (key in message) v = message[key];
            if (key === 'brightness_percent') v = message.brightness;

            const result = await conv.convertSet(entity, key, v, {...meta, message, state});
            return scaleResult(result);
        },
    };
}

// Wrap fz.brightness so reported currentLevel (0-100) becomes 0-254.
const fzBrightnessScaled = {
    ...fz.brightness,
    convert: (model, msg, publish, options, meta) => {
        const out = fz.brightness.convert(model, msg, publish, options, meta);
        if (out) {
            for (const k of Object.keys(out)) {
                if (k.startsWith('brightness') && typeof out[k] === 'number') out[k] = toZ2m(out[k]);
            }
        }
        return out;
    },
};

const tzMap = new Map([
    [tz.light_onoff_brightness, scaledTz(tz.light_onoff_brightness)],
    [tz.light_brightness_step, scaledTz(tz.light_brightness_step)],
    [tz.light_brightness_move, scaledTz(tz.light_brightness_move)],
]);

const lightExtend = m.light({colorTemp: {range: [153, 555]}, color: {modes: ['xy']}});
lightExtend.toZigbee = lightExtend.toZigbee.map((c) => tzMap.get(c) ?? c);
lightExtend.fromZigbee = lightExtend.fromZigbee.map((c) => (c === fz.brightness ? fzBrightnessScaled : c));

export default {
    zigbeeModel: ['C4-VB-RGBTW-A19'],
    model: 'VB-RGBTW-A19',
    vendor: 'Control4',
    description: 'Vibrant RGB Tunable White A19 Lamp',
    extend: [m.identify(), lightExtend],
    ota: true,
};
