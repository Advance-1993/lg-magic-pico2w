#pragma once
typedef int critical_section_t;
static inline void critical_section_init(critical_section_t *p) { *p=0; }
static inline void critical_section_enter_blocking(critical_section_t *p) { (void)p; }
static inline void critical_section_exit(critical_section_t *p) { (void)p; }
