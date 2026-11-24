#ifndef LG_MAPPING_CONFIG_H
#define LG_MAPPING_CONFIG_H
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#define MAP_TAG 0x4C474D31u
#define MAP_COUNT 23u
enum { MAP_NONE=0, MAP_KEY=1, MAP_CONSUMER=2, MAP_POINTER=3 };
typedef struct { uint16_t code; uint8_t kind, reserved; uint16_t value, reserved2; } mapping_entry_t;
typedef struct { uint32_t magic, count; mapping_entry_t entries[MAP_COUNT]; } mapping_config_t;
// Verified MR25GA raw codes, standard USB usages, and the project's factory defaults.
static const mapping_entry_t mapping_default_entries[MAP_COUNT]={
 {0x8040,MAP_KEY,0,0x52,0},{0x8041,MAP_KEY,0,0x51,0},
 {0x8007,MAP_KEY,0,0x50,0},{0x8006,MAP_KEY,0,0x4F,0},
 {0x8044,MAP_KEY,0,0x28,0},{0x8028,MAP_KEY,0,0x29,0},
 {0x807C,MAP_KEY,0,0xE3,0},{0x8002,MAP_KEY,0,0x72,0},
 {0x8003,MAP_KEY,0,0x73,0},{0x8000,MAP_CONSUMER,0,0xE9,0},
 {0x8001,MAP_CONSUMER,0,0xEA,0},{0x808B,MAP_POINTER,0,0,0},
 {0x8056,MAP_KEY,0,0x68,0},{0x805C,MAP_KEY,0,0x69,0},
 {0x8031,MAP_KEY,0,0x6A,0},{0x8049,MAP_KEY,0,0x6B,0},
 {0x8048,MAP_KEY,0,0x6C,0},{0x800C,MAP_KEY,0,0x6D,0},
 {0x8029,MAP_KEY,0,0x6E,0},{0x80A1,MAP_KEY,0,0x6F,0},
 {0x80AB,MAP_KEY,0,0x70,0},{0x8045,MAP_KEY,0,0x71,0},
 {0x8043,MAP_KEY,0,0x45,0}
};
static inline bool mapping_value_valid(uint16_t code,uint8_t kind,uint16_t value) {
 if (kind==MAP_NONE) return value==0;
 if (kind==MAP_POINTER) return value==0 && code!=0x8044; // OK always clicks in pointer mode.
 if (kind==MAP_KEY) return (value>=4 && value<=0x73) || (value>=0xE0 && value<=0xE7);
 if (kind==MAP_CONSUMER) return value==0xE9 || value==0xEA || value==0xE2 || value==0xCD || value==0xB5 || value==0xB6 || value==0xB7;
 return false;
}
static inline void mapping_defaults(mapping_config_t *config) {
 memset(config,0,sizeof(*config)); config->magic=MAP_TAG; config->count=MAP_COUNT;
 memcpy(config->entries,mapping_default_entries,sizeof(mapping_default_entries));
}
static inline bool mapping_valid(const mapping_config_t *config) {
 if (config->magic!=MAP_TAG || config->count!=MAP_COUNT) return false;
 for (unsigned i=0;i<MAP_COUNT;++i) {
  const mapping_entry_t *e=&config->entries[i];
  if (e->code!=mapping_default_entries[i].code || e->reserved || e->reserved2 || !mapping_value_valid(e->code,e->kind,e->value)) return false;
 }
 return true;
}
static inline int mapping_index(uint16_t code) {
 for (unsigned i=0;i<MAP_COUNT;++i) if (mapping_default_entries[i].code==code) return (int)i;
 return -1;
}
static inline const char *mapping_kind_name(uint8_t kind) {
 return kind==MAP_KEY ? "key" : kind==MAP_CONSUMER ? "consumer" : kind==MAP_POINTER ? "pointer" : "none";
}
#endif