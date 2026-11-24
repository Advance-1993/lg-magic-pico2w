"""Compile the production snapshot/admission functions against real SDK structs.
The network state machine is tested separately by hid_reconnect_test.c and hardware.
No copy of the snapshot implementation is maintained in this test.
"""
from pathlib import Path
import os,subprocess,tempfile
project=Path(__file__).resolve().parents[1]
sdk=Path(os.environ.get('PICO_SDK_PATH',str(project/'tools/pico-sdk')))
compiler=os.environ.get('CC','gcc')
source=(project/'firmware/src/hids_client_cached.c').read_text()
chunk=source[source.index('// One RAM snapshot,'):source.index('uint8_t lg_hids_connect_cached(')]
test=(project/'tests/hids_cache_snapshot_test.c').read_text()
test=test.replace('#include "../firmware/src/hids_client_cached.c"','#include "snapshot_under_test.h"')
header='''#include "btstack.h"
#include "diagnostic.h"
static uint16_t lg_bad_subscription_cid,lg_discovered_ccc[15],lg_cached_ccc[15];
static bool lg_fail_next,lg_cache_permitted;
static hids_client_t *test_client;
static btstack_linked_list_t clients;
static uint8_t *hids_client_descriptor_storage;
static uint16_t hids_client_descriptor_storage_len;
static hids_client_t *hids_get_client_for_cid(uint16_t cid) {
 (void)test_client;hids_client_t*c=(hids_client_t*)clients;return c&&c->cid==cid?c:NULL;
}
static const uint8_t *hids_client_descriptor_storage_get_descriptor_data_test(uint16_t cid,uint8_t i){
 (void)i;hids_client_t*c=hids_get_client_for_cid(cid);return hids_client_descriptor_storage+c->services[0].hid_descriptor_offset;
}
#define hids_client_descriptor_storage_get_descriptor_data hids_client_descriptor_storage_get_descriptor_data_test
'''
with tempfile.TemporaryDirectory(prefix='lg-hids-snapshot-') as tmp:
 d=Path(tmp);(d/'snapshot_under_test.h').write_text(header+chunk)
 (d/'test.c').write_text(test)
 exe=d/'snapshot.exe'
 env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env['PATH']
 subprocess.run([compiler,'-std=c11','-DENABLE_BLE','-Wall','-Wextra','-Werror','-Wno-unused-variable',
  '-I'+str(project/'firmware/src'),'-I'+str(sdk/'lib/btstack/src'),str(d/'test.c'),'-o',str(exe)],check=True,env=env)
 subprocess.run([str(exe)],check=True,env=env)
