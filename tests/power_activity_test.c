#include <assert.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
uint32_t test_now=1000;
#include "../firmware/src/bridge_hid.c"
bool tud_mounted(void) { return true; }
bool tud_suspended(void) { return false; }
bool tud_hid_ready(void) { return true; }
bool tud_hid_keyboard_report(uint8_t a,uint8_t b,const uint8_t *c) { (void)a;(void)b;(void)c;return true; }
bool tud_hid_mouse_report(uint8_t a,uint8_t b,int8_t c,int8_t d,int8_t e,int8_t f) { (void)a;(void)b;(void)c;(void)d;(void)e;(void)f;return true; }
bool tud_hid_report(uint8_t a,const void *b,uint16_t c) { (void)a;(void)b;(void)c;return true; }
void diag_log(const char *fmt,...) { (void)fmt; }
static void input(unsigned code,int wheel,int z) {
 uint8_t r[20]={0};r[0]=0xFD;r[17]=code>>8;r[18]=code;r[19]=wheel;r[9]=(uint16_t)z>>8;r[10]=z;
 bridge_hid_input(0xFD,r,20);
}
int main(void) {
 bridge_hid_init();bridge_hid_load_config();bridge_hid_note_activity();assert(bridge_hid_last_activity_ms()==1000);
 test_now=2000;input(0,0,100);assert(bridge_hid_last_activity_ms()==1000); // gyro with pointer OFF is not use
 test_now=3000;input(0x8040,0,0);assert(bridge_hid_last_activity_ms()==3000);
 test_now=3100;input(0x8040,0,0);assert(bridge_hid_last_activity_ms()==3100); // held key
 test_now=3200;input(0,0,0);assert(bridge_hid_last_activity_ms()==3100);
 test_now=4000;input(0,1,0);assert(bridge_hid_last_activity_ms()==4000);
 test_now=5000;bridge_hid_command("mouse on");assert(bridge_hid_last_activity_ms()==5000);
 for(unsigned i=0;i<20;++i) { test_now+=10;input(0,0,100);bridge_hid_task(); }
 assert(bridge_hid_last_activity_ms()>5000); // active USB pointer movement counts
 puts("PASS: actual decoder ignores idle reports and counts held buttons, wheel, pointer activation and mouse movement");
 return 0;
}
