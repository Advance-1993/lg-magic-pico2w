#pragma once
#include <stdint.h>
void reconnect_probe_start(uint16_t handle);
void reconnect_probe_poll(void);
void reconnect_probe_disconnected(void);
