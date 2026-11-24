#ifndef LG_RECONNECT_POLICY_H
#define LG_RECONNECT_POLICY_H
#include <stdbool.h>
#include <stdint.h>
#include "bluetooth.h"

// Retry only known link-loss/timeout statuses; security and unknown errors pause.
// An explicit disconnect/scan must never be undone by a late security event.
static inline bool lg_reencryption_can_retry(uint8_t status, bool enabled) {
    if (!enabled) return false;
    switch (status) {
        case ERROR_CODE_UNKNOWN_CONNECTION_IDENTIFIER:
        case ERROR_CODE_CONNECTION_TIMEOUT:
        case ERROR_CODE_REMOTE_USER_TERMINATED_CONNECTION:
        case ERROR_CODE_REMOTE_DEVICE_TERMINATED_CONNECTION_DUE_TO_LOW_RESOURCES:
        case ERROR_CODE_REMOTE_DEVICE_TERMINATED_CONNECTION_DUE_TO_POWER_OFF:
        case ERROR_CODE_CONNECTION_TERMINATED_BY_LOCAL_HOST:
        case ERROR_CODE_LMP_RESPONSE_TIMEOUT_LL_RESPONSE_TIMEOUT:
        case ERROR_CODE_CONNECTION_FAILED_TO_BE_ESTABLISHED:
            return true;
        default:
            return false;
    }
}

// Repeated transient failures back off instead of hammering the same link.
// Success/explicit resume resets the counter. Ordinary disconnect keeps 300 ms.
static inline uint32_t lg_reencryption_retry_delay(uint8_t failures) {
    if (failures >= 6) return 30000;
    return 1000u << (failures > 0 ? failures - 1 : 0);
}
#endif
