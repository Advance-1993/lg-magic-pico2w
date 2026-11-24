// Exercise the real decoder and USB sender, including release and mode changes.
#include <assert.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
uint32_t test_now=1000;
#include "../firmware/src/bridge_hid.c"
static uint8_t usb_buttons,usb_key;
static int moving_held,mouse_reports;
static bool usb_ready=true;
bool tud_mounted(void){return true;}
bool tud_suspended(void){return false;}
bool tud_hid_ready(void){return usb_ready;}
bool tud_hid_keyboard_report(uint8_t a,uint8_t b,const uint8_t*c){(void)a;(void)b;usb_key=c[0];return true;}
bool tud_hid_mouse_report(uint8_t a,uint8_t buttons,int8_t x,int8_t y,int8_t w,int8_t pan){
 (void)a;(void)w;(void)pan;usb_buttons=buttons;++mouse_reports;
 if(buttons&&(x||y))++moving_held;
 return true;
}
bool tud_hid_report(uint8_t a,const void*b,uint16_t n){(void)a;(void)b;(void)n;return true;}
void diag_log(const char*fmt,...){(void)fmt;}
static void pump(void){for(unsigned i=0;i<8;++i)bridge_hid_task();}
static void input(unsigned code,int z){
 uint8_t r[20]={0};r[0]=0xFD;r[17]=code>>8;r[18]=code;r[9]=(uint16_t)z>>8;r[10]=z;
 bridge_hid_input(0xFD,r,sizeof(r));pump();
}
static void pointer(void){bridge_hid_disconnect();bridge_hid_command("mouse on");pump();usb_key=0;}
int main(void){
 bridge_hid_init();bridge_hid_load_config();pointer();
 // Press is an immediate ordinary left down; short hold/release produces no drag.
 input(0x8044,1000);assert(usb_buttons==1&&moving_held==0);
 test_now+=100;input(0x8044,1000);assert(usb_buttons==1&&moving_held==0);
 test_now+=100;input(0,1000);assert(usb_buttons==0&&moving_held==0&&desired.dx==0);
 test_now+=119;input(0,1000);assert(desired.dx==0);
 test_now+=1;input(0,1000);assert(desired.mouse_mode);
 // A held button permits real USB pointer movement at the exact200ms boundary.
 pointer();uint32_t press=test_now;input(0x8044,1000);int before=moving_held;
 test_now=press+199;input(0x8044,1000);assert(moving_held==before&&!dragging);
 test_now=press+200;input(0x8044,1000);assert(desired.dx>0&&usb_buttons==1&&dragging);
 test_now+=10;input(0x8044,1000);assert(usb_buttons==1&&moving_held>before);
 test_now+=10;input(0,1000);assert(usb_buttons==0&&!dragging&&desired.dx==0);
 // Repeated clicks reset the hold threshold instead of accumulating elapsed time.
 for(unsigned n=0;n<3;++n){test_now+=150;input(0x8044,1000);assert(!dragging);test_now+=100;input(0,1000);assert(usb_buttons==0);}
 // Mode exits cannot leave a USB button held.
 pointer();input(0x8044,1000);test_now+=200;input(0x8044,1000);assert(usb_buttons==1);
 test_now+=10;input(0x8040,1000);assert(!desired.mouse_mode&&usb_buttons==0&&usb_key==0x52);
 // Disconnect during a drag releases through neutral reports, including USB busy retry.
 pointer();input(0x8044,1000);test_now+=200;input(0x8044,1000);
 usb_ready=false;bridge_hid_disconnect();pump();assert(usb_buttons==1);
 usb_ready=true;pump();assert(usb_buttons==0&&!desired.mouse_mode);
 // Silent radio timeout also releases held input.
 pointer();input(0x8044,1000);test_now+=200;input(0x8044,1000);
 test_now+=501;pump();assert(usb_buttons==0&&!desired.mouse_mode);
 // A new pointer session and wrapping clock do not inherit an old drag.
 test_now=UINT32_MAX-100;pointer();input(0x8044,1000);
 test_now+=199;input(0x8044,1000);assert(!dragging);
 test_now+=1;input(0x8044,1000);assert(dragging&&usb_buttons==1);
 test_now+=10;input(0,1000);assert(usb_buttons==0);
 // Navigation OK remains Enter, with an actual release.
 bridge_hid_command("mouse off");pump();test_now+=10;input(0x8044,0);assert(usb_key==0x28&&usb_buttons==0);
 test_now+=10;input(0,0);assert(usb_key==0);
 assert(mouse_reports>0);puts("PASS: real click/200ms drag USB reports, release freeze, repeated clicks, navigation, disconnect/busy/watchdog release and clock wrap");
}
