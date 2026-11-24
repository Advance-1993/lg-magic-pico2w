#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "../firmware/src/hids_client_cached.c"
void diag_log(const char *fmt,...){(void)fmt;}
static hids_client_t seeded;
static uint8_t storage[2048];
static void seed(void){
 memset(&seeded,0,sizeof(seeded));memset(storage,0x5a,sizeof(storage));
 clients=(btstack_linked_item_t*)&seeded;hids_client_descriptor_storage=storage;hids_client_descriptor_storage_len=sizeof(storage);
 seeded.cid=42;seeded.state=HIDS_CLIENT_STATE_CONNECTED;seeded.required_protocol_mode=HID_PROTOCOL_MODE_REPORT;
 seeded.num_instances=1;seeded.num_reports=1;
 seeded.services[0]=(hid_service_t){.protocol_mode=HID_PROTOCOL_MODE_REPORT,.start_handle=10,.end_handle=100,
 .hid_descriptor_offset=0,.hid_descriptor_len=128,.hid_descriptor_max_len=2048};
 seeded.reports[0]=(hids_client_report_t){.value_handle=20,.end_handle=23,.properties=ATT_PROPERTY_NOTIFY,
 .service_index=0,.report_id=0xFD,.report_type=HID_REPORT_TYPE_INPUT};
 memset(&seeded.reports[0].notification_listener,0x99,sizeof(gatt_client_notification_t));
 lg_discovered_ccc[0]=22;lg_bad_subscription_cid=0;lg_hids_cache_clear();
}
int main(void){
 seed();assert(lg_hids_cache_capture(42));assert(lg_cache.valid&&lg_cache.length==128);
 gatt_client_notification_t zero={0};assert(!memcmp(&lg_cache.reports[0].notification_listener,&zero,sizeof(zero)));
 assert(!memcmp(lg_cache.descriptor,storage,128));assert(lg_cached_ccc[0]==22);
 memset(storage,0,sizeof(storage));assert(lg_cache.descriptor[0]==0x5a);
 lg_hids_cache_clear();assert(!lg_hids_cache_valid()&&!lg_cache_permitted);
 seed();assert(!lg_hids_cache_capture(43));
 seed();seeded.num_instances=2;assert(!lg_hids_cache_capture(42));
 seed();seeded.num_external_reports=1;assert(lg_hids_cache_capture(42)); // discovery scratch is not restored
 seed();seeded.services[0].hid_descriptor_len=2049;assert(!lg_hids_cache_capture(42));
 seed();seeded.services[0].hid_descriptor_offset=2000;assert(!lg_hids_cache_capture(42));
 seed();seeded.services[0].hid_descriptor_status=1;assert(!lg_hids_cache_capture(42));
 seed();seeded.reports[0].report_id=1;assert(!lg_hids_cache_capture(42));
 seed();seeded.reports[0].properties=0;assert(!lg_hids_cache_capture(42));
 seed();seeded.reports[0].service_index=1;assert(!lg_hids_cache_capture(42));
 seed();seeded.reports[0].value_handle=9;assert(!lg_hids_cache_capture(42));
 seed();seeded.reports[0].end_handle=101;assert(!lg_hids_cache_capture(42));
 seed();lg_discovered_ccc[0]=0;assert(!lg_hids_cache_capture(42));
 seed();lg_discovered_ccc[0]=24;assert(!lg_hids_cache_capture(42));
 seed();lg_bad_subscription_cid=42;assert(!lg_hids_cache_capture(42));
 puts("PASS: real HID snapshot rejects unsupported/incomplete layouts, sanitizes listeners, owns descriptor bytes and uses discovered CCCs");
}
