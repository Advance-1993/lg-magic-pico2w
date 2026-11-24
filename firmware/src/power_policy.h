#ifndef LG_POWER_POLICY_H
#define LG_POWER_POLICY_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#define POWER_IDLE_MS 90000u
#define POWER_USB_GRACE_MS 2000u
#define POWER_PEER_QUIET_MS 2000u

typedef enum { POWER_HOST_OFF, POWER_ACTIVE, POWER_IDLE } power_mode_t;
typedef enum { POWER_NOTHING, POWER_PAUSE, POWER_WAKE } power_action_t;
typedef struct {
    power_mode_t mode;
    bool host_online, usb_loss_pending, idle_armed, idle_enabled;
    uint32_t idle_timeout_ms;
    uint32_t usb_loss_since, last_activity_ms, idle_enter_ms, last_peer_adv_ms;
    uint32_t host_pauses, host_resumes, idle_pauses, peer_wakes, manual_wakes, idle_peer_ads;
} power_policy_t;
static inline void power_policy_init(power_policy_t *p,uint32_t now,bool host_online) {
    memset(p,0,sizeof(*p));p->mode=host_online ? POWER_ACTIVE : POWER_HOST_OFF;
    p->host_online=host_online;p->last_activity_ms=now;p->idle_enabled=true;p->idle_timeout_ms=POWER_IDLE_MS;
}
// Saving an explicit user setting starts a fresh countdown; it never wakes a paused link.
static inline void power_policy_set_timeout(power_policy_t *p,uint32_t now,uint32_t timeout_ms) {
    p->idle_timeout_ms=timeout_ms;p->last_activity_ms=now;
}
static inline void power_policy_activity(power_policy_t *p,uint32_t activity_ms) {
    if ((int32_t)(activity_ms-p->last_activity_ms)>0) p->last_activity_ms=activity_ms;
}
static inline power_action_t power_policy_sleep(power_policy_t *p,uint32_t now) {
    if (!p->host_online || p->mode!=POWER_ACTIVE) return POWER_NOTHING;
    p->mode=POWER_IDLE;p->idle_armed=false;p->idle_enter_ms=now;p->last_peer_adv_ms=now;
    ++p->idle_pauses;return POWER_PAUSE;
}
static inline power_action_t power_policy_resume(power_policy_t *p,uint32_t now) {
    p->last_activity_ms=now;p->idle_armed=false;
    if (!p->host_online) return POWER_NOTHING;
    bool changed=p->mode!=POWER_ACTIVE;p->mode=POWER_ACTIVE;
    if (changed) ++p->manual_wakes;
    return changed ? POWER_WAKE : POWER_NOTHING;
}
static inline power_action_t power_policy_tick(power_policy_t *p,uint32_t now,bool raw_usb_active,uint32_t activity_ms,bool idle_allowed) {
    if (raw_usb_active) {
        p->usb_loss_pending=false;
        if (!p->host_online) {
            p->host_online=true;p->mode=POWER_ACTIVE;p->last_activity_ms=now;
            p->idle_armed=false;++p->host_resumes;return POWER_WAKE;
        }
    } else if (p->host_online) {
        if (!p->usb_loss_pending) { p->usb_loss_pending=true;p->usb_loss_since=now; }
        if (now-p->usb_loss_since>=POWER_USB_GRACE_MS) {
            p->host_online=false;p->mode=POWER_HOST_OFF;p->idle_armed=false;
            ++p->host_pauses;return POWER_PAUSE;
        }
    }
    power_policy_activity(p,activity_ms);
    if (!p->host_online) return POWER_NOTHING;
    if (p->mode==POWER_ACTIVE && p->idle_enabled && idle_allowed && now-p->last_activity_ms>=p->idle_timeout_ms)
        return power_policy_sleep(p,now);
    if (p->mode==POWER_IDLE && !p->idle_armed && now-p->last_peer_adv_ms>=POWER_PEER_QUIET_MS)
        p->idle_armed=true;
    return POWER_NOTHING;
}
// Passive advertising only. Ignore the post-disconnect burst, then wait for NEW peer advertising.
static inline bool power_policy_peer_advertisement(power_policy_t *p,uint32_t now) {
    if (p->mode!=POWER_IDLE || !p->host_online) return false;
    ++p->idle_peer_ads;
    bool fresh=p->idle_armed || now-p->last_peer_adv_ms>=POWER_PEER_QUIET_MS;
    p->last_peer_adv_ms=now;
    if (!fresh) return false;
    p->mode=POWER_ACTIVE;p->last_activity_ms=now;p->idle_armed=false;++p->peer_wakes;
    return true;
}
#endif
