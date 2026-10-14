// Squeak Tap firmware - captures the Cheap Squeak Deluxe DAC bus over USB.
// By Ethical Paul.
//
// Core 1 owns the PIO sampler: it reads every 960 kHz sample, and whenever
// the 11-bit sample (10 DAC bits + MARK) changes it writes one 32-bit
// event word into a RAM ring. Core 0 runs TinyUSB and streams the ring to the
// PC over a USB CDC serial port.
//
// Host protocol (all multi-byte values little-endian):
//   PC sends 'S'  -> device replies with a 16-byte header, then event words
//   PC sends 'X'  -> device stops, drains the ring, sends CTRL_END
//   PC sends 'I'  -> device replies with one ASCII info line
//
// Header: "SQTP" | u32 version | u32 sample_hz | u32 sample_bits
//
// Event word:
//   bits 0-11  sample value (bits 0-9 DAC D0-D9, bit 10 MARK active-low, bit 11 = 0)
//   bits 12-31 ticks (1/sample_hz) since the previous event word
//   The first word after the header has ticks = 0.
//   A word may repeat the previous value: that is a keep-alive for long gaps.
//   ticks == 0xFFFFF marks a control word; bits 0-11 then hold the code.

#include <string.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"
#include "hardware/sync.h"
#include "tusb.h"
#include "sampler.pio.h"

#define FW_VERSION      2u
#define PIN_BASE        2u          // GP2..GP12
#define PIN_COUNT       11u
#define PIN_MARK        12u
#define PIN_LED         25u
#define SYS_KHZ         120000u
#define SAMPLE_HZ       960000u
#define CYCLES_PER_SAMPLE 5u        // must match sampler.pio

#define SAMPLE_MASK     0x7FFu      // raw pins read by the PIO
#define FIELD_MASK      0xFFFu      // sample field in an event word
#define TICKS_SHIFT     12u
#define TICKS_CTRL      0xFFFFFu    // reserved for control words
#define TICKS_MAX       0xFFFFEu    // longest normal gap, about 1.09 s

#define CTRL_OVERFLOW   0x001u      // ring was full, events were dropped
#define CTRL_PIO_STALL  0x002u      // PIO FIFO filled, sample timing slipped
#define CTRL_END        0x0FFu      // capture finished

#define RING_WORDS      (1u << 14)  // 16384 events = 64 KB

static PIO const pio = pio0;
static const uint sm = 0;

static uint32_t ring[RING_WORDS];
static volatile uint32_t ring_wr;   // written by core 1
static volatile uint32_t ring_rd;   // written by core 0
static volatile bool capturing;     // set by core 0
static volatile bool core1_idle = true;
static volatile uint32_t activity;  // event counter for the LED

static inline uint32_t ctrl_word(uint32_t code) {
    return (TICKS_CTRL << TICKS_SHIFT) | (code & FIELD_MASK);
}

// Rev A wiring puts D5-D9 on GP2-GP6 and D0-D4 on GP7-GP11 (the ribbon order
// that keeps both boards' traces uncrossed). Rotate back to D0-D9; keep MARK.
static inline uint32_t __not_in_flash_func(to_dac_order)(uint32_t raw) {
    return ((raw >> 5) & 0x1Fu) | ((raw & 0x1Fu) << 5) | (raw & 0x400u);
}

// ---------------------------------------------------------------- core 1 --

static bool overflow_pending;

static inline void __not_in_flash_func(emit)(uint32_t w) {
    uint32_t wr = ring_wr;
    uint32_t used = wr - ring_rd;
    if (overflow_pending) {
        if (used + 2u > RING_WORDS) return;          // still full: drop
        ring[wr & (RING_WORDS - 1u)] = ctrl_word(CTRL_OVERFLOW);
        wr++;
        overflow_pending = false;
    } else if (used >= RING_WORDS) {
        overflow_pending = true;
        return;
    }
    ring[wr & (RING_WORDS - 1u)] = w;
    __dmb();
    ring_wr = wr + 1u;
}

static void __not_in_flash_func(core1_main)(void) {
    io_ro_32 *rxf = &pio->rxf[sm];
    const uint32_t empty_bit = 1u << (PIO_FSTAT_RXEMPTY_LSB + sm);
    const uint32_t stall_bit = 1u << (PIO_FDEBUG_RXSTALL_LSB + sm);

    for (;;) {
        core1_idle = true;
        while (!capturing) tight_loop_contents();
        core1_idle = false;
        overflow_pending = false;

        pio_sm_set_enabled(pio, sm, false);
        pio_sm_clear_fifos(pio, sm);
        pio_sm_restart(pio, sm);
        pio->fdebug = stall_bit;
        pio_sm_set_enabled(pio, sm, true);

        while (pio->fstat & empty_bit) tight_loop_contents();
        uint32_t last = *rxf & SAMPLE_MASK;
        emit(to_dac_order(last));                     // ticks = 0
        uint32_t since = 0;
        uint32_t check = 0;

        while (capturing) {
            while (pio->fstat & empty_bit) tight_loop_contents();
            uint32_t v = *rxf & SAMPLE_MASK;
            since++;
            if (v != last || since >= TICKS_MAX) {
                emit((since << TICKS_SHIFT) | to_dac_order(v));
                last = v;
                since = 0;
                activity++;
            }
            if ((++check & 0xFFFu) == 0 && (pio->fdebug & stall_bit)) {
                pio->fdebug = stall_bit;
                emit(ctrl_word(CTRL_PIO_STALL));
            }
        }
        pio_sm_set_enabled(pio, sm, false);
    }
}

// ---------------------------------------------------------------- core 0 --

static void cdc_write_all(const void *data, uint32_t len) {
    const uint8_t *p = data;
    while (len) {
        tud_task();
        if (!tud_cdc_connected()) return;
        uint32_t n = tud_cdc_write(p, len);
        p += n;
        len -= n;
        if (n == 0) tud_cdc_write_flush();
    }
}

// Send as many ring words as the CDC FIFO will take right now.
static void pump(void) {
    uint32_t rd = ring_rd;
    uint32_t wr = ring_wr;
    __dmb();
    while (rd != wr) {
        uint32_t room = tud_cdc_write_available() / 4u;
        if (room == 0) break;
        uint32_t idx = rd & (RING_WORDS - 1u);
        uint32_t n = wr - rd;
        if (n > RING_WORDS - idx) n = RING_WORDS - idx;  // up to the wrap
        if (n > room) n = room;
        tud_cdc_write(&ring[idx], n * 4u);
        rd += n;
        __dmb();
        ring_rd = rd;
    }
    tud_cdc_write_flush();
}

static void start_capture(void) {
    if (capturing) return;
    while (!core1_idle) tight_loop_contents();
    ring_rd = 0;
    ring_wr = 0;
    uint32_t hdr[4];
    memcpy(&hdr[0], "SQTP", 4);
    hdr[1] = FW_VERSION;
    hdr[2] = SAMPLE_HZ;
    hdr[3] = PIN_COUNT;
    cdc_write_all(hdr, sizeof hdr);
    __dmb();
    capturing = true;
}

static void stop_capture(bool send_end) {
    if (!capturing) return;
    capturing = false;
    while (!core1_idle) tight_loop_contents();
    if (!send_end) return;
    while (ring_rd != ring_wr && tud_cdc_connected()) {
        tud_task();
        pump();
    }
    uint32_t end = ctrl_word(CTRL_END);
    cdc_write_all(&end, 4);
    tud_cdc_write_flush();
}

static void send_info(void) {
    static const char info[] =
        "Squeak Tap fw 2 (board Rev A), 960000 Hz, 11 bits (D5-D9 GP2-GP6, D0-D4 GP7-GP11, MARK GP12)\n";
    cdc_write_all(info, sizeof info - 1);
    tud_cdc_write_flush();
}

int main(void) {
    set_sys_clock_khz(SYS_KHZ, true);

    gpio_init(PIN_LED);
    gpio_set_dir(PIN_LED, GPIO_OUT);

    uint offset = pio_add_program(pio, &sampler_program);
    float div = (float)clock_get_hz(clk_sys) / (float)(SAMPLE_HZ * CYCLES_PER_SAMPLE);
    sampler_program_init(pio, sm, offset, PIN_BASE, PIN_COUNT, div);
    gpio_pull_up(PIN_MARK);               // button to GND

    multicore_launch_core1(core1_main);

    tud_init(BOARD_TUD_RHPORT);

    uint32_t last_act = 0;
    absolute_time_t led_tick = make_timeout_time_ms(50);

    for (;;) {
        tud_task();

        if (capturing && !tud_cdc_connected()) stop_capture(false);

        while (tud_cdc_available()) {
            uint8_t c = (uint8_t)tud_cdc_read_char();
            if (c == 'S') start_capture();
            else if (c == 'X') stop_capture(true);
            else if (c == 'I') send_info();
        }

        if (capturing) pump();

        // LED: off when idle, on while capturing, flickers with DAC activity.
        if (time_reached(led_tick)) {
            led_tick = make_timeout_time_ms(50);
            uint32_t a = activity;
            bool busy = (a != last_act);
            last_act = a;
            static bool flick;
            flick = !flick;
            gpio_put(PIN_LED, capturing && !(busy && flick));
        }
    }
}
