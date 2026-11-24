#pragma once
#include <stdbool.h>
#include <stdint.h>
#define POWER_CONFIG_TAG 0x4C475031u /* LGP1: independent of bonds/maps/gyro */
#define POWER_TIMEOUT_COUNT 21u
#define POWER_TIMEOUT_MAX_SECONDS 43200u
static const uint32_t power_timeout_seconds[POWER_TIMEOUT_COUNT]={30,60,90,180,240,300,360,420,480,540,600,660,720,780,1800,2700,3600,7200,14400,21600,43200};
typedef struct { uint32_t magic,seconds,check; } power_config_t;
static inline bool power_timeout_valid(uint32_t seconds) {
    for (unsigned i=0;i<POWER_TIMEOUT_COUNT;++i) if (power_timeout_seconds[i]==seconds) return true;
    return false;
}
static inline power_config_t power_config_make(uint32_t seconds) {
    return (power_config_t){POWER_CONFIG_TAG,seconds,POWER_CONFIG_TAG^seconds^0xA55A3CC3u};
}
static inline bool power_config_valid(const power_config_t *c) {
    return c->magic==POWER_CONFIG_TAG && power_timeout_valid(c->seconds) && c->check==(POWER_CONFIG_TAG^c->seconds^0xA55A3CC3u);
}

static inline bool power_timeout_parse(const char *text,uint32_t *seconds) {
    uint32_t value=0;if (!*text) return false;
    for (;*text;++text) {
        if (*text<'0' || *text>'9' || value>POWER_TIMEOUT_MAX_SECONDS/10u) return false;
        value=value*10u+(uint32_t)(*text-'0');if (value>POWER_TIMEOUT_MAX_SECONDS) return false;
    }
    if (!power_timeout_valid(value)) return false;
    *seconds=value;return true;
}
