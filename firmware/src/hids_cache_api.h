#pragma once
#include <stdbool.h>
#include "btstack.h"
void lg_hids_cache_clear(void);
bool lg_hids_cache_valid(void);
bool lg_hids_cache_capture(uint16_t cid);
void lg_hids_cache_fail_next(void);
uint8_t lg_hids_connect_cached(hci_con_handle_t handle,btstack_packet_handler_t callback,uint16_t *cid);
