# Firmware bướm RC — điều khiển bằng điện thoại

```
Điện thoại ──Wi‑Fi──► ESP32 + NRF24 (trạm phát) ──NRF24 2480 MHz──► Nano + NRF24 (trên bướm)
 (trình duyệt)          web 192.168.4.1                    ◄── ack: điện áp pin, số gói
```

Điện thoại không nói chuyện trực tiếp với NRF24, nên cần một **trạm phát** ở dưới đất: ESP32 phát Wi‑Fi, phục vụ trang điều khiển, rồi chuyển lệnh sang NRF24. Phần cứng trên bướm giữ nguyên (Nano + NRF24, không thêm khối lượng). Sau này làm tay phát có cần gạt thì chỉ cần thay trạm phát, firmware trên bướm vẫn giữ nguyên.

| Thư mục | Nạp vào | Board trong Arduino IDE |
|---|---|---|
| `butterfly_rx/` | Arduino Nano trên bướm | **Arduino Nano**, Processor **ATmega328P** (bản clone cũ: *ATmega328P (Old Bootloader)*) |
| `ground_station/` | ESP32 trạm phát | **ESP32 Dev Module**, hoặc **ESP32C3 Dev Module** (bật *USB CDC On Boot*) |

`protocol.h` có 2 bản giống hệt nhau trong 2 thư mục. Nếu sửa thì sửa cả 2 và tăng `BFLY_PROTO`.

## 1. Cài đặt

1. Arduino IDE 2: *Boards Manager* → cài **Arduino AVR Boards** và **esp32** (Espressif).
2. *Library Manager* → cài **RF24** (TMRh20). Đã thử với RF24 1.6.2, AVR core 1.8.8, esp32 core 3.3.8.
3. Không cần thư viện Wi‑Fi hay web nào khác (dùng `WiFi.h` / `WebServer.h` có sẵn trong core ESP32).

## 2. Đấu dây trạm phát

NRF24 lấy nguồn từ chân **3V3** của board ESP32, hàn thêm tụ 10–100µF sát chân VCC/GND của module.

| NRF24 | ESP32 (Dev Module) | ESP32‑C3 |
|---|---|---|
| VCC | 3V3 | 3V3 |
| GND | GND | GND |
| CE | GPIO 4 | GPIO 3 |
| CSN | GPIO 5 | GPIO 7 |
| SCK | GPIO 18 | GPIO 4 |
| MOSI | GPIO 23 | GPIO 6 |
| MISO | GPIO 19 | GPIO 5 |
| IRQ | không nối | không nối |

Dùng board khác thì sửa các hằng `PIN_*` ở đầu `ground_station.ino`. Bướm đấu theo `design/HUONG_DAN_THI_CONG.md`, mục 8.

## 3. Dùng

1. Cắm nguồn trạm phát (pin dự phòng USB). Mở Serial Monitor 115200 nếu muốn xem log: `NRF24 OK`.
2. Điện thoại kết nối Wi‑Fi **`Butterfly-RC`**, mật khẩu **`butterfly`**. Android báo "không có Internet" thì chọn **giữ kết nối**.
3. Mở trình duyệt, vào **`http://192.168.4.1`**, xoay ngang điện thoại.
4. Cắm pin cho bướm. Thanh trên cùng phải hiện `Trạm OK`, `Bướm xx%` (xanh) và điện áp pin.

| Điều khiển | Tác dụng |
|---|---|
| Ô trái (kéo lên/xuống) | **Ga** = biên độ vỗ, 0 → biên độ tối đa (mặc định 30°). Thả tay thì giữ nguyên |
| Ô phải (kéo trái/phải) | **Lái**: lệch biên độ hai cánh, tối đa 3° mỗi bên (mặc định). Lái phải thì cánh trái vỗ mạnh hơn, cánh phải yếu hơn. Thả tay thì về giữa. Bướm rất nhạy với lệch biên độ (mục 4): lái nhẹ và ngắn |
| `−` / `+` | Tần số vỗ, bước 0,1 Hz (mặc định 2,5 Hz) |
| **BẬT VỖ / TẮT VỖ** | Chỉ bật được khi ga đang ở 0. TẮT VỖ khi đang bay: cánh dừng ngay ở góc lượn, không chạy kịch bản hạ cánh |
| **HẠ CÁNH** | Bướm tự hạ cánh (mục 4); ga và lái bị khóa. Bấm lần nữa (HỦY HẠ CÁNH) để lái lại |
| ⚙ | Biên độ tối đa, độ lệch khi lái, góc lượn (nhị diện), trim từng cánh, đảo chiều lái, thông số tự hạ cánh. Lưu trong điện thoại |

Ga 50% ứng với ±15°, 67% ứng với ±20°. Theo mô phỏng cánh v3.1: khoảng ±9° là bay ngang, ±15° leo 0,2 m/s, ±20° leo 0,5 m/s (mục 4). Ngoài thực tế cần biên độ lớn hơn một chút.

## 4. Tự hạ cánh an toàn

Trên bướm không có cảm biến (không IMU, không đo độ cao), nên Nano hạ cánh theo **kịch bản định sẵn theo thời gian**. Kịch bản được chọn từ mô phỏng bay tự do của chính bản vẽ hiện tại (bảng ở cuối mục).

```
mất sóng ──0,5 s──► GIẢM VỖ DẦN 10°/s ──► LƯỢN: 2 cánh đứng yên ở góc lượn + trim ──50 s──► SERVO NGHỈ
          (giữ lệnh cũ)   (±20° → 0 mất 2 s)                                                (chỉ khi vẫn mất sóng)
```

| Giai đoạn | Bướm làm gì | Lý do |
|---|---|---|
| 0–0,5 s sau gói cuối | Giữ nguyên lệnh cuối | Mất sóng ngắn (vài gói) không làm gián đoạn bay |
| **Giảm vỗ** | Biên độ hai cánh giảm đều nhau, 10°/s, tần số 2,5 Hz; không lái | Lực đẩy giảm từ từ, mũi không bị chúc đột ngột |
| **Lượn** | Cánh đứng yên ở góc lượn + trim cuối cùng nhận được | Mô phỏng: lượn ổn định (α 9–11°, không thất tốc, không nghiêng), chìm khoảng 0,1–0,3 m/s |
| **Servo nghỉ** | `landTime` + 30 s sau khi bắt đầu hạ, nếu vẫn mất sóng: tắt xung servo | Nếu cánh bị kẹt sau khi chạm đất, servo không bị cháy |
| Có sóng lại | Gói không có cờ hạ cánh: trả quyền lái ngay | |

**Chỉ hạ cánh khi bướm đang vỗ.** Nếu lúc mất sóng bướm đang TẮT VỖ (ví dụ đang nằm dưới đất), Nano giữ nguyên cánh và không bao giờ tự vỗ.

Chế độ hạ cánh được kích hoạt bởi:

| Tình huống | Ai xử lý |
|---|---|
| Bướm không nhận được gói nào trong 0,5 s (mất sóng NRF24) | Nano tự chạy |
| Điện thoại im lặng quá 0,5 s (rớt Wi‑Fi, tắt màn hình) | Trạm phát gửi cờ HẠ CÁNH |
| Trang mất kết nối tới trạm quá 1 s, hoặc bạn chuyển sang app khác | Trang tự bật HẠ CÁNH. Khi quay lại, nút hiện **HỦY HẠ CÁNH**: bấm để lấy lại quyền lái |
| Bạn bấm **HẠ CÁNH** | Chạy cùng kịch bản trên. Dùng để thử chế độ này khi vẫn còn sóng |
| Pin dưới 6,3V lúc đang hạ cánh | Bỏ qua giai đoạn vỗ nhẹ (nếu có), lượn luôn |
| Pin dưới 6,6V (3,3V/cell) lúc bay bình thường | Ô pin chuyển đỏ. Chỉ báo, không tự giảm ga |

**Tùy chọn vỗ nhẹ khi hạ** (⚙ → *Tự hạ cánh*): thay vì lượn ngay, giữ hai cánh vỗ ±`landAmp` trong `landTime` giây rồi mới lượn. Mặc định **0° = lượn ngay**. Nano chặn `landAmp` ≤ 8°, vì theo mô phỏng ±10° đã giữ được độ cao, nên vỗ nhẹ hơn chỉ giảm tốc độ chìm một chút (±6°: khoảng 0,06 m/s thay vì 0,11 m/s), đổi lại bướm bay xa hơn gấp đôi trước khi chạm đất. Điện thoại gửi `landAmp` và `landTime` trong mọi gói lệnh, nên lúc mất sóng Nano dùng giá trị mới nhất.

**Không có lượn vòng khi hạ cánh.** Mô phỏng cho thấy chỉ cần hai cánh lệch biên độ 1° là bướm nghiêng tới 32° sau 2,4 s (xoắn ốc), còn lệch 2° thì mất ổn định sau 0,9 s. Không có cảm biến góc nghiêng để giữ cân bằng, nên lúc tự hạ hai cánh luôn vỗ đều nhau. Cũng vì vậy, độ lái mặc định của bạn (⚙ → *Lệch biên độ khi lái tối đa*) được hạ từ 10° xuống **3°**.

**Thử trước khi tin.** Bay ở độ cao an toàn, bấm HẠ CÁNH, quan sát rồi bấm HỦY HẠ CÁNH để lấy lại quyền lái. Trim hai cánh phải chuẩn: khi lượn mà lệch trim thì bướm sẽ lượn vòng xoắn ốc giống như trường hợp lệch biên độ ở trên.

### Số liệu mô phỏng

Ptera UVLM + MuJoCo, bay tự do 6 bậc tự do, CG 22,5mm, khởi đầu 4,0 m/s, α 9°, 2,5 Hz. Thân bị giữ cố định 0,8 s, sau đó thả tự do 2,4 s. File: `analysis/results/freeflight/cg23_*.csv`; xem 3D bằng `analysis/view_freeflight.py`.

| Biên độ (phải / trái) | Tốc độ leo, nửa sau (m/s) | Pitch (°) | α (°) | Roll lớn nhất (°) |
|---|---|---|---|---|
| 0° (lượn) | −0,11 | 2,6 … 10,9 | 9,0 … 11,0 | 0 |
| ±10° | +0,04 | 1,3 … 13,7 | 6,1 … 14,0 | 0 |
| ±12,5° | +0,12 | 0,6 … 15,1 | 5,4 … 14,8 | 0 |
| ±15° | +0,22 | −0,1 … 16,7 | 4,8 … 15,8 | 0 |
| ±20° | +0,49 | −1,9 … 20,8 | 3,7 … 17,6 | 0 |
| 11,5° / 13,5° (lệch 1°) | −0,07 | 0,0 … 13,4 | 4,3 … 14,9 | **31,9**, vẫn đang tăng |
| 10,5° / 14,5° (lệch 2°) | mất ổn định sau 0,9 s | −6,7 … 9,8 | 5,9 … 14,9 | **19,7** rồi phân kỳ |

Các điểm đối xứng khớp với công thức leo ≈ 0,0015·A² − 0,11 m/s (A tính bằng độ), nên mức bay ngang là khoảng ±8,6°. Mức này thấp hơn ước lượng ±15° trong `HUONG_DAN_THI_CONG.md`, vì cánh v3.1 khỏe hơn cánh cũ.

Giới hạn của mô phỏng: UVLM không nhớt (không có lực cản ma sát của màng, không thất tốc), nên ngoài thực tế bướm chìm nhanh hơn và leo chậm hơn. Thời gian bay tự do chỉ 2,4 s, vẫn còn dao động dọc ban đầu (sụt 0,6–0,7 m ngay sau khi thả ở mọi biên độ). Không có gió, không có sai số chế tạo. Các con số dùng để so sánh tương đối giữa các biên độ, không phải giá trị tuyệt đối.

**Muốn hạ cánh có điều khiển thật** (giữ cánh thăng bằng, lượn vòng tại chỗ, giảm tốc trước khi chạm đất) thì cần thêm cảm biến: IMU MPU6050 (~2g, I2C ở A4/A5) để giữ góc nghiêng bằng lệch biên độ, và có thể thêm áp kế BMP280 (~1g) để biết độ cao. Khối lượng tăng thì phải cập nhật `butterfly_params.json`, dựng lại trong Fusion và cân lại trọng tâm.

Giới hạn cứng trong firmware bướm (`butterfly_rx.ino`, phần *configuration*): góc cánh không quá ±45° (Fusion kiểm tra không va chạm tới ±45°), biên độ ≤ 35°, tần số 0,5–4 Hz, và **biên độ × tần số ≤ 110 °·Hz** (tốc độ đỉnh khoảng 690°/s, mức servo PTK 7465Plus theo kịp khi mang cánh). Ví dụ ở 3,5 Hz biên độ bị chặn còn 31°. Biên độ thay đổi tối đa 80°/s, góc lượn/trim 60°/s, nên cánh không giật khi kéo ga hay đổi trim.

## 5. Thử trên bàn (tháo cánh, chỉ lắp tay servo)

1. Nạp `butterfly_rx`. Khi cấp nguồn, cả hai servo về **1500µs**: lắp tay servo nằm ngang (bước 7 trong hướng dẫn thi công). Nếu lệch cả một răng then thì sửa `CENTER_US_R` / `CENTER_US_L`.
2. **Kiểm tra chiều servo:** trong ⚙ đặt góc lượn +10°. Cả hai tay servo phải **nâng lên**. Bên nào hạ xuống thì đổi dấu `DIR_R` hoặc `DIR_L` (mặc định `+1` / `−1`, vì hai servo đặt cạnh nhau, tay quay ra hai phía ngược nhau). Đặt lại góc lượn 0.
3. Chỉnh trim phải/trái để hai tay nằm đúng ngang.
4. Bật vỗ, kéo ga lên từ từ. Lái phải: tay trái phải quét rộng hơn.
5. Đang vỗ, tắt trạm phát: sau 0,5 s biên độ giảm dần (10°/s) tới khi tay servo đứng yên ở vị trí ngang; khoảng 50 s sau servo thả lỏng (xoay tay servo bằng tay được). Bật lại trạm phát: servo giữ lại ngay. Nếu đang TẮT VỖ mà tắt trạm phát, servo phải đứng yên.
6. Bấm HẠ CÁNH khi đang vỗ: ô trạng thái giữa màn hình hiện *Tự hạ cánh: lượn … s* (hoặc *vỗ nhẹ* trước, nếu đặt `landAmp` > 0). Bấm HỦY HẠ CÁNH để lấy lại ga.
7. Muốn xem log trên Nano: đặt `DEBUG_SERIAL 1`, mở Serial Monitor 115200. Log in chế độ (pilot / DESCEND / GLIDE / RELAXED), tần số, biên độ, góc lượn, điện áp, số gói nhận.
8. Kiểm tra logic hạ cánh trên máy tính, không cần board: `firmware/test/host_test.cpp` chạy đúng code của `butterfly_rx.ino` với thời gian giả lập (19 trường hợp: mất sóng, có sóng lại, đang tắt vỗ, pin yếu, thông số vượt giới hạn…).

## 6. Thông số kỹ thuật

- Servo: Timer1 Fast PWM mode 14, chia 8, khung 3 ms (333 Hz), D9 = OC1A (phải), D10 = OC1B (trái). Không dùng `Servo.h`. Mỗi khung tính lại góc theo `off + amp·sin(φ)`, φ tích phân theo tần số nên đổi tần số không làm cánh nhảy.
- Radio: kênh 80 (2480 MHz), 250 kbps, CRC 16, địa chỉ `BFLY1`, auto‑ack + ack payload; trạm phát gửi 50 Hz, thử lại 3 lần cách 1,5 ms. Wi‑Fi AP cố định kênh 1 (2401–2423 MHz), cách NRF24 gần 60 MHz.
- Giao thức `BFLY_PROTO 2`. Gói lệnh (15 byte): cờ (vỗ, hạ cánh), tần số (0,1 Hz), biên độ phải/trái, tâm hành trình phải/trái (0,1°, + là cánh lên), thông số hạ cánh (biên độ vỗ nhẹ, thời gian). Trộn ga + lái làm trên điện thoại.
- Gói telemetry (10 byte, trả về trong ack): điện áp pin (mV), cờ đang vỗ / pin yếu, số lần mất sóng, số gói nhận, chế độ (lái / vỗ nhẹ / lượn / servo nghỉ) và số giây từ lúc bắt đầu hạ cánh.
- Kích thước bản dựng: Nano 7,0 KB flash / 131 B RAM; ESP32 khoảng 960 KB.
- Điện áp pin đọc ở A0 qua cầu chia 20k/10k, tham chiếu là 5V của Nano. Nếu số hiện trên điện thoại lệch so với đồng hồ đo, chỉnh `VBAT_SCALE`. Không hàn cầu chia thì đặt `VBAT_FITTED = false`.
