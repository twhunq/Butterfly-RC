// Butterfly RC - ground station: phone (Wi-Fi, browser) -> ESP32 -> NRF24L01 -> butterfly.
//
// The ESP32 opens a Wi-Fi access point; the phone joins it and opens http://192.168.4.1.
// The page sends the stick state to /c every 50 ms; the ESP32 forwards it as a CmdPacket
// at 50 Hz and returns the butterfly telemetry (ack payload) to the page.
// Phone silent for > PHONE_TIMEOUT_MS while flapping: CMD_LAND is set, the butterfly runs its
// auto-landing sequence with the last landing profile the phone sent.
//
// Board: any ESP32 (ESP32 Dev Module) or ESP32-C3 (ESP32C3 Dev Module, USB CDC On Boot: Enabled).
// Library: RF24 by TMRh20. NRF24 VCC from the board 3V3 pin + 10-100 uF across VCC/GND.

#include <WiFi.h>
#include <WebServer.h>
#include <SPI.h>
#include <RF24.h>
#include "protocol.h"
#include "web_ui.h"

// ---------------- configuration ----------------
const char *AP_SSID = "Butterfly-RC";
const char *AP_PASS = "butterfly";     // at least 8 characters
const uint8_t AP_CHANNEL = 1;          // keep 1: NRF24 runs at 2480 MHz, far from it

#if CONFIG_IDF_TARGET_ESP32C3
const int PIN_SCK = 4, PIN_MISO = 5, PIN_MOSI = 6, PIN_CSN = 7, PIN_CE = 3;
#else  // classic ESP32 (VSPI)
const int PIN_SCK = 18, PIN_MISO = 19, PIN_MOSI = 23, PIN_CSN = 5, PIN_CE = 4;
#endif

const uint32_t TX_PERIOD_MS = 20;      // 50 Hz
const uint32_t PHONE_TIMEOUT_MS = 500;
const uint32_t LINK_TIMEOUT_MS = 500;
// ------------------------------------------------

RF24 radio(PIN_CE, PIN_CSN);
WebServer server(80);
bool radioOk = false;

CmdPacket cmd = {BFLY_PROTO, 0, 0, 25, 0, 0, 0, 0, 0, 20};
TelemPacket tlm = {};
uint32_t lastPhoneMs = 0;
uint32_t lastAckMs = 0;
bool everAcked = false;
float linkQ = 0;                       // fraction of packets acked (moving average)

long argClamped(const char *name, long lo, long hi, long def) {
  if (!server.hasArg(name)) return def;
  return constrain(server.arg(name).toInt(), lo, hi);
}

void handleRoot() {
  server.send_P(200, "text/html; charset=utf-8", PAGE);
}

void handleCmd() {
  cmd.flags = (argClamped("a", 0, 1, 0) ? CMD_FLAP : 0) | (argClamped("l", 0, 1, 0) ? CMD_LAND : 0);
  cmd.freq_dHz = argClamped("f", 5, 40, 25);
  cmd.ampR = argClamped("ar", 0, 350, 0);
  cmd.ampL = argClamped("al", 0, 350, 0);
  cmd.offR = argClamped("or", -450, 450, 0);
  cmd.offL = argClamped("ol", -450, 450, 0);
  cmd.landAmp = argClamped("la", 0, 80, 0);
  cmd.landTime_s = argClamped("lt", 0, 120, 20);
  lastPhoneMs = millis();

  bool link = everAcked && (millis() - lastAckMs < LINK_TIMEOUT_MS);
  char buf[160];
  snprintf(buf, sizeof(buf),
           "{\"r\":%d,\"l\":%d,\"q\":%d,\"v\":%u,\"fl\":%u,\"fs\":%u,\"rx\":%u,\"m\":%u,\"ls\":%u}",
           radioOk, link, (int)(linkQ * 100 + 0.5f), tlm.vbat_mV, tlm.flags, tlm.failsafes, tlm.rx_count,
           tlm.mode, tlm.land_s);
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", buf);
}

void radioBegin() {
  SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_CSN);
  radioOk = radio.begin(&SPI);
  if (!radioOk) return;
  radio.setChannel(RF_CHANNEL);
  radio.setDataRate(RF24_250KBPS);
  radio.setPALevel(RF24_PA_MAX);
  radio.setCRCLength(RF24_CRC_16);
  radio.enableDynamicPayloads();
  radio.enableAckPayload();
  radio.setRetries(5, 3);              // 1.5 ms between retries: needed for ack payloads at 250 kbps
  radio.openWritingPipe(RF_ADDR);
  radio.stopListening();
}

void sendCmd() {
  if (millis() - lastPhoneMs > PHONE_TIMEOUT_MS && (cmd.flags & CMD_FLAP)) cmd.flags |= CMD_LAND;
  cmd.proto = BFLY_PROTO;
  cmd.seq++;
  bool ok = radio.write(&cmd, sizeof(cmd));
  linkQ += 0.05f * ((ok ? 1.0f : 0.0f) - linkQ);
  if (!ok) return;
  lastAckMs = millis();
  everAcked = true;
  while (radio.available()) {
    if (radio.getDynamicPayloadSize() != sizeof(TelemPacket)) {
      radio.flush_rx();
      break;
    }
    TelemPacket t;
    radio.read(&t, sizeof(t));
    if (t.proto == BFLY_PROTO) tlm = t;
  }
}

void setup() {
  Serial.begin(115200);
  radioBegin();
  Serial.println(radioOk ? "NRF24 OK" : "NRF24 NOT FOUND - check wiring and 3V3");

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS, AP_CHANNEL);
#if CONFIG_IDF_TARGET_ESP32C3
  WiFi.setTxPower(WIFI_POWER_8_5dBm);  // many C3 "SuperMini" boards drop Wi-Fi at full power
#endif
  WiFi.setSleep(false);                // no power-save latency spikes
  Serial.print("Wi-Fi \"");
  Serial.print(AP_SSID);
  Serial.print("\" -> http://");
  Serial.println(WiFi.softAPIP());

  server.on("/", handleRoot);
  server.on("/c", handleCmd);
  server.onNotFound(handleRoot);
  server.begin();
}

void loop() {
  server.handleClient();

  static uint32_t lastTxMs = 0;
  if (radioOk && millis() - lastTxMs >= TX_PERIOD_MS) {
    lastTxMs = millis();
    sendCmd();
  }
}
