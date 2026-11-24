#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t bd_addr_t[6];
typedef uint16_t hci_con_handle_t;
typedef void (*btstack_packet_handler_t)(uint8_t,uint16_t,uint8_t*,uint16_t);
typedef struct {uint16_t value_handle,end_handle,properties,uuid16;} gatt_client_characteristic_t;
typedef struct {int dummy;} gatt_client_notification_t;
#define HCI_CON_HANDLE_INVALID 0xffff
#define HCI_EVENT_PACKET 4
#define GATT_EVENT_INDICATION 1
#define GATT_EVENT_CHARACTERISTIC_QUERY_RESULT 2
#define GATT_EVENT_QUERY_COMPLETE 3
#define ATT_PROPERTY_INDICATE 0x20
#define ERROR_CODE_SUCCESS 0
#define GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION 2
#define HID_PROTOCOL_MODE_REPORT 1
static inline unsigned hci_event_packet_get_type(const uint8_t*p){return p[0];}
static inline unsigned gatt_event_indication_get_handle(const uint8_t*p){return p[1];}
static inline unsigned gatt_event_indication_get_value_handle(const uint8_t*p){return p[2];}
static inline unsigned gatt_event_indication_get_value_length(const uint8_t*p){return p[3];}
static inline unsigned gatt_event_characteristic_query_result_get_handle(const uint8_t*p){return p[1];}
static inline unsigned gatt_event_query_complete_get_handle(const uint8_t*p){return p[1];}
static inline unsigned gatt_event_query_complete_get_att_status(const uint8_t*p){return p[2];}
void gatt_event_characteristic_query_result_get_characteristic(const uint8_t*,gatt_client_characteristic_t*);
void gatt_client_stop_listening_for_characteristic_value_updates(gatt_client_notification_t*);
void gatt_client_listen_for_characteristic_value_updates(gatt_client_notification_t*,btstack_packet_handler_t,uint16_t,gatt_client_characteristic_t*);
uint8_t gatt_client_write_client_characteristic_configuration(btstack_packet_handler_t,uint16_t,gatt_client_characteristic_t*,uint16_t);
uint8_t gatt_client_discover_characteristics_for_handle_range_by_uuid16(btstack_packet_handler_t,uint16_t,uint16_t,uint16_t,uint16_t);
uint8_t hids_client_connect(uint16_t,btstack_packet_handler_t,unsigned,uint16_t*);
void gap_disconnect(uint16_t);
uint32_t btstack_run_loop_get_time_ms(void);

