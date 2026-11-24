// Bonded RAM HID cache with standard Service Changed subscription and slow fallback.
#include "btstack.h"
#include "diagnostic.h"
#include "bridge_hid.h"
#include "hids_cache_api.h"
#include "hid_cache_rules.h"
#include "hid_reconnect.h"
typedef enum { RC_IDLE,RC_FIND_CHANGED,RC_SUBSCRIBE,RC_FULL,RC_FAST,RC_READY,RC_FAILED } reconnect_stage_t;
static reconnect_stage_t stage;
static uint16_t connection=HCI_CON_HANDLE_INVALID;
static bd_addr_t peer,cache_peer;
static uint8_t peer_type,cache_type,changed_count;
static gatt_client_characteristic_t changed,cached_changed;
static gatt_client_notification_t listener;
static btstack_packet_handler_t client_callback;
static uint16_t *client_cid;
static bool listening,eligible,subscribed,dirty,fast_attempt,enabled=true;
static uint32_t started,deadline_started,attempts,hits,falls,invalidations;
static void setup_event(uint8_t type,uint16_t channel,uint8_t *packet,uint16_t size);

void hid_reconnect_clear(const char *reason) {
    lg_hids_cache_clear();memset(cache_peer,0,sizeof(cache_peer));memset(&cached_changed,0,sizeof(cached_changed));
    ++invalidations;diag_log("HID_CACHE invalidated reason=%s\n",reason);
}
static void fail_closed(const char *reason) {
    if (stage==RC_FAILED || connection==HCI_CON_HANDLE_INVALID) return;
    if (fast_attempt) ++falls;
    hid_reconnect_clear(reason);dirty=true;stage=RC_FAILED;
    // A pending ATT request must be cancelled by controller disconnect, not reused.
    bridge_hid_disconnect();diag_log("HID_CACHE fallback reason=%s; reconnect with full discovery\n",reason);
    gap_disconnect(connection);
}
static void changed_event(uint8_t type,uint16_t channel,uint8_t *packet,uint16_t size) {
    (void)channel;if (type!=HCI_EVENT_PACKET || size<12 ||
        hci_event_packet_get_type(packet)!=GATT_EVENT_INDICATION ||
        gatt_event_indication_get_handle(packet)!=connection) return;
    uint16_t handle=gatt_event_indication_get_value_handle(packet);
    // Listen before encryption; Service Changed may arrive as soon as security completes.
    // Unknown indications conservatively invalidate too, rather than risking stale input.
    diag_log("HID_CACHE indication handle=%04X changed=%04X len=%u\n",handle,changed.value_handle,
             gatt_event_indication_get_value_length(packet));
    fail_closed("service_changed_indication");
}
void hid_reconnect_link(uint16_t handle,const bd_addr_t address,uint8_t type) {
    if (listening) gatt_client_stop_listening_for_characteristic_value_updates(&listener);
    connection=handle;memcpy(peer,address,6);peer_type=type;
    stage=RC_IDLE;subscribed=false;dirty=false;fast_attempt=false;
    changed=cached_changed;
    memset(&listener,0,sizeof(listener));
    gatt_client_listen_for_characteristic_value_updates(&listener,changed_event,handle,NULL);listening=true;
}
void hid_reconnect_disconnected(void) {
    if (listening) gatt_client_stop_listening_for_characteristic_value_updates(&listener);
    listening=false;connection=HCI_CON_HANDLE_INVALID;stage=RC_IDLE;
    client_callback=NULL;client_cid=NULL;subscribed=false;fast_attempt=false;
}
static void begin_hid(void) {
    if (dirty || connection==HCI_CON_HANDLE_INVALID) return;
    deadline_started=btstack_run_loop_get_time_ms();
    fast_attempt=eligible && subscribed && enabled && lg_hids_cache_valid();
    stage=fast_attempt ? RC_FAST : RC_FULL;
    diag_log("HID_CACHE path=%s elapsed_ms=%lu\n",fast_attempt ? "cached" : "full",(unsigned long)(deadline_started-started));
    uint8_t status;
    if (fast_attempt) { ++attempts;status=lg_hids_connect_cached(connection,client_callback,client_cid); }
    else status=hids_client_connect(connection,client_callback,HID_PROTOCOL_MODE_REPORT,client_cid);
    if (status!=ERROR_CODE_SUCCESS) fail_closed("hid_start_error");
}
static void setup_event(uint8_t type,uint16_t channel,uint8_t *packet,uint16_t size) {
    (void)channel;(void)size;if (type!=HCI_EVENT_PACKET || dirty || connection==HCI_CON_HANDLE_INVALID) return;
    switch (hci_event_packet_get_type(packet)) {
        case GATT_EVENT_CHARACTERISTIC_QUERY_RESULT:
            if (stage!=RC_FIND_CHANGED || gatt_event_characteristic_query_result_get_handle(packet)!=connection) return;
            ++changed_count;gatt_event_characteristic_query_result_get_characteristic(packet,&changed);break;
        case GATT_EVENT_QUERY_COMPLETE: {
            if (gatt_event_query_complete_get_handle(packet)!=connection) return;
            uint8_t status=gatt_event_query_complete_get_att_status(packet);
            if (stage==RC_FIND_CHANGED) {
                if (status || changed_count!=1 || changed.uuid16!=0x2A05 || !(changed.properties&ATT_PROPERTY_INDICATE)) {
                    hid_reconnect_clear("service_changed_unavailable");eligible=false;begin_hid();return;
                }
                if (eligible && (changed.value_handle!=cached_changed.value_handle || changed.end_handle!=cached_changed.end_handle)) {
                    hid_reconnect_clear("service_changed_handles_changed");eligible=false;
                }
                stage=RC_SUBSCRIBE;
                status=gatt_client_write_client_characteristic_configuration(setup_event,connection,&changed,
                                  GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION);
                if (status) { hid_reconnect_clear("service_changed_subscribe_start_failed");eligible=false;begin_hid(); }
            } else if (stage==RC_SUBSCRIBE) {
                subscribed=status==ERROR_CODE_SUCCESS;
                diag_log("HID_CACHE service_changed subscription=%u status=%02X value=%04X\n",subscribed,status,changed.value_handle);
                if (!subscribed) { hid_reconnect_clear("service_changed_subscribe_failed");eligible=false; }
                begin_hid();
            }
            break;
        }
        default:break;
    }
}
void hid_reconnect_start(btstack_packet_handler_t callback,uint16_t *cid,bool trusted) {
    if (dirty || connection==HCI_CON_HANDLE_INVALID) return;
    client_callback=callback;client_cid=cid;started=btstack_run_loop_get_time_ms();deadline_started=started;
    eligible=LG_ENABLE_HID && enabled && hid_cache_identity_matches(lg_hids_cache_valid(),cache_peer,cache_type,peer,peer_type,trusted);
    // Pairing/re-pairing can retain the address while replacing the trust relation.
    if (!trusted) hid_reconnect_clear("new_pairing_or_identity");
    if (!LG_ENABLE_HID || !enabled) { eligible=false;begin_hid();return; }
    stage=RC_FIND_CHANGED;changed_count=0;
    uint8_t status=gatt_client_discover_characteristics_for_handle_range_by_uuid16(setup_event,connection,1,0xFFFF,0x2A05);
    if (status) { hid_reconnect_clear("service_changed_discovery_start_failed");eligible=false;begin_hid(); }
}
void hid_reconnect_poll(void) {
    if (stage==RC_IDLE || stage==RC_READY || stage==RC_FAILED) return;
    uint32_t limit=stage==RC_FAST ? 2500u : 8000u;
    if (hid_cache_deadline_expired(btstack_run_loop_get_time_ms(),deadline_started,limit)) fail_closed("setup_timeout");
}
void hid_reconnect_ready(uint16_t cid) {
    if (dirty || stage==RC_FAILED) return;
    bool was_fast=stage==RC_FAST;
    stage=RC_READY;
    if (was_fast) ++hits;
    else if (LG_ENABLE_HID && enabled && subscribed && peer_type==0 && lg_hids_cache_capture(cid)) {
        memcpy(cache_peer,peer,6);cache_type=peer_type;cached_changed=changed;
        diag_log("HID_CACHE captured RAM snapshot; standard Service Changed armed\n");
    }
    diag_log("HID_CACHE ready path=%s setup_ms=%lu attempts=%lu hits=%lu fallbacks=%lu\n",was_fast ? "cached" : "full",
        (unsigned long)(btstack_run_loop_get_time_ms()-started),(unsigned long)attempts,(unsigned long)hits,(unsigned long)falls);
}
void hid_reconnect_failed(uint8_t status) {
    diag_log("HID_CACHE hid_error=%02X\n",status);fail_closed("hid_subscription_error");
}
bool hid_reconnect_input_allowed(void) {
    // Cached reports stay gated until every input CCC operation succeeded.
    return !dirty && (stage==RC_FULL || stage==RC_READY);
}
bool hid_reconnect_command(const char *command) {
    if (!strcmp(command,"reconnect cache status")) {
        diag_log("HID_CACHE_STATUS enabled=%u valid=%u stage=%u subscribed=%u attempts=%lu hits=%lu fallbacks=%lu invalidations=%lu ram_only=1\n",
            enabled,lg_hids_cache_valid(),stage,subscribed,(unsigned long)attempts,(unsigned long)hits,(unsigned long)falls,(unsigned long)invalidations);return true;
    }
    if (!strcmp(command,"reconnect cache clear")) { hid_reconnect_clear("manual_clear");return true; }
    if (!strcmp(command,"reconnect cache off")) { enabled=false;hid_reconnect_clear("manual_disable");return true; }
    if (!strcmp(command,"reconnect cache on")) { enabled=true;diag_log("HID_CACHE enabled; next full discovery can populate RAM\n");return true; }
    if (!strcmp(command,"reconnect cache fail-next")) { lg_hids_cache_fail_next();diag_log("HID_CACHE_TEST next cached CCC completion will fail locally; no vendor command\n");return true; }
    if (!strcmp(command,"reconnect cache change-test")) { fail_closed("synthetic_service_changed_test");return true; }
    return false;
}
