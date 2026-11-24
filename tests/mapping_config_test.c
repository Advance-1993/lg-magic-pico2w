#include "mapping_config.h"
#include <assert.h>
int main(void) {
 mapping_config_t c; mapping_defaults(&c);
 assert(mapping_valid(&c)); assert(sizeof(mapping_entry_t)==8); assert(sizeof(c)==192);
 assert(c.entries[mapping_index(0x8002)].value==0x72);
 assert(c.entries[mapping_index(0x8003)].value==0x73);
 assert(c.entries[mapping_index(0x8043)].value==0x45);
 assert(mapping_index(0x807C)>=0); assert(mapping_index(0xFFFF)<0);
 c.entries[0].value=0xE3; assert(mapping_valid(&c));
 c.entries[0].value=0xFFFF; assert(!mapping_valid(&c));
 mapping_defaults(&c); c.entries[0].code=0xFFFF; assert(!mapping_valid(&c));
 mapping_defaults(&c); c.entries[0].reserved=1; assert(!mapping_valid(&c));
 assert(!mapping_value_valid(0x8044,MAP_POINTER,0));
 assert(mapping_value_valid(0x808B,MAP_POINTER,0));
 assert(!mapping_value_valid(0x8040,MAP_KEY,0));
 assert(!mapping_value_valid(0x8040,MAP_CONSUMER,0xFFFF));
 assert(mapping_value_valid(0x8040,MAP_NONE,0));
 return 0;
}