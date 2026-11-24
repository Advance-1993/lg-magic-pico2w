// Read-only standard GATT cache-capability investigation; no cached handles or vendor writes.
#include "btstack.h"
#include "diagnostic.h"
#include "reconnect_probe.h"
static uint16_t connection=HCI_CON_HANDLE_INVALID,hash_handle,changed_handle;
static unsigned phase;
static bool active,waiting;
static void probe_event(uint8_t packet_type,uint16_t channel,uint8_t *packet,uint16_t size) {
    (void)channel;(void)size;if (!active || packet_type!=HCI_EVENT_PACKET) return;
    switch (hci_event_packet_get_type(packet)) {
        case GATT_EVENT_CHARACTERISTIC_QUERY_RESULT: {
            if (gatt_event_characteristic_query_result_get_handle(packet)!=connection) return;
            gatt_client_characteristic_t c;gatt_event_characteristic_query_result_get_characteristic(packet,&c);
            if (phase==1) changed_handle=c.value_handle;
            if (phase==2) hash_handle=c.value_handle;
            diag_log("CACHE_CAPABILITY uuid=%04X value_handle=%04X properties=%04X\n",c.uuid16,c.value_handle,c.properties);break;
        }
        case GATT_EVENT_CHARACTERISTIC_VALUE_QUERY_RESULT:
            if (gatt_event_characteristic_value_query_result_get_handle(packet)!=connection) return;
            diag_hex("CACHE_DATABASE_HASH",0,0,gatt_event_characteristic_value_query_result_get_value(packet),gatt_event_characteristic_value_query_result_get_value_length(packet));break;
        case GATT_EVENT_QUERY_COMPLETE: {
            if (gatt_event_query_complete_get_handle(packet)!=connection) return;
            unsigned status=gatt_event_query_complete_get_att_status(packet);
            diag_log("CACHE_PROBE_PHASE phase=%u status=%02X\n",phase,status);waiting=false;
            if (status!=ATT_ERROR_SUCCESS && status!=ATT_ERROR_ATTRIBUTE_NOT_FOUND) { active=false;diag_log("CACHE_PROBE_FAILED; normal HID unchanged\n");break; }
            ++phase;break;
        }
        default:break;
    }
}
void reconnect_probe_start(uint16_t handle) {
    if (active) { diag_log("CACHE_PROBE_BUSY\n");return; }
    connection=handle;phase=1;hash_handle=0;changed_handle=0;waiting=false;active=true;
    diag_log("CACHE_PROBE_START; UUID2A05/2B2A standard reads only; HID path unchanged\n");
}
void reconnect_probe_poll(void) {
    if (!active || waiting) return;
    uint8_t status=0;
    if (phase<=2) {
        status=gatt_client_discover_characteristics_for_handle_range_by_uuid16(probe_event,connection,1,0xFFFF,phase==1 ? 0x2A05 : 0x2B2A);
    } else if (phase==3 && hash_handle) {
        status=gatt_client_read_value_of_characteristic_using_value_handle(probe_event,connection,hash_handle);
    } else {
        diag_log("CACHE_PROBE_DONE service_changed=%u database_hash=%u; cached-connect not enabled\n",changed_handle!=0,hash_handle!=0);active=false;return;
    }
    if (status==ERROR_CODE_SUCCESS) waiting=true;
    else { diag_log("CACHE_PROBE_FAILED start_status=%02X; normal HID unchanged\n",status);active=false; }
}
void reconnect_probe_disconnected(void) {
    if (active) diag_log("CACHE_PROBE_ABORTED disconnected\n");
    active=false;waiting=false;connection=HCI_CON_HANDLE_INVALID;
}
