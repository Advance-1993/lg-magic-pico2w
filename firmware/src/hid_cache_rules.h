#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
// Cache identity is intentionally limited to public identities in this release.
static inline bool hid_cache_identity_matches(bool valid,const uint8_t saved[6],uint8_t saved_type,
                                             const uint8_t current[6],uint8_t type,bool reencrypted) {
    return valid && reencrypted && saved_type==0 && type==0 && memcmp(saved,current,6)==0;
}
static inline bool hid_cache_deadline_expired(uint32_t now,uint32_t started,uint32_t duration) {
    return (uint32_t)(now-started)>=duration;
}
