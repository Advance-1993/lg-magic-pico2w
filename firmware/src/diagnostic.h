#pragma once
#include <stdint.h>
#include <stdbool.h>
void diag_init(void);
void diag_log(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
void diag_hex(const char *kind, unsigned service, unsigned id, const uint8_t *data, unsigned len);
void diag_usb_task(void);
bool diag_get_command(char *command);
