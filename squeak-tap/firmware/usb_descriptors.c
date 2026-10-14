// USB descriptors for Squeak Tap: a single CDC serial interface.
// Uses the Raspberry Pi Pico SDK's CDC VID/PID so it enumerates with the
// standard Pico serial drivers on every OS.

#include <string.h>
#include "tusb.h"
#include "pico/unique_id.h"

#define USBD_VID 0x2E8A            // Raspberry Pi
#if PICO_RP2040
#define USBD_PID 0x000A            // Pico SDK CDC (RP2040)
#else
#define USBD_PID 0x0009            // Pico SDK CDC
#endif

enum { ITF_CDC = 0, ITF_CDC_DATA, ITF_COUNT };
enum { STR_LANG = 0, STR_MANUF, STR_PRODUCT, STR_SERIAL, STR_CDC };

#define EP_CDC_NOTIF 0x81
#define EP_CDC_OUT   0x02
#define EP_CDC_IN    0x82
#define CONFIG_LEN   (TUD_CONFIG_DESC_LEN + TUD_CDC_DESC_LEN)

static const tusb_desc_device_t desc_device = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = TUSB_CLASS_MISC,
    .bDeviceSubClass = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = USBD_VID,
    .idProduct = USBD_PID,
    .bcdDevice = 0x0100,
    .iManufacturer = STR_MANUF,
    .iProduct = STR_PRODUCT,
    .iSerialNumber = STR_SERIAL,
    .bNumConfigurations = 1,
};

static const uint8_t desc_config[CONFIG_LEN] = {
    TUD_CONFIG_DESCRIPTOR(1, ITF_COUNT, 0, CONFIG_LEN, 0, 100),
    TUD_CDC_DESCRIPTOR(ITF_CDC, STR_CDC, EP_CDC_NOTIF, 8, EP_CDC_OUT, EP_CDC_IN, 64),
};

uint8_t const *tud_descriptor_device_cb(void) {
    return (uint8_t const *)&desc_device;
}

uint8_t const *tud_descriptor_configuration_cb(uint8_t index) {
    (void)index;
    return desc_config;
}

static const char *const strings[] = {
    [STR_MANUF] = "Ethical Paul",
    [STR_PRODUCT] = "Squeak Tap",
    [STR_CDC] = "Squeak Tap capture",
};

uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    static uint16_t buf[33];
    char serial[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];
    const char *s;
    uint8_t n;

    if (index == STR_LANG) {
        buf[1] = 0x0409;
        n = 1;
    } else {
        if (index == STR_SERIAL) {
            pico_get_unique_board_id_string(serial, sizeof serial);
            s = serial;
        } else if (index < sizeof strings / sizeof strings[0] && strings[index]) {
            s = strings[index];
        } else {
            return NULL;
        }
        n = (uint8_t)strlen(s);
        if (n > 32) n = 32;
        for (uint8_t i = 0; i < n; i++) buf[1 + i] = (uint8_t)s[i];
    }
    buf[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2u * n + 2u));
    return buf;
}
