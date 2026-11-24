#pragma once
#include <stdint.h>
#include <stdbool.h>
void bridge_hid_init(void);
void bridge_hid_input(uint8_t id, const uint8_t *report, unsigned length);
void bridge_hid_disconnect(void);
void bridge_hid_task(void);
void bridge_hid_load_config(void);
bool bridge_hid_command(const char *command);

uint32_t bridge_hid_last_activity_ms(void);
void bridge_hid_note_activity(void);
