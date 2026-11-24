#pragma once
#include "btstack.h"
void hid_reconnect_link(uint16_t handle,const bd_addr_t address,uint8_t type);
void hid_reconnect_disconnected(void);
void hid_reconnect_start(btstack_packet_handler_t callback,uint16_t *cid,bool trusted);
void hid_reconnect_poll(void);
void hid_reconnect_ready(uint16_t cid);
void hid_reconnect_failed(uint8_t status);
bool hid_reconnect_input_allowed(void);
void hid_reconnect_clear(const char *reason);
bool hid_reconnect_command(const char *command);
