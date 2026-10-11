#pragma once
#include <deque>
#include <vector>
#include <cstring>
#include <cstdint>
enum { RF24_250KBPS, RF24_PA_MAX, RF24_CRC_16 };
struct RF24 {
  static std::deque<std::vector<uint8_t>> rx;
  static std::vector<uint8_t> ack;
  RF24(int, int) {}
  bool begin() { return true; }
  void setChannel(int) {} void setDataRate(int) {} void setPALevel(int) {} void setCRCLength(int) {}
  void enableDynamicPayloads() {} void enableAckPayload() {}
  void openReadingPipe(int, const uint8_t *) {} void startListening() {}
  bool available(uint8_t *p) { if (p) *p = 1; return !rx.empty(); }
  uint8_t getDynamicPayloadSize() { return rx.front().size(); }
  void flush_rx() { rx.clear(); }
  void read(void *b, uint8_t n) { memcpy(b, rx.front().data(), n); rx.pop_front(); }
  bool writeAckPayload(int, const void *b, uint8_t n) { ack.assign((const uint8_t *)b, (const uint8_t *)b + n); return true; }
};
std::deque<std::vector<uint8_t>> RF24::rx;
std::vector<uint8_t> RF24::ack;
