#pragma once
#include <stdbool.h>
#include <stdint.h>
typedef int hid_report_type_t;
#define MOUSE_BUTTON_LEFT 1
bool tud_mounted(void);
bool tud_suspended(void);
bool tud_hid_ready(void);
bool tud_hid_keyboard_report(uint8_t,uint8_t,const uint8_t *);
bool tud_hid_mouse_report(uint8_t,uint8_t,int8_t,int8_t,int8_t,int8_t);
bool tud_hid_report(uint8_t,const void *,uint16_t);
