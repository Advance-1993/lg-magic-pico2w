// Exercise the real orchestrator with a deterministic fake GATT transport.
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include "btstack.h"
static uint32_t now;
static bool valid;
static unsigned full_calls,fast_calls,disconnects,neutral,listen,subscription_writes;
static uint8_t start_status,subscribe_status;
static btstack_packet_handler_t query,watcher;
static gatt_client_characteristic_t found={3,4,ATT_PROPERTY_INDICATE,0x2A05};
uint32_t btstack_run_loop_get_time_ms(void){return now;}
void diag_log(const char *f,...){(void)f;}
void bridge_hid_disconnect(void){++neutral;}
void gap_disconnect(uint16_t h){assert(h==7);++disconnects;}
void lg_hids_cache_clear(void){valid=false;}
bool lg_hids_cache_valid(void){return valid;}
bool lg_hids_cache_capture(uint16_t cid){assert(cid==42);valid=true;return true;}
void lg_hids_cache_fail_next(void){}
uint8_t lg_hids_connect_cached(uint16_t h,btstack_packet_handler_t cb,uint16_t *cid){assert(h==7&&cb);++fast_calls;*cid=42;return start_status;}
uint8_t hids_client_connect(uint16_t h,btstack_packet_handler_t cb,unsigned mode,uint16_t *cid){assert(h==7&&cb&&mode==HID_PROTOCOL_MODE_REPORT);++full_calls;*cid=42;return start_status;}
void gatt_client_stop_listening_for_characteristic_value_updates(gatt_client_notification_t*n){(void)n;assert(listen);--listen;}
void gatt_client_listen_for_characteristic_value_updates(gatt_client_notification_t*n,btstack_packet_handler_t cb,uint16_t h,gatt_client_characteristic_t*c){(void)n;assert(h==7&&!c);watcher=cb;++listen;}
uint8_t gatt_client_discover_characteristics_for_handle_range_by_uuid16(btstack_packet_handler_t cb,uint16_t h,uint16_t a,uint16_t b,uint16_t uuid){assert(h==7&&a==1&&b==65535&&uuid==0x2A05);query=cb;return 0;}
uint8_t gatt_client_write_client_characteristic_configuration(btstack_packet_handler_t cb,uint16_t h,gatt_client_characteristic_t*c,uint16_t v){assert(h==7&&c->value_handle==found.value_handle&&v==2);query=cb;++subscription_writes;return subscribe_status;}
void gatt_event_characteristic_query_result_get_characteristic(const uint8_t*p,gatt_client_characteristic_t*c){(void)p;*c=found;}
#include "../firmware/src/hid_reconnect.c"
static uint16_t cid;
static void client(uint8_t t,uint16_t c,uint8_t*p,uint16_t n){(void)t;(void)c;(void)p;(void)n;}
static const bd_addr_t remote={0x78,0,0xA8,0x94,0x3A,0x55};
static void begin(bool trusted){hid_reconnect_link(7,remote,0);hid_reconnect_start(client,&cid,trusted);}
static void result(unsigned status){uint8_t e[12]={GATT_EVENT_QUERY_COMPLETE,7,(uint8_t)status};query(4,0,e,sizeof(e));}
static void characteristic(void){uint8_t e[12]={GATT_EVENT_CHARACTERISTIC_QUERY_RESULT,7};query(4,0,e,sizeof(e));}
static void setup(void){characteristic();result(0);result(0);}
static void down(void){hid_reconnect_disconnected();assert(listen==0);}
int main(void){
 // First connection never uses cache; subscribe before full discovery and capture.
 begin(false);assert(!hid_reconnect_input_allowed());setup();assert(full_calls==1&&fast_calls==0);
 assert(hid_reconnect_input_allowed());hid_reconnect_ready(42);assert(valid);down();
 // Bonded reconnect uses cache, but no input until all subscriptions succeed.
 begin(true);setup();assert(fast_calls==1&&!hid_reconnect_input_allowed());
 hid_reconnect_ready(42);assert(hid_reconnect_input_allowed()&&valid);down();
 // Actual Service Changed callback immediately releases inputs and invalidates.
 begin(true);setup();hid_reconnect_ready(42);
 uint8_t indication[12]={GATT_EVENT_INDICATION,7,3,4};watcher(4,0,indication,sizeof(indication));
 assert(!valid&&!hid_reconnect_input_allowed()&&disconnects==1&&neutral==1);down();
 begin(true);setup();assert(full_calls==2);hid_reconnect_ready(42);down();
 // Failed cached HID completion must cause a slow reconnect, not success.
 begin(true);setup();hid_reconnect_failed(0x12);assert(!valid&&disconnects==2);down();
 begin(true);setup();assert(full_calls==3);hid_reconnect_ready(42);down();
 // Cached setup timeout and uptime wrap are bounded and neutralize inputs.
 now=UINT32_MAX-1000;begin(true);setup();now+=2499;hid_reconnect_poll();assert(disconnects==2);
 now+=1;hid_reconnect_poll();assert(disconnects==3&&!valid);down();now=0;
 // Missing Service Changed or failed subscription disables caching, keeps full path.
 begin(true);result(0);assert(stage==RC_FULL);hid_reconnect_ready(42);assert(!valid);down();
 begin(true);characteristic();result(0);result(3);assert(stage==RC_FULL&&!valid);hid_reconnect_ready(42);assert(!valid);down();
 // No cache when peer identity changes, random identity, or trust was replaced.
 begin(true);setup();hid_reconnect_ready(42);down();assert(valid);
 bd_addr_t other={1,2,3,4,5,6};hid_reconnect_link(7,other,0);hid_reconnect_start(client,&cid,true);setup();assert(stage==RC_FULL);down();
 hid_reconnect_link(7,remote,1);hid_reconnect_start(client,&cid,true);setup();assert(stage==RC_FULL);down();
 begin(false);assert(!valid);setup();hid_reconnect_ready(42);down();
 // Changed Service Changed handles invalidate rather than reusing old HID handles.
 found.value_handle=5;found.end_handle=6;begin(true);setup();assert(stage==RC_FULL&&!valid);hid_reconnect_ready(42);down();
 // Turning optimization off retains normal input and full discovery on next link.
 assert(hid_reconnect_command("reconnect cache off"));begin(true);assert(stage==RC_FULL);
 hid_reconnect_ready(42);assert(hid_reconnect_input_allowed()&&!valid);down();
 assert(hid_reconnect_command("reconnect cache on"));
 // Synchronous setup failure fails closed. No client leak or repeated disconnects.
 start_status=0x0c;begin(true);setup();assert(stage==RC_FAILED&&!valid);unsigned n=disconnects;
 hid_reconnect_poll();assert(disconnects==n);down();
 assert(!hid_cache_identity_matches(true,remote,0,other,0,true));
 assert(!hid_cache_identity_matches(true,remote,0,remote,0,false));
 puts("PASS: real HID reconnect orchestrator: trust/identity, gated input, Service Changed, strict failure, timeout/wrap, disable and full fallback");
}
