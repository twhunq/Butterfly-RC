// Butterfly RC radio protocol (NRF24L01, 250 kbps, auto-ack + ack payload).
// Two identical copies: firmware/butterfly_rx/protocol.h and firmware/ground_station/protocol.h.
// Change both together and bump BFLY_PROTO.
#pragma once
#include <stdint.h>

#define BFLY_PROTO 2

// 2480 MHz: far above Wi-Fi channel 1 (2401-2423 MHz) that the ground station AP uses.
static const uint8_t RF_CHANNEL = 80;
static const uint8_t RF_ADDR[6] = "BFLY1";

// CmdPacket.flags
static const uint8_t CMD_FLAP = 0x01;      // 0 = stop flapping, hold wings at the offsets
static const uint8_t CMD_LAND = 0x02;      // run the auto-landing sequence now (only while CMD_FLAP)

// Ground -> butterfly, sent at 50 Hz. Angles in 0.1 deg, + = wing up (seen from behind).
struct __attribute__((packed)) CmdPacket {
  uint8_t proto;       // BFLY_PROTO
  uint8_t seq;
  uint8_t flags;
  uint8_t freq_dHz;    // flap frequency, 0.1 Hz
  int16_t ampR;        // flap amplitude (half stroke)
  int16_t ampL;
  int16_t offR;        // stroke centre = glide dihedral + trim
  int16_t offL;
  // Auto-landing profile. Sent every packet, so the butterfly flies the latest one after a link loss.
  // Both wings always get the same amplitude: in the free-flight simulation even 1 deg of
  // differential amplitude rolls the butterfly to 32 deg in 2.4 s, so there is no circling option.
  int16_t landAmp;     // gentle-flap amplitude during the descent, 0 = glide straight away
  uint8_t landTime_s;  // flap this long, then glide with the wings still
};

// TelemPacket.flags
static const uint8_t TLM_FLAPPING = 0x01;
static const uint8_t TLM_LOW_BATT = 0x02;

// TelemPacket.mode
static const uint8_t MODE_PILOT = 0;       // flying the pilot's command (or disarmed)
static const uint8_t MODE_DESCEND = 1;     // auto-landing: gentle flapping (only if landAmp > 0)
static const uint8_t MODE_GLIDE = 2;       // auto-landing: flapping ramped down, wings still, gliding
static const uint8_t MODE_RELAXED = 3;     // auto-landing over for a while: servo pulses off

// Butterfly -> ground, returned in the ack of every CmdPacket (one packet late).
struct __attribute__((packed)) TelemPacket {
  uint8_t proto;
  uint8_t seq;         // seq of the last CmdPacket received
  uint8_t flags;
  uint8_t failsafes;   // link-loss events since power-up (saturates at 255)
  uint16_t vbat_mV;    // 0 if the A0 divider is not fitted
  uint16_t rx_count;
  uint8_t mode;
  uint8_t land_s;      // seconds since the landing sequence started
};
