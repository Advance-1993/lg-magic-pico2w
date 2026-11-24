#include "reconnect_policy.h"
#include <assert.h>
int main(void) {
    const unsigned allowed[] = {0x02,0x08,0x13,0x14,0x15,0x16,0x22,0x3E};
    for (unsigned status=0; status<256; ++status) {
        bool expected=false;
        for (unsigned i=0;i<sizeof(allowed)/sizeof(allowed[0]);++i)
            if (status==allowed[i]) expected=true;
        assert(lg_reencryption_can_retry((uint8_t)status,true)==expected);
        assert(!lg_reencryption_can_retry((uint8_t)status,false));
    }
    // Never retry genuine security failures, success, or unknown errors.
    assert(!lg_reencryption_can_retry(ERROR_CODE_AUTHENTICATION_FAILURE,true));
    assert(!lg_reencryption_can_retry(ERROR_CODE_PIN_OR_KEY_MISSING,true));
    assert(!lg_reencryption_can_retry(ERROR_CODE_CONNECTION_TERMINATED_DUE_TO_MIC_FAILURE,true));
    assert(!lg_reencryption_can_retry(ERROR_CODE_SUCCESS,true));
    const unsigned delays[]={1000,1000,2000,4000,8000,16000,30000,30000};
    for (unsigned i=0;i<sizeof(delays)/sizeof(delays[0]);++i)
        assert(lg_reencryption_retry_delay((uint8_t)i)==delays[i]);
    assert(lg_reencryption_retry_delay(255)==30000);
    return 0;
}
