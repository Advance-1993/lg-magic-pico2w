#include "bridge_hid.h"
#if LG_ENABLE_HID
#include "pico/stdlib.h"
#include "pico/critical_section.h"
#include "tusb.h"
#include "usb_descriptors.h"
#include "diagnostic.h"
#include "btstack_tlv.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "mapping_config.h"
static mapping_config_t mappings;
static void load_mappings(void) {
    mapping_defaults(&mappings);
    const btstack_tlv_t *impl; void *context;
    btstack_tlv_get_instance(&impl,&context);
    mapping_config_t saved;
    bool valid=impl && impl->get_tag(context,MAP_TAG,(uint8_t *)&saved,sizeof(saved))==sizeof(saved) && mapping_valid(&saved);
    if (valid) mappings=saved;
    diag_log("MAP_CONFIG source=%s count=%u\n",valid ? "flash" : "defaults",MAP_COUNT);
}

// Only fields and buttons verified in labeled MR25GA captures are decoded.
typedef struct {
    uint8_t key;
    uint16_t consumer;
    int wheel;
    uint8_t buttons;
    bool mouse_mode;
    float dx, dy;
    uint32_t epoch, last_report_ms, mouse_last_activity_ms, last_activity_ms;
} state_t;
static critical_section_t lock;
static state_t desired;
#define MOUSE_IDLE_TIMEOUT_MS 120000u
// Defaults are measured from 900 stationary MR25GA samples, not an older model.
typedef struct { uint32_t magic; float bias[3]; uint32_t gain_milli; } gyro_config_t;
static gyro_config_t config={0x4C474331, {-4.571111f, 0.306667f, -0.876667f}, 12500};
#define GYRO_CONFIG_TAG 0x4C474331u
#define LEGACY_GYRO_CONFIG_TAG 0x4C474330u
static float filtered_x, filtered_y;
static uint32_t last_motion_ms;
static uint32_t click_freeze_until;
#define MOUSE_DRAG_HOLD_MS 200u
#define MOUSE_RELEASE_FREEZE_MS 120u
static uint32_t click_pressed_ms;
static bool dragging; // Core1 only; desired.buttons remains protected by lock.
static uint16_t last_code;
static unsigned calibration_samples;
static bool calibrating;
static int64_t sums[3], squares[3];
static int16_t min_sample[3], max_sample[3];

static void save_config(void) {
    const btstack_tlv_t *impl; void *context;
    btstack_tlv_get_instance(&impl, &context);
    if (!impl) { diag_log("GYRO config storage unavailable\n"); return; }
    int rc=impl->store_tag(context, GYRO_CONFIG_TAG, (const uint8_t *)&config, sizeof(config));
    gyro_config_t check;
    int n=impl->get_tag(context, GYRO_CONFIG_TAG, (uint8_t *)&check, sizeof(check));
    diag_log("GYRO config store rc=%d readback=%u\n", rc, n==sizeof(check) && !memcmp(&check,&config,sizeof(check)));
}
void bridge_hid_load_config(void) {
    load_mappings();
    const btstack_tlv_t *impl; void *context;
    btstack_tlv_get_instance(&impl, &context);
    gyro_config_t saved;
    bool valid=impl && impl->get_tag(context, GYRO_CONFIG_TAG, (uint8_t *)&saved, sizeof(saved))==sizeof(saved)
        && saved.magic==GYRO_CONFIG_TAG && saved.gain_milli>=1000 && saved.gain_milli<=100000;
    if (valid) for (unsigned i=0;i<3;++i) valid=valid && isfinite(saved.bias[i]) && fabsf(saved.bias[i])<100;
    const char *origin=valid ? "flash" : "measured defaults";
    if (!valid && impl && impl->get_tag(context, LEGACY_GYRO_CONFIG_TAG, (uint8_t *)&saved, sizeof(saved))==sizeof(saved)
        && saved.magic==LEGACY_GYRO_CONFIG_TAG && saved.gain_milli>=1 && saved.gain_milli<=100) {
        valid=true;
        for (unsigned i=0;i<3;++i) valid=valid && isfinite(saved.bias[i]) && fabsf(saved.bias[i])<100;
        if (valid) {
            saved.magic=GYRO_CONFIG_TAG;
            saved.gain_milli*=1000; // old record held integer gain in this field.
            origin="legacy migrated";
        }
    }
    if (valid) config=saved;
    diag_log("GYRO config=%s gain=%u.%03u; calibrated default bias available; mouse starts OFF\n", origin, config.gain_milli/1000, config.gain_milli%1000);
}
static bool parse_gain(const char *text, uint32_t *result) {
    uint32_t whole=0, fraction=0, place=100;
    unsigned digits=0;
    while (*text>='0' && *text<='9') {
        if (++digits>3) return false;
        whole=whole*10+(*text++-'0');
    }
    if (!digits) return false;
    if (*text=='.') {
        ++text; unsigned decimals=0;
        while (*text>='0' && *text<='9') {
            if (++decimals>3) return false;
            fraction+=(*text++-'0')*place; place/=10;
        }
        if (!decimals) return false;
    }
    if (*text || whole>100) return false;
    *result=whole*1000+fraction;
    return *result>=1000 && *result<=100000;
}
static void set_mouse_mode(bool on) {
    critical_section_enter_blocking(&lock);
    desired.mouse_mode=on;
    desired.key=0; desired.consumer=0; desired.buttons=0;
    desired.dx=0; desired.dy=0; desired.wheel=0; ++desired.epoch;
    desired.last_report_ms=to_ms_since_boot(get_absolute_time());
    desired.mouse_last_activity_ms=desired.last_report_ms;
    desired.last_activity_ms=desired.last_report_ms;
    critical_section_exit(&lock);
    filtered_x=0; filtered_y=0; last_motion_ms=0;
    click_freeze_until=to_ms_since_boot(get_absolute_time());click_pressed_ms=0;dragging=false;
    diag_log("MOUSE mode=%s; mapped pointer toggle, OK clicks, navigation exits\n", on ? "ON" : "OFF");
}

static void log_mapping(unsigned i) {
    const mapping_entry_t *e=&mappings.entries[i],*d=&mapping_default_entries[i];
    diag_log("MAP code=%04X kind=%s value=%04X default_kind=%s default_value=%04X\n",e->code,mapping_kind_name(e->kind),e->value,mapping_kind_name(d->kind),d->value);
}
static void save_mappings(const mapping_config_t *candidate) {
    const btstack_tlv_t *impl; void *context;
    btstack_tlv_get_instance(&impl,&context);
    int rc=-1; bool verified=false;
    if (impl) {
        rc=impl->store_tag(context,MAP_TAG,(const uint8_t *)candidate,sizeof(*candidate));
        mapping_config_t check;
        verified=rc==0 && impl->get_tag(context,MAP_TAG,(uint8_t *)&check,sizeof(check))==sizeof(check) && !memcmp(&check,candidate,sizeof(check));
    }
    if (verified) {
        set_mouse_mode(false); last_code=0; // neutral epoch before new mapping input.
        mappings=*candidate;
    }
    diag_log("MAP_STORE rc=%d readback=%u applied=%u\n",rc,verified,verified);
}
static bool mapping_command(const char *command) {
    if (!strcmp(command,"map list")) {
        for (unsigned i=0;i<MAP_COUNT;++i) log_mapping(i);
        diag_log("MAP_END count=%u\n",MAP_COUNT); return true;
    }
    if (!strcmp(command,"map reset")) {
        mapping_config_t candidate; mapping_defaults(&candidate); save_mappings(&candidate); return true;
    }
    if (!strncmp(command,"map set ",8)) {
        unsigned code,value; char kind[16],extra;
        if (sscanf(command,"map set %4x %15s %4x %c",&code,kind,&value,&extra)!=3) { diag_log("MAP_REJECT malformed command\n"); return true; }
        int index=mapping_index((uint16_t)code);
        uint8_t action=!strcmp(kind,"key") ? MAP_KEY : !strcmp(kind,"consumer") ? MAP_CONSUMER : !strcmp(kind,"pointer") ? MAP_POINTER : !strcmp(kind,"none") ? MAP_NONE : 255;
        if (index<0 || !mapping_value_valid((uint16_t)code,action,(uint16_t)value)) { diag_log("MAP_REJECT unsupported button/action/value\n"); return true; }
        mapping_config_t candidate=mappings;
        candidate.entries[index].kind=action; candidate.entries[index].value=(uint16_t)value;
        save_mappings(&candidate); return true;
    }
    return false;
}

bool bridge_hid_command(const char *command) {
    if (mapping_command(command)) return true;
    if (!strcmp(command,"mouse on")) { if (!calibrating) set_mouse_mode(true); return true; }
    if (!strcmp(command,"mouse off")) { set_mouse_mode(false); return true; }
    if (!strcmp(command,"mouse status")) {
        critical_section_enter_blocking(&lock);
        bool mode=desired.mouse_mode;
        uint32_t idle_ms=to_ms_since_boot(get_absolute_time())-desired.mouse_last_activity_ms;
        critical_section_exit(&lock);
        diag_log("GYRO mode=%u gain=%u.%03u calibrating=%u samples=%u bias_milli=%ld,%ld,%ld deadband=5 idle_timeout_ms=%u idle_ms=%lu\n", mode,config.gain_milli/1000,config.gain_milli%1000,calibrating,calibration_samples,
            (long)(config.bias[0]*1000), (long)(config.bias[1]*1000), (long)(config.bias[2]*1000), MOUSE_IDLE_TIMEOUT_MS, (unsigned long)(mode ? idle_ms : 0));
        return true;
    }
    if (!strcmp(command,"calibrate")) {
        set_mouse_mode(false);
        calibration_samples=0; memset(sums,0,sizeof(sums)); memset(squares,0,sizeof(squares));
        calibrating=true;
        diag_log("GYRO calibration START; leave remote still for 500 reports (about five seconds)\n");
        return true;
    }
    uint32_t gain;
    if (!strncmp(command,"mouse gain ",11)) {
        if (!parse_gain(command+11,&gain)) diag_log("GYRO gain rejected; range 1..100, at most three decimal places\n");
        else { config.gain_milli=gain; save_config(); }
        return true;
    }
    return false;
}
static void calibration_input(const int16_t gyro[3]) {
    for (unsigned i=0;i<3;++i) {
        if (!calibration_samples || gyro[i]<min_sample[i]) min_sample[i]=gyro[i];
        if (!calibration_samples || gyro[i]>max_sample[i]) max_sample[i]=gyro[i];
        sums[i]+=gyro[i]; squares[i]+=(int32_t)gyro[i]*gyro[i];
    }
    if (++calibration_samples<500) return;
    calibrating=false;
    bool valid=true;
    float bias[3];
    for (unsigned i=0;i<3;++i) {
        bias[i]=(float)sums[i]/calibration_samples;
        float variance=(float)squares[i]/calibration_samples-bias[i]*bias[i];
        if (variance>9 || max_sample[i]-min_sample[i]>20 || fabsf(bias[i])>=100) valid=false;
    }
    if (!valid) { diag_log("GYRO calibration REJECTED: remote moved; previous bias retained\n"); return; }
    memcpy(config.bias,bias,sizeof(bias));
    save_config();
    diag_log("GYRO calibration PASS bias_milli=%ld,%ld,%ld; mouse remains OFF\n", (long)(bias[0]*1000),(long)(bias[1]*1000),(long)(bias[2]*1000));
}
static float deadband(float value) {
    if (value>5) return value-5;
    if (value< -5) return value+5;
    return 0;
}

uint32_t bridge_hid_last_activity_ms(void) {
    critical_section_enter_blocking(&lock);uint32_t value=desired.last_activity_ms;critical_section_exit(&lock);return value;
}
void bridge_hid_note_activity(void) {
    critical_section_enter_blocking(&lock);desired.last_activity_ms=to_ms_since_boot(get_absolute_time());critical_section_exit(&lock);
}
void bridge_hid_init(void) { critical_section_init(&lock); }
void bridge_hid_disconnect(void) {
    critical_section_enter_blocking(&lock);
    desired.key = 0;
    desired.consumer = 0;
    desired.wheel = 0;
    desired.buttons=0; desired.dx=0; desired.dy=0; desired.mouse_mode=false;
    ++desired.epoch;
    critical_section_exit(&lock);
    last_code=0; filtered_x=0; filtered_y=0; last_motion_ms=0; click_freeze_until=0;click_pressed_ms=0;dragging=false; calibrating=false;
    diag_log("HID link down: neutral keyboard/mouse/consumer reports pending\n");
}
void bridge_hid_input(uint8_t id, const uint8_t *report, unsigned length) {
    if (id != 0xFD || length != 20 || report[0] != 0xFD) return;
    uint16_t code = ((uint16_t)report[17] << 8) | report[18];
    int16_t gyro[3];
    for (unsigned i=0;i<3;++i) gyro[i]=(int16_t)(((uint16_t)report[5+2*i]<<8)|report[6+2*i]);
    if (calibrating) calibration_input(gyro);
    critical_section_enter_blocking(&lock);
    bool mouse_mode=desired.mouse_mode;
    critical_section_exit(&lock);
    int map_index=mapping_index(code);
    mapping_entry_t entry=map_index>=0 ? mappings.entries[map_index] : (mapping_entry_t){0};
    if (entry.kind==MAP_POINTER && last_code!=code && !calibrating) { set_mouse_mode(!mouse_mode); mouse_mode=!mouse_mode; }
    bool navigation=code==0x8040 || code==0x8041 || code==0x8007 || code==0x8006 || code==0x8028 || code==0x807C || code==0x8002 || code==0x8003;
    if (navigation && entry.kind!=MAP_POINTER && mouse_mode) { set_mouse_mode(false); mouse_mode=false; }
    last_code=code;
    uint8_t key = 0;
    uint16_t consumer = 0;
    // Physical OK remains a stabilized mouse click while pointer mode is active.
    if (!(mouse_mode && code==0x8044)) {
        if (entry.kind==MAP_KEY) key=(uint8_t)entry.value;
        if (entry.kind==MAP_CONSUMER) consumer=entry.value;
    }
    critical_section_enter_blocking(&lock);
    uint8_t buttons=(mouse_mode && code==0x8044) ? MOUSE_BUTTON_LEFT : 0;
    bool changed = key != desired.key || consumer != desired.consumer || buttons != desired.buttons;
    uint32_t now=to_ms_since_boot(get_absolute_time());
    // Short clicks retain stabilization. A deliberate hold unlocks motion
    // while the ordinary USB left button stays down; release always drops it.
    bool drag_started=false,drag_released=false;
    if (buttons && !desired.buttons) {
        click_pressed_ms=now;dragging=false;click_freeze_until=now;
    }
    if (buttons && !dragging && (uint32_t)(now-click_pressed_ms)>=MOUSE_DRAG_HOLD_MS) {
        dragging=true;drag_started=true;
    }
    if (!buttons) {
        if (desired.buttons) click_freeze_until=now+MOUSE_RELEASE_FREEZE_MS;
        drag_released=dragging;dragging=false;click_pressed_ms=0;
    }
    desired.key = key;
    desired.consumer = consumer;
    desired.buttons=buttons;
    desired.last_report_ms = now;
    if (code || report[19]) desired.last_activity_ms=now;
    if (mouse_mode) {
        uint32_t elapsed=last_motion_ms ? now-last_motion_ms : 10;
        if (elapsed>40) elapsed=40;
        last_motion_ms=now;
        // Hardware gesture tests: right = +gyro Z, up = -gyro X.
        if ((buttons && !dragging) || (int32_t)(now-click_freeze_until)<0) {
            filtered_x=0; filtered_y=0; desired.dx=0; desired.dy=0;
        } else {
            float vx=deadband(gyro[2]-config.bias[2]);
            float vy=deadband(gyro[0]-config.bias[0]);
            filtered_x += 0.25f*(vx-filtered_x);
            filtered_y += 0.25f*(vy-filtered_y);
            desired.dx += filtered_x*elapsed*config.gain_milli/10000000.0f;
            desired.dy += filtered_y*elapsed*config.gain_milli/10000000.0f;
        }
        if (desired.dx>512) desired.dx=512;
        if (desired.dx< -512) desired.dx=-512;
        if (desired.dy>512) desired.dy=512;
        if (desired.dy< -512) desired.dy=-512;
    }
    desired.wheel += (int8_t)report[19];
    if (desired.wheel > 1024) desired.wheel=1024;
    if (desired.wheel < -1024) desired.wheel=-1024;
    critical_section_exit(&lock);
    if (drag_started) diag_log("MOUSE drag=ARMED hold_ms=%u; left button held, motion enabled\n",MOUSE_DRAG_HOLD_MS);
    if (drag_released) diag_log("MOUSE drag=RELEASED; left button up\n");
    if (changed || report[19]) diag_log("TRANSLATE code=%04X key=%02X consumer=%04X buttons=%u wheel=%d\n", code, key, consumer, buttons, (int)(int8_t)report[19]);
}
void bridge_hid_task(void) {
    static uint32_t sent_epoch = UINT32_MAX;
    static uint32_t release_epoch;
    static unsigned release_phase;
    static uint8_t sent_key;
    static uint16_t sent_consumer;
    static uint8_t sent_buttons;
    static bool mounted;
    if (!tud_mounted()) { mounted=false; return; }
    if (!mounted) {
        mounted=true;
        sent_epoch=UINT32_MAX;
        release_phase=0;
    }
    critical_section_enter_blocking(&lock);
    uint32_t now=to_ms_since_boot(get_absolute_time());
    bool mouse_idle=false;
    if ((desired.key || desired.consumer || desired.buttons || desired.mouse_mode) && now-desired.last_report_ms > 500) {
        desired.key=0; desired.consumer=0; desired.wheel=0; ++desired.epoch;
        desired.buttons=0; desired.dx=0; desired.dy=0; desired.mouse_mode=false;
    }
    // Do not change a held mouse click into an Enter hold by timing out mid-press.
    if (desired.mouse_mode && !desired.buttons && now-desired.mouse_last_activity_ms>=MOUSE_IDLE_TIMEOUT_MS) {
        desired.mouse_mode=false; desired.key=0; desired.consumer=0; desired.buttons=0;
        desired.wheel=0; desired.dx=0; desired.dy=0; ++desired.epoch;
        mouse_idle=true;
    }
    state_t state=desired;
    critical_section_exit(&lock);
    if (mouse_idle) diag_log("MOUSE mode=OFF reason=idle timeout_ms=%u; mapped pointer toggle re-enables; remote sleep not commanded\n", MOUSE_IDLE_TIMEOUT_MS);
    if (!tud_hid_ready()) return;
    // Epoch changes force all three neutral reports BEFORE any new input.
    // Keep retrying each report if USB is busy or suspended.
    if (sent_epoch != state.epoch) {
        if (!release_phase || release_epoch != state.epoch) {
            release_epoch=state.epoch; release_phase=1;
        }
        uint8_t zero[6]={0};
        bool ok=false;
        if (release_phase == 1) ok=tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, zero);
        if (release_phase == 2) ok=tud_hid_mouse_report(REPORT_ID_MOUSE, 0, 0, 0, 0, 0);
        if (release_phase == 3) { uint16_t usage=0; ok=tud_hid_report(REPORT_ID_CONSUMER_CONTROL, &usage, sizeof(usage)); }
        if (ok && ++release_phase == 4) {
            sent_epoch=state.epoch; release_phase=0; sent_key=0; sent_consumer=0; sent_buttons=0;
            diag_log("HID neutral reports queued epoch=%lu\n", (unsigned long)sent_epoch);
        }
        return;
    }
    if (state.key != sent_key) {
        // GUI is a modifier bit, never an ordinary key-array usage.
        bool modifier_key=state.key>=0xE0 && state.key<=0xE7;
        uint8_t keys[6]={modifier_key ? 0 : state.key,0,0,0,0,0};
        if (tud_hid_keyboard_report(REPORT_ID_KEYBOARD, modifier_key ? (uint8_t)(1u<<(state.key-0xE0)) : 0, keys)) sent_key=state.key;
        return;
    }
    if (state.consumer != sent_consumer) {
        if (tud_hid_report(REPORT_ID_CONSUMER_CONTROL, &state.consumer, sizeof(state.consumer))) sent_consumer=state.consumer;
        return;
    }
    int dx=(int)state.dx, dy=(int)state.dy;
    if (dx>127) dx=127;
    if (dx< -127) dx=-127;
    if (dy>127) dy=127;
    if (dy< -127) dy=-127;
    if (state.wheel || dx || dy || state.buttons!=sent_buttons) {
        int amount=state.wheel;
        if (amount>127) amount=127;
        if (amount< -127) amount=-127;
        if (tud_hid_mouse_report(REPORT_ID_MOUSE, state.buttons, dx, dy, amount, 0)) {
            sent_buttons=state.buttons;
            critical_section_enter_blocking(&lock);
            // Do not subtract wheel data belonging to a disconnected session.
            if (desired.epoch == state.epoch) {
                desired.wheel -= amount; desired.dx-=dx; desired.dy-=dy;
                if (desired.mouse_mode) desired.mouse_last_activity_ms=now;
                if (dx || dy || amount || state.buttons) desired.last_activity_ms=now;
            }
            critical_section_exit(&lock);
        }
    }
}
uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t type, uint8_t *buffer, uint16_t length) {
    (void)instance; (void)report_id; (void)type; (void)buffer; (void)length; return 0;
}
void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t type, const uint8_t *buffer, uint16_t length) {
    (void)instance; (void)report_id; (void)type; (void)buffer; (void)length;
    // Host LED/output reports are never forwarded to the LG remote.
}
#else
void bridge_hid_init(void) {}
void bridge_hid_input(uint8_t id, const uint8_t *report, unsigned length) { (void)id; (void)report; (void)length; }
void bridge_hid_disconnect(void) {}
void bridge_hid_task(void) {}
void bridge_hid_load_config(void) {}
uint32_t bridge_hid_last_activity_ms(void) { return 0; }
void bridge_hid_note_activity(void) {}
bool bridge_hid_command(const char *command) { (void)command; return false; }
#endif
