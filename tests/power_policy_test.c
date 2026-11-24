#include "power_policy.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
 power_policy_t p;power_policy_init(&p,100,true);
 assert(power_policy_tick(&p,90099,true,100,true)==POWER_NOTHING);
 assert(power_policy_tick(&p,90100,true,100,true)==POWER_PAUSE && p.mode==POWER_IDLE);
 // Existing advertising must not cause a reconnect loop.
 for(unsigned i=1;i<20;++i) assert(!power_policy_peer_advertisement(&p,90100+i*100));
 assert(power_policy_tick(&p,94000,true,100,true)==POWER_NOTHING && p.idle_armed);
 assert(power_policy_peer_advertisement(&p,94100) && p.mode==POWER_ACTIVE && p.peer_wakes==1);
 assert(power_policy_tick(&p,94101,true,100,true)==POWER_NOTHING);
 // Genuine button/wheel/pointer activity keeps the timeout from expiring.
 power_policy_init(&p,100,true);
 for(uint32_t t=1000;t<900000;t+=1000) assert(power_policy_tick(&p,t,true,t,true)==POWER_NOTHING);
 assert(power_policy_tick(&p,988999,true,899000,true)==POWER_NOTHING);
 assert(power_policy_tick(&p,989000,true,899000,true)==POWER_PAUSE);
 // USB loss is debounced; return before the deadline cancels it.
 power_policy_init(&p,0,true);
 assert(power_policy_tick(&p,10,false,0,true)==POWER_NOTHING);
 assert(power_policy_tick(&p,2009,false,0,true)==POWER_NOTHING);
 assert(power_policy_tick(&p,2010,true,0,true)==POWER_NOTHING && p.host_online);
 assert(power_policy_tick(&p,3000,false,0,true)==POWER_NOTHING);
 assert(power_policy_tick(&p,5000,false,0,true)==POWER_PAUSE && p.mode==POWER_HOST_OFF);
 assert(!power_policy_peer_advertisement(&p,9000));
 assert(power_policy_resume(&p,9001)==POWER_NOTHING && !p.host_online);
 assert(power_policy_tick(&p,10000,true,0,true)==POWER_WAKE && p.mode==POWER_ACTIVE);
 assert(p.host_pauses==1 && p.host_resumes==1);
 // Starting without a PC never auto-connects; mount wakes with a fresh idle timer.
 power_policy_init(&p,100,false);
 assert(power_policy_tick(&p,400000,false,0,true)==POWER_NOTHING && p.mode==POWER_HOST_OFF);
 assert(power_policy_tick(&p,400001,true,0,true)==POWER_WAKE);
 assert(power_policy_tick(&p,400002,true,0,true)==POWER_NOTHING);
 // Manual/security pause and pairing are supplied as idle_allowed=false.
 power_policy_init(&p,100,true);
 assert(power_policy_tick(&p,900000,true,100,false)==POWER_NOTHING);
 p.idle_enabled=false;assert(power_policy_tick(&p,900000,true,100,true)==POWER_NOTHING);
 assert(power_policy_sleep(&p,900001)==POWER_PAUSE);
 assert(power_policy_resume(&p,900002)==POWER_WAKE && p.last_activity_ms==900002);
 // Timeouts remain correct across 32-bit uptime wrap.
 uint32_t start=UINT32_MAX-1000u;power_policy_init(&p,start,true);
 assert(power_policy_tick(&p,start+89999u,true,start,true)==POWER_NOTHING);
 assert(power_policy_tick(&p,start+90000u,true,start,true)==POWER_PAUSE);
 assert(!power_policy_peer_advertisement(&p,start+90100u));
 assert(power_policy_peer_advertisement(&p,start+92101u));
 puts("PASS: 90-second idle, activity, quiet-gated wake, USB grace/off/resume, manual pause and uptime wrap");
 return 0;
}
