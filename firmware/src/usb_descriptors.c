/*
 * The MIT License (MIT)
 *
 * Copyright (c) 2019 Ha Thach (tinyusb.org)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 */

#include "bsp/board_api.h"
#include "tusb.h"
#include "usb_descriptors.h"
#if LG_ENABLE_HID
#define LG_PID 0x4005
#define LG_INTERFACE_COUNT 3
#define LG_CONFIGURATION_LENGTH (TUD_CONFIG_DESC_LEN+TUD_CDC_DESC_LEN+TUD_HID_DESC_LEN)
static const uint8_t hid_descriptor[]={
 TUD_HID_REPORT_DESC_KEYBOARD(HID_REPORT_ID(REPORT_ID_KEYBOARD)),
 TUD_HID_REPORT_DESC_MOUSE(HID_REPORT_ID(REPORT_ID_MOUSE)),
 TUD_HID_REPORT_DESC_CONSUMER(HID_REPORT_ID(REPORT_ID_CONSUMER_CONTROL))
};
const uint8_t *tud_hid_descriptor_report_cb(uint8_t instance) { (void)instance; return hid_descriptor; }
#else
#define LG_PID 0x4001
#define LG_INTERFACE_COUNT 2
#define LG_CONFIGURATION_LENGTH (TUD_CONFIG_DESC_LEN+TUD_CDC_DESC_LEN)
#endif
// TinyUSB example VID/PID for personal development, CDC-only interface.
static const tusb_desc_device_t device = {
 .bLength=sizeof(tusb_desc_device_t), .bDescriptorType=TUSB_DESC_DEVICE,
 .bcdUSB=0x0200, .bDeviceClass=TUSB_CLASS_MISC,
 .bDeviceSubClass=MISC_SUBCLASS_COMMON, .bDeviceProtocol=MISC_PROTOCOL_IAD,
 .bMaxPacketSize0=64, .idVendor=0xCAFE, .idProduct=LG_PID,
 .bcdDevice=0x0100, .iManufacturer=1, .iProduct=2, .iSerialNumber=3, .bNumConfigurations=1
};
uint8_t const *tud_descriptor_device_cb(void) { return (const uint8_t *)&device; }
static const uint8_t configuration[] = {
 TUD_CONFIG_DESCRIPTOR(1, LG_INTERFACE_COUNT, 0, LG_CONFIGURATION_LENGTH, 0, 250),
 TUD_CDC_DESCRIPTOR(0, 0, 0x81, 8, 0x02, 0x82, 64),
#if LG_ENABLE_HID
 TUD_HID_DESCRIPTOR(2, 0, HID_ITF_PROTOCOL_NONE, sizeof(hid_descriptor), 0x83, CFG_TUD_HID_EP_BUFSIZE, 1)
#endif
};
uint8_t const *tud_descriptor_configuration_cb(uint8_t index) { (void)index; return configuration; }
// String Descriptor Index
enum {
    STRID_LANGID = 0,
    STRID_MANUFACTURER,
    STRID_PRODUCT,
    STRID_SERIAL,
};

// array of pointer to string descriptors
char const *string_desc_arr[] =
{
    (const char[]) { 0x09, 0x04 }, // 0: is supported language is English (0x0409)
    "LG Magic Pico Project",          // 1: Manufacturer
    "LG Magic USB Bridge",            // 2: Product
    NULL,                          // 3: Serials will use unique ID if possible
};

static uint16_t _desc_str[32 + 1];

// Invoked when received GET STRING DESCRIPTOR request
// Application return pointer to descriptor, whose contents must exist long enough for transfer to complete
uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void) langid;
    size_t chr_count;

    switch ( index ) {
        case STRID_LANGID:
            memcpy(&_desc_str[1], string_desc_arr[0], 2);
            chr_count = 1;
            break;

        case STRID_SERIAL:
            chr_count = board_usb_get_serial(_desc_str + 1, 32);
            break;

        default:
            // Note: the 0xEE index string is a Microsoft OS 1.0 Descriptors.
            // https://docs.microsoft.com/en-us/windows-hardware/drivers/usbcon/microsoft-defined-usb-descriptors

            if ( !(index < sizeof(string_desc_arr) / sizeof(string_desc_arr[0])) ) return NULL;

            const char *str = string_desc_arr[index];

            // Cap at max char
            chr_count = strlen(str);
            size_t const max_count = sizeof(_desc_str) / sizeof(_desc_str[0]) - 1; // -1 for string type
            if ( chr_count > max_count ) chr_count = max_count;

            // Convert ASCII string into UTF-16
            for ( size_t i = 0; i < chr_count; i++ ) {
                _desc_str[1 + i] = str[i];
            }
            break;
    }

    // first byte is length (including header), second byte is string type
    _desc_str[0] = (uint16_t) ((TUSB_DESC_STRING << 8) | (2 * chr_count + 2));

    return _desc_str;
}
