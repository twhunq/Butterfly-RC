// Butterfly RC - on-board firmware (Arduino Nano V3, ATmega328P + NRF24L01).
//
// Receives CmdPacket from the ground station and flaps both wings with a smooth sine:
//   angle(t) = off + amp * sin(phase),  phase advances by 2*pi*f*dt
// Frequency changes never jump the wing (phase is integrated); amplitude and offset
// are slew-limited.
//
// Auto-landing (no sensors on board, so the sequence is open-loop and time-based):
//   link lost <= HOLD_MS          keep flying the last command (short dropouts are ignored)
//   then, if it was flapping:     DESCEND  - only if landAmp > 0: both wings at the gentle-flap
//                                            amplitude (below level flight) for landTime_s seconds
//                                 GLIDE    - flapping ramped down at LAND_SLEW_DEG_S, wings still at
//                                            the glide offsets until touchdown
//                                 RELAXED  - RELAX_AFTER_S later the servo pulses stop, so a
//                                            servo jammed by a crashed wing does not burn out
//   if it was not flapping:       stays still (never starts flapping on its own)
// Free-flight simulation of this airframe (firmware/README.md, section 4): climb ~ 0.0015*A^2 - 0.11 m/s,
// level flight at about +-8.6 deg, gliding is stable; any left/right amplitude difference spirals.
// The same sequence runs on request (CMD_LAND), e.g. when the ground station loses the phone.
// Any packet without CMD_LAND hands control straight back to the pilot.
//
// Wiring (design/HUONG_DAN_THI_CONG.md, section 8):
//   servo R / L signal  D9 (OC1A) / D10 (OC1B), Timer1 333 Hz - Servo.h is NOT used
//   NRF24 CE / CSN      D7 / D8, SPI D13 / D11 / D12, VCC from a separate 3.3 V LDO
//   battery divider     A0 (20k / 10k, optional)
// Library: RF24 by TMRh20 (Library Manager: "RF24").

#include <SPI.h>
#include <RF24.h>
#include "protocol.h"

// ---------------- configuration ----------------
const uint8_t PIN_CE = 7;
const uint8_t PIN_CSN = 8;
const uint8_t PIN_VBAT = A0;

const uint16_t FRAME_US = 3000;               // servo frame: 3 ms = 333 Hz (digital servo)
const float US_PER_DEG = 2000.0f / 180.0f;     // 500-2500 us = 180 deg

// Pulse at which each horn is horizontal (build guide step 7). Fine trim is done
// from the phone; change these only if a horn is off by a whole spline tooth.
const int16_t CENTER_US_R = 1500;
const int16_t CENTER_US_L = 1500;
// +1 / -1 so that a positive angle lifts the wing. The two servos sit side by side
// with their horns pointing opposite ways, so one of them is normally reversed.
// Check on the bench: arm with a small offset only, both wings must go UP.
const int8_t DIR_R = +1;
const int8_t DIR_L = -1;

const float ANGLE_LIMIT_DEG = 45.0f;   // Fusion: no collision up to +-45 deg
const float AMP_MAX_DEG = 35.0f;
const float FREQ_MIN_HZ = 0.5f;
const float FREQ_MAX_HZ = 4.0f;
// Peak wing speed = 2*pi*f*amp. 110 deg*Hz = 690 deg/s, about what the PTK 7465Plus
// can follow on 2S under wing load. Above this the servo lags and overheats.
const float AMP_FREQ_MAX = 110.0f;
const float AMP_SLEW_DEG_S = 80.0f;    // amplitude change rate
const float OFF_SLEW_DEG_S = 60.0f;    // offset / trim change rate

// Auto-landing. The profile (amplitude, time) comes from the phone with every packet
// (defaults and their reasoning: firmware/README.md, section 4); these are hard limits.
const uint32_t HOLD_MS = 500;
const float LAND_FREQ_HZ = 2.5f;       // the frequency the descent amplitudes were simulated at
const float LAND_SLEW_DEG_S = 10.0f;   // slow amplitude changes: no pitch jolt when the thrust drops
const float LAND_AMP_MAX = 8.0f;       // simulation: +-10 deg already holds height, so stay below
const uint8_t LAND_TIME_MAX_S = 120;
const uint16_t RELAX_AFTER_S = 30;     // after the descent ends

const uint32_t LINK_STAT_MS = 500;     // a link-loss event is counted after this long

const bool VBAT_FITTED = true;         // false if the A0 divider is not soldered
const float VBAT_SCALE = 5.0f * 3.0f / 1023.0f;   // Vref 5 V, divider x3 (calibrate if needed)
const uint16_t VBAT_LOW_MV = 6600;     // 3.3 V per cell under load: warning on the phone
const uint16_t VBAT_LAND_MV = 6300;    // during auto-landing: stop flapping and glide

#define DEBUG_SERIAL 0                 // 1: print status at 2 Hz on USB serial (115200)
// ------------------------------------------------

RF24 radio(PIN_CE, PIN_CSN);
bool radioOk = false;

CmdPacket cmd;
TelemPacket tlm;
bool haveCmd = false;
bool linkLost = true;
bool lowBatt = false;
uint32_t lastRxMs = 0;

bool landing = false;
uint32_t landStartMs = 0;
bool servosOn = false;

float phase = 0;          // rad
float ampR = 0, ampL = 0; // current (slewed) values, deg
float offR = 0, offL = 0;
float freqHz = 2.5f;
uint32_t lastUpdUs = 0;

static inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

static inline float slew(float cur, float target, float maxStep) {
  if (target > cur + maxStep) return cur + maxStep;
  if (target < cur - maxStep) return cur - maxStep;
  return target;
}

void servoTimerBegin() {
  pinMode(9, OUTPUT);
  pinMode(10, OUTPUT);
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;
  ICR1 = 2 * FRAME_US - 1;                              // 0.5 us ticks (16 MHz / 8)
  TCCR1A = _BV(WGM11);                                  // mode 14 (fast PWM, TOP = ICR1), outputs off
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS11);         // prescaler 8
  servosOn = false;
}

// Connect / disconnect OC1A and OC1B. Off = pins held low, no pulses, servos go limp.
void servoOutputs(bool on) {
  if (on == servosOn) return;
  servosOn = on;
  if (on) {
    TCCR1A |= _BV(COM1A1) | _BV(COM1B1);
  } else {
    TCCR1A &= ~(_BV(COM1A1) | _BV(COM1B1));
    digitalWrite(9, LOW);
    digitalWrite(10, LOW);
  }
}

// OCR1x is double-buffered in mode 14: the new width starts at the next frame, no glitch.
void writeServos(float angR, float angL) {
  angR = clampf(angR, -ANGLE_LIMIT_DEG, ANGLE_LIMIT_DEG);
  angL = clampf(angL, -ANGLE_LIMIT_DEG, ANGLE_LIMIT_DEG);
  uint16_t usR = (uint16_t)(CENTER_US_R + DIR_R * angR * US_PER_DEG + 0.5f);
  uint16_t usL = (uint16_t)(CENTER_US_L + DIR_L * angL * US_PER_DEG + 0.5f);
  OCR1A = 2 * usR - 1;
  OCR1B = 2 * usL - 1;
}

uint16_t readVbat_mV() {
  if (!VBAT_FITTED) return 0;
  static float filt = -1;
  float v = analogRead(PIN_VBAT) * VBAT_SCALE;
  filt = (filt < 0) ? v : filt + 0.1f * (v - filt);   // flapping draws current pulses
  return (uint16_t)(filt * 1000.0f);
}

void radioBegin() {
  radioOk = radio.begin();
  if (!radioOk) return;
  radio.setChannel(RF_CHANNEL);
  radio.setDataRate(RF24_250KBPS);
  radio.setPALevel(RF24_PA_MAX);
  radio.setCRCLength(RF24_CRC_16);
  radio.enableDynamicPayloads();
  radio.enableAckPayload();
  radio.openReadingPipe(1, RF_ADDR);
  radio.startListening();                 // flushes TX FIFO, so load the ack after this
  tlm.proto = BFLY_PROTO;
  radio.writeAckPayload(1, &tlm, sizeof(tlm));
}

void pollRadio() {
  if (!radioOk) return;
  uint8_t pipe;
  while (radio.available(&pipe)) {
    uint8_t len = radio.getDynamicPayloadSize();
    if (len != sizeof(CmdPacket)) {       // wrong size or corrupt: drop it
      radio.flush_rx();
      return;
    }
    CmdPacket p;
    radio.read(&p, sizeof(p));
    if (p.proto != BFLY_PROTO) continue;
    cmd = p;
    haveCmd = true;
    lastRxMs = millis();
    tlm.seq = p.seq;
    tlm.rx_count++;
    radio.writeAckPayload(1, &tlm, sizeof(tlm));   // answered with the next packet
  }
}

void updateServos() {
  uint32_t now = micros();
  float dt = (now - lastUpdUs) * 1e-6f;
  lastUpdUs = now;
  if (dt > 0.05f) dt = 0.05f;
  uint32_t nowMs = millis();

  bool statLost = !haveCmd || (nowMs - lastRxMs > LINK_STAT_MS);
  if (statLost && !linkLost && haveCmd && tlm.failsafes < 255) tlm.failsafes++;
  linkLost = statLost;

  bool lost = !haveCmd || (nowMs - lastRxMs > HOLD_MS);
  bool armed = haveCmd && (cmd.flags & CMD_FLAP);         // last known state
  bool wantLand = armed && (lost || (cmd.flags & CMD_LAND));
  if (!wantLand) {
    landing = false;
  } else if (!landing) {
    landing = true;
    landStartMs = nowMs;
  }

  float tAmpR = 0, tAmpL = 0;
  float tOffR = offR, tOffL = offL;
  float ampSlew = AMP_SLEW_DEG_S;
  uint8_t mode = MODE_PILOT;
  bool outputs = true;
  if (haveCmd) {                          // offsets: the last received ones, also after a loss
    tOffR = clampf(cmd.offR * 0.1f, -ANGLE_LIMIT_DEG, ANGLE_LIMIT_DEG);
    tOffL = clampf(cmd.offL * 0.1f, -ANGLE_LIMIT_DEG, ANGLE_LIMIT_DEG);
  }

  if (landing) {
    uint32_t t_ms = nowMs - landStartMs;
    uint8_t landTime = min(cmd.landTime_s, LAND_TIME_MAX_S);
    float landAmp = clampf(cmd.landAmp * 0.1f, 0, LAND_AMP_MAX);
    bool battOk = !(tlm.vbat_mV && tlm.vbat_mV < VBAT_LAND_MV);
    freqHz = LAND_FREQ_HZ;
    ampSlew = LAND_SLEW_DEG_S;
    if (landAmp >= 0.5f && t_ms < landTime * 1000UL && battOk) {
      mode = MODE_DESCEND;
      tAmpR = tAmpL = landAmp;
    } else {
      mode = MODE_GLIDE;
      // relax only while the link is down; with the pilot watching (CMD_LAND) keep holding
      if (lost && t_ms >= (landTime + (uint32_t)RELAX_AFTER_S) * 1000UL) {
        mode = MODE_RELAXED;
        outputs = false;
      }
    }
    uint32_t s = t_ms / 1000;
    tlm.land_s = s > 255 ? 255 : s;
  } else {
    tlm.land_s = 0;
    if (haveCmd) freqHz = clampf(cmd.freq_dHz * 0.1f, FREQ_MIN_HZ, FREQ_MAX_HZ);
    if (armed && !lost) {
      float ampLim = min(AMP_MAX_DEG, AMP_FREQ_MAX / freqHz);
      tAmpR = clampf(cmd.ampR * 0.1f, 0, ampLim);
      tAmpL = clampf(cmd.ampL * 0.1f, 0, ampLim);
    }
  }

  ampR = slew(ampR, tAmpR, ampSlew * dt);
  ampL = slew(ampL, tAmpL, ampSlew * dt);
  offR = slew(offR, tOffR, OFF_SLEW_DEG_S * dt);
  offL = slew(offL, tOffL, OFF_SLEW_DEG_S * dt);

  phase += TWO_PI * freqHz * dt;
  if (phase >= TWO_PI) phase -= TWO_PI;
  float s = sin(phase);
  writeServos(offR + ampR * s, offL + ampL * s);
  servoOutputs(outputs);

  tlm.mode = mode;
  tlm.flags = ((ampR > 0.5f || ampL > 0.5f) ? TLM_FLAPPING : 0) | (lowBatt ? TLM_LOW_BATT : 0);
}

void setup() {
#if DEBUG_SERIAL
  Serial.begin(115200);
#endif
  servoTimerBegin();
  writeServos(0, 0);                      // horns horizontal: mount them now (guide step 7)
  servoOutputs(true);
  radioBegin();
#if DEBUG_SERIAL
  Serial.println(radioOk ? F("NRF24 OK") : F("NRF24 NOT FOUND - check 3.3 V LDO and wiring"));
#endif
  lastUpdUs = micros();
}

void loop() {
  pollRadio();

  if (TIFR1 & _BV(TOV1)) {                // once per servo frame
    TIFR1 = _BV(TOV1);
    updateServos();
  }

  static uint32_t lastBattMs = 0;
  if (millis() - lastBattMs >= 100) {
    lastBattMs = millis();
    tlm.vbat_mV = readVbat_mV();
    lowBatt = tlm.vbat_mV && tlm.vbat_mV < VBAT_LOW_MV;
  }

#if DEBUG_SERIAL
  static uint32_t lastDbgMs = 0;
  if (millis() - lastDbgMs >= 500) {
    lastDbgMs = millis();
    static const char *const modes[] = {"pilot", "DESCEND", "GLIDE", "RELAXED"};
    Serial.print(linkLost ? F("LOST ") : F("ok   "));
    Serial.print(modes[tlm.mode & 3]);
    Serial.print(F(" t=")); Serial.print(tlm.land_s);
    Serial.print(F(" f=")); Serial.print(freqHz, 1);
    Serial.print(F(" ampR=")); Serial.print(ampR, 1);
    Serial.print(F(" ampL=")); Serial.print(ampL, 1);
    Serial.print(F(" offR=")); Serial.print(offR, 1);
    Serial.print(F(" offL=")); Serial.print(offL, 1);
    Serial.print(F(" vbat=")); Serial.print(tlm.vbat_mV);
    Serial.print(F(" rx=")); Serial.println(tlm.rx_count);
  }
#endif
}
