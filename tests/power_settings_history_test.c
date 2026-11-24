#include "power_policy.h"
#include "power_config.h"
#include "connection_history.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
 for (unsigned i=0;i<POWER_TIMEOUT_COUNT;++i) {
  uint32_t seconds=power_timeout_seconds[i];char decimal[16];snprintf(decimal,sizeof(decimal),"%lu",(unsigned long)seconds);
  uint32_t parsed=0;assert(power_timeout_parse(decimal,&parsed) && parsed==seconds);power_config_t c=power_config_make(seconds);assert(power_config_valid(&c));
  c.check^=1;assert(!power_config_valid(&c));
  power_policy_t p;power_policy_init(&p,100,true);power_policy_set_timeout(&p,50000,seconds*1000u);
  assert(power_policy_tick(&p,50000+seconds*1000u-1,true,100,true)==POWER_NOTHING);
  assert(power_policy_tick(&p,50000+seconds*1000u,true,100,true)==POWER_PAUSE);
  uint32_t start=UINT32_MAX-2000000u;power_policy_init(&p,start,true);power_policy_set_timeout(&p,start,seconds*1000u);
  assert(power_policy_tick(&p,start+seconds*1000u-1,true,start,true)==POWER_NOTHING);
  assert(power_policy_tick(&p,start+seconds*1000u,true,start,true)==POWER_PAUSE);
 }
 power_config_t c=power_config_make(31);assert(!power_config_valid(&c));c=power_config_make(90);c.magic=0;assert(!power_config_valid(&c));
 uint32_t value=0;assert(power_timeout_parse("90",&value) && value==90);assert(power_timeout_parse("780",&value) && value==780);
 const char *bad[]={"","-30","+30","90 ","90x","0","31","179","181","781","1799","43201","90000","4294967386","9999999999999999999999"};
 for (unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);++i) assert(!power_timeout_parse(bad[i],&value));
 power_policy_t p;power_policy_init(&p,0,false);power_policy_set_timeout(&p,10,30000);assert(p.mode==POWER_HOST_OFF && !p.host_online);
 assert(power_policy_tick(&p,40000,false,0,true)==POWER_NOTHING);
 power_policy_init(&p,0,true);assert(power_policy_sleep(&p,100)==POWER_PAUSE);power_policy_set_timeout(&p,200,60000);assert(p.mode==POWER_IDLE);
 link_history_t h;link_history_init(&h,0x1234);assert(!link_history_get(&h,0));
 for (unsigned i=1;i<=100;++i) { link_event_t e=link_history_add(&h,i*10,LINK_CONNECTED,i);assert(e.seq==i); }
 assert(h.count==32 && link_history_get(&h,0)->seq==69 && link_history_get(&h,31)->seq==100 && !link_history_get(&h,32));
 assert(h.boot==0x1234 && !strcmp(link_event_name(LINK_USB_OFF),"usb_unavailable"));
 puts("PASS: all21 timeout records, malformed/overflow rejection, new countdown and pause preservation, bounded ordered history");return 0;
}
