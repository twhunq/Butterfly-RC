// Host test for firmware/butterfly_rx: fake time + Timer1 registers, runs the real sketch code.
// Build (from firmware/test):  g++ -std=c++17 -I stub -I ../butterfly_rx host_test.cpp -o host_test && ./host_test
// (or "zig c++" instead of g++ on Windows)
#include <cstdint>
#include <cmath>
#include <cstdio>
#include <algorithm>
using std::min;
#define F(x) x
#define _BV(b) (1u << (b))
enum { COM1A1 = 7, COM1B1 = 5, WGM11 = 1, WGM13 = 4, WGM12 = 3, CS11 = 1, TOV1 = 0 };
enum { A0 = 14, OUTPUT = 1, LOW = 0 };
static const float TWO_PI = 6.283185307f;
uint16_t TCCR1A, TCCR1B, TCNT1, ICR1, OCR1A, OCR1B, TIFR1;
uint64_t nowUs = 0;
int adcValue = 545;                                    // ~8.0 V
uint32_t millis() { return nowUs / 1000; }
uint32_t micros() { return (uint32_t)nowUs; }
void pinMode(int, int) {}
void digitalWrite(int, int) {}
int analogRead(int) { return adcValue; }
#include "butterfly_rx.ino"

// --- harness ---
float angR() { return ((OCR1A + 1) / 2.0f - CENTER_US_R) / US_PER_DEG * DIR_R; }
float angL() { return ((OCR1B + 1) / 2.0f - CENTER_US_L) / US_PER_DEG * DIR_L; }
bool outputsOn() { return TCCR1A & _BV(COM1A1); }
uint8_t seqN = 0;
// landing profile defaults below = the phone defaults (glide straight away, 20 s)
void send(uint8_t flags, float amp, float landAmp = 0, uint8_t landT = 20, float off = 0) {
  CmdPacket p{BFLY_PROTO, seqN++, flags, 25, (int16_t)(amp * 10), (int16_t)(amp * 10), (int16_t)(off * 10),
              (int16_t)(off * 10), (int16_t)(landAmp * 10), landT};
  RF24::rx.emplace_back((uint8_t *)&p, (uint8_t *)&p + sizeof(p));
}
// run for `sec`; `link` = send a packet every 20 ms; returns the stroke half-amplitudes seen in the last 0.4 s
struct Obs { float ampR, ampL, mid; bool out; uint8_t mode; };
Obs run(float sec, bool link, uint8_t flags = 0, float amp = 0, float landAmp = 0, uint8_t landT = 20, float off = 0) {
  float rmin = 1e9, rmax = -1e9, lmin = 1e9, lmax = -1e9;
  uint64_t end = nowUs + (uint64_t)(sec * 1e6), lastTx = 0;
  while (nowUs < end) {
    if (link && nowUs - lastTx >= 20000) { lastTx = nowUs; send(flags, amp, landAmp, landT, off); }
    nowUs += 3000;
    TIFR1 = 1;                                          // timer overflow each 3 ms frame
    loop();
    if (end - nowUs < 400000) {
      rmin = std::min(rmin, angR()); rmax = std::max(rmax, angR());
      lmin = std::min(lmin, angL()); lmax = std::max(lmax, angL());
    }
  }
  return {(rmax - rmin) / 2, (lmax - lmin) / 2, (rmax + rmin) / 2, outputsOn(), tlm.mode};
}
int fails = 0;
void check(const char *what, bool ok, Obs o) {
  printf("%s %-58s ampR %5.1f ampL %5.1f mid %5.1f out %d mode %d\n", ok ? "PASS" : "FAIL", what, o.ampR, o.ampL, o.mid, o.out, o.mode);
  if (!ok) fails++;
}
void reset() {
  nowUs = 1000000; RF24::rx.clear(); haveCmd = false; landing = false; ampR = ampL = offR = offL = 0; phase = 0;
  tlm = TelemPacket{}; adcValue = 545; setup();
}
int main() {
  Obs o;
  reset();
  o = run(2, false);                         check("power-up, no packets: wings still at 0", o.ampR < 0.1f && fabsf(o.mid) < 0.1f && o.out, o);
  o = run(5, false);                         check("still no packets after 7 s: never flaps", o.ampR < 0.1f && o.mode == MODE_PILOT, o);

  reset();
  o = run(3, true, 0, 20, 0, 20, 3);         check("disarmed on the ground, glide offset 3", o.ampR < 0.1f && fabsf(o.mid - 3) < 0.2f, o);
  o = run(90, false);                        check("disarmed + link lost 90 s: no flapping, holds offset", o.ampR < 0.1f && fabsf(o.mid - 3) < 0.2f && o.mode == MODE_PILOT && o.out, o);

  // default profile: glide straight away
  reset();
  o = run(5, true, CMD_FLAP, 20, 0, 20, 2);  check("pilot flying +-20, glide offset 2", fabsf(o.ampR - 20) < 0.3f && fabsf(o.ampL - 20) < 0.3f, o);
  o = run(0.45f, false);                     check("link lost 0.45 s: still +-20 (hold)", fabsf(o.ampR - 20) < 0.3f && o.mode == MODE_PILOT, o);
  o = run(0.55f, false);                     check("lost 1.0 s: flapping ramping down (10 deg/s), not cut", o.ampR > 14 && o.ampR < 19 && o.mode == MODE_GLIDE, o);
  o = run(2.5f, false);                      check("lost 3.5 s: gliding, wings still at offset 2", o.ampR < 0.1f && fabsf(o.mid - 2) < 0.2f && o.mode == MODE_GLIDE && o.out, o);
  o = run(26, false);                        check("lost 29.5 s: still holding the glide", o.mode == MODE_GLIDE && o.out, o);
  o = run(23, false);                        check("lost 52.5 s (20+30 s after start): servos relaxed", o.mode == MODE_RELAXED && !o.out, o);
  o = run(2, true, CMD_FLAP, 20, 0, 20, 2);  check("link back: pilot control, pulses on, +-20", fabsf(o.ampR - 20) < 0.3f && o.out && o.mode == MODE_PILOT, o);

  // optional gentle flap
  reset();
  o = run(3, true, CMD_FLAP, 25, 6, 10);
  o = run(3, false);                         check("landAmp 6: lost 3 s, both wings +-6", fabsf(o.ampR - 6) < 0.3f && fabsf(o.ampL - 6) < 0.3f && o.mode == MODE_DESCEND, o);
  o = run(9, false);                         check("landAmp 6, landTime 10: lost 12 s, gliding", o.ampR < 0.1f && o.mode == MODE_GLIDE, o);
  o = run(1, true, CMD_FLAP, 25, 6, 10);     check("link back: pilot +-25 again", fabsf(o.ampR - 25) < 0.3f && o.mode == MODE_PILOT, o);

  reset();
  o = run(3, true, CMD_FLAP, 20, 40, 200);   // out-of-range profile from a bad packet
  o = run(5, false);                         check("landAmp 40 / landTime 200 clamped: +-8", fabsf(o.ampR - 8) < 0.3f && fabsf(o.ampL - 8) < 0.3f && o.mode == MODE_DESCEND, o);

  // pilot-commanded landing, link stays up
  reset();
  o = run(3, true, CMD_FLAP, 20, 5, 5);
  o = run(3, true, CMD_FLAP | CMD_LAND, 20, 5, 5); check("CMD_LAND with landAmp 5: both wings +-5", fabsf(o.ampR - 5) < 0.3f && fabsf(o.ampL - 5) < 0.3f && o.mode == MODE_DESCEND, o);
  o = run(80, true, CMD_FLAP | CMD_LAND, 20, 5, 5); check("CMD_LAND 83 s with link: glide, never relaxes", o.ampR < 0.1f && o.mode == MODE_GLIDE && o.out, o);
  o = run(2, true, CMD_FLAP, 20, 5, 5);      check("LAND cancelled: pilot +-20", fabsf(o.ampR - 20) < 0.3f && o.mode == MODE_PILOT, o);

  reset();
  o = run(3, true, CMD_FLAP, 20, 6, 30);
  adcValue = 423;                            // ~6.2 V
  o = run(7, false);                         check("battery 6.2 V during landing: skips the gentle flap", o.ampR < 0.1f && o.mode == MODE_GLIDE, o);
  printf("telemetry: vbat %u mV, lowBatt flag %d, failsafes %u\n", tlm.vbat_mV, (tlm.flags & TLM_LOW_BATT) != 0, tlm.failsafes);

  printf(fails ? "\n%d FAILED\n" : "\nall passed\n", fails);
  return fails != 0;
}
