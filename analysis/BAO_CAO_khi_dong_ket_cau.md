# Bướm RC 2 servo — thiết kế v3 (cánh một tấm gấp)

Báo cáo khí động, kết cấu, ổn định và bay tự do.

Bìa hồ sơ: `design/drawings/butterfly_cover.pdf`. Bản vẽ thi công: `design/drawings/`. Hướng dẫn: `design/HUONG_DAN_THI_CONG.md`.

## 0. Một nguồn duy nhất cho bản vẽ và mô phỏng

```
design/butterfly_params.json  +  design/wing_geometry.py      (kích thước + hình học cánh dùng chung)
        |                                   |                               |
design/fusion_build.py (Fusion)   design/make_drawings.py         analysis/design_link.py
   dựng CAD, khớp, xuất STL          mẫu cắt 1:1, bảng cắt que         butterfly_aero.py · ptera_model.py
        |                                                              ptera_stability.py · ptera_freeflight.py
        v
design/fusion_mass_properties.json  (khối lượng, trọng tâm, quán tính tính từ mô hình Fusion)  -->  mô phỏng
```

Quy trình khi sửa thiết kế:
1. Sửa `butterfly_params.json`.
2. Chạy `fusion_build.py` trong Fusion.
3. Chạy `make_drawings.py` và `make_cover.py`.
4. Chạy các script trong `analysis/`.

Không còn kích thước viết tay ở bất kỳ đâu.

## 1. Thiết kế v3

| Hạng mục | Giá trị |
|---|---|
| Sải cánh / diện tích / AR | 805mm (ở góc nhị diện nghỉ) / 16,23 dm² / 4,1 |
| Khối lượng (Fusion) | **64,2g** (hub gốc cánh liền khối, PETG); tải cánh 4,0 g/dm² |
| Trọng tâm | **20,0mm** sau mép trước gốc cánh, 6,9mm dưới gốc cánh |
| Servo | 2 × PTK 7465Plus quay ngược, thân servo làm "ngực" phía trước gốc cánh |
| Thân | Xương sống ống carbon vuông 2mm × 250mm. Khay "bụng" ESP32‑C3 + buck; pin 2S 180mAh buộc dưới khay (tâm x = −75,2mm) |
| **Cánh** | **Một tấm màng liền mỗi bên.** Mép trước thẳng theo ống carbon 2,0 × 1,0mm; mép gốc thẳng theo que 1,0mm |
| **Đường gấp** | Que 1,0mm từ gốc R tới đỉnh chỗ khuyết N. Tấm sau gập xuống **7,26°**, cho góc cúi **−5°** và rủ thêm 5,3°. Hướng lỗ trong hub gốc cánh tạo sẵn góc này |
| Gân | A Ø1,0 và B Ø0,8 trên ống cạnh trước; C Ø0,8 trên que đường gấp (đỡ thùy sau) |
| Diện tích màng mỗi bên | Tấm trước 513 cm², tấm sau 299 cm² |

Vì sao làm một tấm: cắt và dán một lần, không có mép nối dễ bong, tấm liền truyền lực giữa phần trước và phần sau. Đường gấp thẳng nên tấm màng trải phẳng hoàn toàn, cắt đúng theo mẫu in.

## 2. Lực khí động (chuẩn tĩnh, `butterfly_aero.py`)

- Cánh phải **tự xoắn được** (η khoảng 0,5–0,8). Cánh cứng bị thất tốc và không có lực đẩy.
- Ở 2,5 Hz: ±25° thì servo dư 47%, công suất cơ khoảng 0,8 W; ±30° dư 15%. Từ khoảng 3 Hz trở lên, servo không theo kịp.

## 3. Kết cấu

| Que cạnh trước (60% tải tấm trước) | Võng đầu cánh | Ứng suất |
|---|---|---|
| 1,5mm đặc | 25% | 250 MPa ✗ |
| **Ống 2,0 × 1,0mm (chọn)** | **8,5%** | **114 MPa** |
| Ống 2,5 × 1,5mm | 3,8% | 64 MPa |

Thông số: E = 120 GPa, ứng suất cho phép khi mỏi 400 MPa. Các que đường gấp, mép gốc và gân C cùng đỡ tấm sau.

## 4. Ổn định dọc (`ptera_stability.py`)

| | v2 (hai tấm) | **v3 (một tấm gấp)** |
|---|---|---|
| Điểm trung hòa | 34,6mm | **37,4mm** |
| Dự trữ ổn định | 14,3mm | **17,4mm** |
| Lượn khi tắt servo | α ≈ 15° (sát thất tốc) | **α ≈ 11°, 4,0 m/s** |
| Khi vỗ cánh (tại α cân bằng) | — | Lực nâng 1,24 lần trọng lượng, lực đẩy +0,08 N |

## 5. Bay tự do 6 bậc tự do (`ptera_freeflight.py`, biểu đồ `results/freeflight_v3.png`)

Tần số 2,5 Hz, trọng tâm 20mm; giá trị trung bình 0,4 giây cuối:

| Biên độ | Góc thân TB (°) | α TB (°) | Tốc độ TB (m/s) | Tốc độ leo (m/s) |
|---|---|---|---|---|
| ±15° | 10.8 | 9.4 | 4.16 | +0.10 |
| ±20° | 15.5 | 9.3 | 4.16 | +0.45 |
| ±25° | 21.0 | 8.9 | 4.21 | +0.89 |
| ±30° | 25.9 | 8.2 | 4.39 | +1.33 |

**Khuyến nghị:** bay thử bắt đầu ở **±20°** (còn dư leo 0,45 m/s để bù sai lệch của mô hình). Bay ngang ở khoảng **±15–20°**, leo ở ±25–30°.

Tất cả các chế độ đều **ổn định, không lật**. Biên độ là "cần ga" điều khiển leo/hạ: tốc độ leo giảm khoảng 0,09 m/s cho mỗi độ biên độ.

Giới hạn của mô phỏng:
- UVLM không mô hình được thất tốc.
- Mức tự xoắn của màng là giá trị áp đặt (η = 0,6).
- Chưa tính quán tính của cánh tác động lên thân.
- Chỉ mô phỏng 2,4 giây; hướng ngang chưa được kích thích.

## 6. Thông số code

- ±15° → `fd` ≈ 167 µs; ±20° → 222 µs; ±25° → 278 µs; ±30° → 333 µs (servo 500–2500 µs ứng với 180°).
- 2,5 Hz → `ys` ≈ 11 100 µs (36 bước mỗi chu kỳ).
- Arduino Nano: **không dùng thư viện `Servo.h`** (nó chiếm Timer1 và chỉ chạy 50 Hz). Tự cấu hình Timer1: Fast PWM mode 14, chia 8, `ICR1 = 5999` → 333 Hz; servo phải ở D9 (`OCR1A`), trái ở D10 (`OCR1B`); độ rộng xung: `OCR1x = 2 * pulse_us - 1`. Cập nhật `OCR1x` theo hẹn giờ `micros()`, không dùng `delayMicroseconds()`.
- Thu phát: thư viện `RF24` (TMRh20), CE = D7, CSN = D8, tốc độ 250 kbps để tầm xa nhất. Gói tin gồm biên độ trái, biên độ phải, tần số.
- **Mất sóng** quá 0,5 s: dừng vỗ, giữ cánh ở góc lượn (vị trí giữa), để bướm tự lượn xuống.

## 7. Phần mềm

| Phần mềm | Vai trò |
|---|---|
| **Ptera Software** (UVLM + MuJoCo) | Lực khí động không dừng, ổn định, bay tự do 6 bậc tự do |
| `butterfly_aero.py` | Quét nhanh tần số, biên độ, que, giới hạn servo |
| Fusion 360 | CAD, khớp `Flap_R` / `Flap_L`, kiểm tra va chạm (không va chạm ở ±45°), xuất STL |
| Nếu cần sâu hơn | OpenFOAM / Fluent (CFD có thất tốc); preCICE + CalculiX (tương tác khí – màng) |

## 8. Chi tiết in 3D: liền khối và đủ bền (`printed_parts_check.py`)

Bản trước dùng khớp nối tay servo nhỏ (khối 4,5 × 10 × 8mm), 3 ống cắm mảnh thành 0,9mm và chỉ 1 vít. Ứng suất ở gốc ống cắm khoảng 22–27 MPa, ngang với độ bền bám lớp của PETG, nên sẽ nứt khi chịu vỗ cánh liên tục.

Bản mới là **hub gốc cánh** (`PRINT_WingHub_R/L`), **1 khối liền** (Fusion xác nhận 1 khối), nặng 1,72g mỗi bên, gồm:
- khối kẹp tay servo, thành 2mm, 2 bulông M2 xuyên qua;
- lõi cầu ở gốc;
- 3 ống cắm côn: que cạnh trước Ø7,2 → Ø4,6mm, que gấp và que gốc Ø4,6 → Ø3,2mm;
- gân nối giữa các ống.

Khớp gân có ống luồn thành 1,0mm, ống cắm thành 1,2mm, chỗ nối chữ T được bo tròn. Khung servo có thành 1,6mm, ống kẹp xương sống thành khoảng 1,5mm.

| Mặt cắt (tải xấu nhất) | Ứng suất | Hệ số an toàn mỏi |
|---|---|---|
| Ống cắm que cạnh trước, gốc / giữa | 3,8 / 3,5 MPa | 2,1 / 2,3 |
| Ống cắm que gấp / que gốc, gốc / giữa | 5,0 / 4,1 MPa | 1,6 / 1,9 |
| Ống cắm của khớp gân | 4,1 MPa | 1,9 |
| Bulông M2 kẹp tay servo | 8,3 N mỗi bulông, ép mặt 1,9 MPa | rất dư |

Mọi chi tiết in đều là 1 khối liền. Không va chạm ở 0° / ±36° / ±45°. Tổng khối lượng tăng lên 63,8g; pin dời về x = −73,5mm để giữ trọng tâm ở 20,0mm.

Kiểm tra lại sau khi đổi sang hub mới (63,8g; file `results/freeflight/m63_*.csv`):
- Dự trữ ổn định vẫn 17,4mm.
- Bay tự do ở ±20° vẫn ổn định: góc thân 14,6°, α 9,3°, tốc độ 4,3 m/s, leo 0,39 m/s (bản 60,4g leo 0,45 m/s).
- Khuyến nghị bay thử không đổi: bắt đầu ở ±20°.

### Sửa va chạm tai servo – khung (sau khi rà soát)

- Tai bắt vít servo nhô dưới đáy servo 4,5mm (tới z = −4,3mm) và trước đó đâm xuyên ống kẹp xương sống (z −5,4 đến −1,4mm). Lỗi lọt qua vì trước đây chỉ kiểm tra va chạm cánh với thân.
- Đã sửa: xương sống hạ xuống z = −7,7mm (khe hở 0,8mm dưới tai servo). Khung servo nối xuống ống kẹp bằng vách đứng chỉ nằm dưới đai ôm servo. Khay bụng và pin hạ theo.
- `fusion_build.py` nay **tự kiểm tra va chạm giữa mọi chi tiết thân** (servo, khung, khay, xương sống, pin, hub, que) và ghi vào `fusion_mass_properties.json` → `static_clashes`. Kết quả hiện tại: rỗng.
- Kết quả sau sửa: khối lượng 64,2g, trọng tâm 20,0mm (pin x = −75,2mm), dự trữ ổn định 17,5mm, không va chạm ở ±45°.

## 9. v3.1 — cánh dáng bướm thật (Monarch)

Chỉ đổi hình dạng cánh. Thân, servo, pin và cơ cấu gấp giữ nguyên. Mọi thay đổi nằm trong `butterfly_params.json` → `wing`.

**Hình dạng mới**
- **Cánh trước** dạng tam giác như cánh bướm Monarch: mép trước chạy theo ống carbon, đỉnh cánh tròn ở sải 389mm, mép ngoài gần thẳng chạy về góc sau (điểm khuyết N, dời từ (−158, 150) ra (−184, 212)).
- **Cánh sau** hình quạt tròn, lùi tới x = −309mm, mép có 6 múi lượn sóng (khía chữ V giữa các múi). Mép trong chạy gần song song với bụng.
- **Gân** toả ra từ gốc như gân bướm thật: A, B trên ống cạnh trước (t = 70 / 170mm), **thêm gân D**, C và D trên que gấp (t = 70 / 170mm). Đầu gân sau dừng giữa một múi, cách mép 7mm. Gân D đỡ phần cánh sau mới mở rộng.
- `wing_geometry.py`: danh sách que tấm sau (`HIND_RODS`) nay tính từ các gân gắn trên que gấp, không viết tay. `ptera_model.py`: vị trí các mặt cắt theo sải tính từ đường bao, không còn số cứng.

| Hạng mục | v3 | **v3.1** |
|---|---|---|
| Sải cánh | 805mm | **814mm** |
| Diện tích màng mỗi bên (trước + sau) | 513 + 299 cm² | **470 + 374 cm²** |
| Tổng diện tích | 16,23 dm² | **16,89 dm²** (+4%) |
| Khối lượng (Fusion) | 64,2g | **65,4g** |
| Trọng tâm sau mép trước gốc cánh (pin giữ x = −75,2mm) | 20,0mm | **22,4mm** |
| Điểm trung hòa (UVLM) | 37,5mm | **41,4mm** |
| Dự trữ ổn định | 17,5mm | **19,0mm** |
| α cân bằng / tốc độ lượn | 10,9° / 4,14 m/s | **10,2° / 4,21 m/s** |
| Vỗ ±20° 2,5 Hz tại điểm cân bằng: lực nâng/trọng lượng, lực đẩy | 1,19 · 0,034 N | **1,10 · 0,042 N** |
| Góc gấp tấm sau (cánh sau vẫn cúi 5°) | 7,26° | **6,62°** |
| Mômen quán tính vỗ của màng (∫r²dA, so sánh) | 1,00 | **0,98** |

Cánh trước bớt diện tích ở đầu cánh, cánh sau thêm diện tích ở gần gốc, nên quán tính vỗ gần như không đổi. So ở cùng điểm bay, mômen servo tăng 4–10% (ví dụ 2 Hz ±30°: 0,170 → 0,182 N·m) và dự trữ servo gần như giữ nguyên (1,55 → 1,51).

Trọng tâm lùi 2,4mm do cánh sau to hơn và có thêm gân D. Điểm trung hòa lùi 3,9mm, nhiều hơn trọng tâm, nên **giữ pin ở chỗ cũ**: dự trữ ổn định 19mm, gần mức của v3.

**Bay tự do 6 bậc tự do** (±20°, 2,5 Hz; `results/freeflight/v31_cg22_f2.5_a20_U4.0.csv`, `results/ffV31_20.txt`):
- Ổn định, không lăn, không xoay.
- α giữ trong khoảng 7,8–9,7° suốt 3,2s.
- Tốc độ và góc thân dao động chậm kiểu phugoid (V 4,0 → 5,3 → 4,7 m/s, chu kỳ khoảng 3s). Dao động này chưa tắt hẳn trong 3,2s mô phỏng.
- 0,4s cuối: góc thân 16,7°, α 8,5°, tốc độ 4,66 m/s, leo 0,66 m/s. Bản v3: leo 0,39 m/s.

**Chi tiết in**
- Que gấp dài hơn (218 → 281mm) và gánh cánh sau lớn hơn. Ở điểm tải xấu nhất mà `butterfly_aero.py` chọn (2,5 Hz ±30°), hệ số an toàn ống cắm que gấp/que gốc chỉ còn 1,2.
- Đã tăng chân ống cắm từ Ø4,6 lên **Ø5,2mm** (ngọn vẫn Ø3,2mm). Hệ số an toàn nay 1,8 ở gốc và 1,9 ở giữa. Hub nặng 1,38 cm³ mỗi cái.
- Các chi tiết khác giữ hệ số an toàn ≥ 1,5.
- Mọi chi tiết in đều là 1 khối liền. Không va chạm ở 0° / ±36° / ±45°. STL đã xuất lại, gồm cả `PRINT_ConnD_R/L` mới.

## 10. Thân ống carbon tròn + Arduino Nano V3 + NRF24L01

Thân mới thay cho ESP32‑C3 (có sẵn WiFi). Arduino Nano không có sóng nên thêm module NRF24L01.

**Kết cấu thân**
- **Xương sống:** ống carbon tròn **3 × 2mm**, thay ống vuông 2mm. Độ cứng uốn gấp 2,4 lần, nặng gần như cũ.
- **Chiều dài ống:** 154mm, tính tự động trong `wing_geometry.body_layout()`. Ống dừng ngay dưới đầu chân hàn của NRF24, để anten mạch in nằm trên phần nhựa, không nằm trên carbon.
- **Khay in 75mm được bỏ.** Thay bằng 2 kẹp PETG luồn trên ống:
  - `PRINT_BattMount` (0,97 cm³): pin treo dưới tấm đỡ. 2 dây rút vòng quanh pin, tấm đỡ và cả ống carbon, nên siết dây là khóa luôn kẹp. Kẹp trượt được dọc ống để chỉnh trọng tâm.
  - `PRINT_AvionicsMount` (1,76 cm³): Nano nằm trên 2 thanh ngang ở 2 đầu mạch, chừa 2,6mm phía dưới cho linh kiện mặt dưới (CH340). 2 vấu trước giữ mép mạch; vấu chỉ đè lên 2,5mm ở 2 đầu mạch, chỗ không có lỗ chân. Cổng USB quay về trước, nạp code không cần tháo mạch. NRF24 nằm trên lưỡi nhựa phía sau, anten quay ra đuôi. Ống luồn kín đầu, chụp lên đuôi ống carbon.
- **Ống kẹp của khung servo** đổi thành ống tròn. Tâm ống carbon ở z = −7,97mm, cách tai servo 0,8mm.

**Kiểm tra trong Fusion**
- Không có va chạm tĩnh giữa các chi tiết (gồm cả mạch Nano và NRF24).
- Khi vỗ ở 0° / ±36° / ±45°, cánh không chạm thân.
- Mọi chi tiết in đều là 1 khối liền.
- File `Tray_Abdomen.stl` đã xóa.

| Hạng mục | v3.1 (ESP32‑C3) | **Nano + NRF24** |
|---|---|---|
| Điện tử | ESP32‑C3 1,6g + buck 1,5g | Nano (đã tháo header) 5,0g + NRF24 2,0g + LDO 3,3V 0,5g |
| Chi tiết in thân | khay 2,8g | 2 kẹp 3,5g |
| Khối lượng | 65,4g | **69,8g** (tải cánh 4,1 g/dm²) |
| Tâm pin | x = −75,2mm | **x = −39,1mm** (ngay sau servo; Nano ở đuôi để cân; xem §11–12) |
| Trọng tâm / điểm trung hòa / dự trữ ổn định | 22,4 / 41,4 / 19,0mm | **22,5 / 41,5 / 19,0mm** |
| α cân bằng / tốc độ lượn | 10,2° / 4,21 m/s | **10,2° / 4,35 m/s** |
| Vỗ ±20° 2,5 Hz: lực nâng/trọng lượng, lực đẩy | 1,10 · 0,042 N | **1,09 · 0,040 N** |

**Bay tự do** (±20°, 2,5 Hz; `results/freeflight/cg22_f2.5_a20_U4.0.csv`, `results/ffNano_20.txt`):
- Ổn định, không lăn, không xoay. α giữ trong khoảng 7,8–9,9°.
- Dao động phugoid lớn hơn một chút so với v3.1: V 4,0 → 5,55 → 4,8 m/s.
- 0,4s cuối: góc thân 17,5°, tốc độ 4,82 m/s, leo 0,75 m/s.

**Điện:** pin 2S vào chân VIN của Nano; servo nhận thẳng 2S. NRF24 lấy 3,3V từ một LDO riêng, cấp từ chân 5V của Nano, kèm tụ 10µF. Không dùng chân 3V3 của Nano clone. Sơ đồ chân ở `design/HUONG_DAN_THI_CONG.md` §8, cấu hình Timer1 333 Hz ở §6.

## 11. Kích thước servo và model 3D thật

**PTK 7465 thường và 7465Plus**
- Không tìm thấy datasheet chính thức của bản Plus. Các trang bán chỉ ghi "7465Plus 7,5kg, bánh răng kim loại, digital", cùng nhóm "9g" với 7465 MG, và có bán kèm bộ kit bướm vỗ cánh.
- Bản thường (7465 MG / 7465W MG) được ghi 23,7 × 12 × 26,6mm; vài nơi ghi 23,9 × 12 × 26,6mm; servodatabase ghi 23,6 × 11,9 × 26,7mm. Khối lượng 12–13g. Mômen 5,5 kg·cm ở 7,4V, 5,8 kg·cm ở 8,4V. Tốc độ 0,07 s/60° ở 8,4V.
- Không nguồn nào cho thấy vỏ bản Plus khác bản thường. Bản Plus được xem là cùng vỏ, chỉ mạnh hơn (7,5 kg·cm).
- **Nên đo lại servo thật bằng thước cặp**: dài, rộng, cao tới đỉnh tháp bánh răng, và khoảng cách từ trục tới đầu thân.

**Đo trên model STEP** (`design/cad/PTK_7465.step`):

| Kích thước | Số cũ trong `butterfly_params.json` | Model STEP | Số mới |
|---|---|---|---|
| Dài thân | 23,7 | 23,8 | 23,8 |
| Rộng thân | 12,0 | 11,7 (11,9 tính cả nhãn) | 12,0 (rãnh khung) |
| Cao: đáy tới đỉnh tháp bánh răng | 26,6 | 26,8 (thân chính 22,0 + tháp 4,8) | 26,8 |
| Trục: cách đầu thân / giữa bề rộng | 6,0 / giữa | 6,2 / giữa | 6,2 |
| Then trục | Ø5, nhô 4,0 | Ø5, nhô 3,5 trên vành | giữ 4,0 (tay servo) |
| Tai bắt vít: cách mặt ra trục / dày / nhô | 6,6 / 2,0 / 4,5 | 8,55 / 2,0 / 4,05 | 8,55 / 2,0 / 4,05 |

Số cũ chỉ lệch 0,1–0,2mm, trừ vị trí tai lệch khoảng 2mm.

**Thay đổi trên mô hình**
- Hai khối hộp servo được thay bằng model STEP thật. `fusion_build.py` nhập file STEP, chép và đặt 2 bản: trục ra hướng về sau, bản trái là bản phải dịch sang (trục nằm giữa bề rộng nên không cần lấy đối xứng gương).
- Trục vỗ hạ 0,1mm (z 17,9 → 17,8). Gốc cánh hạ theo.
- Tai servo nhô ít hơn (4,05mm), nên ống carbon được nâng lên z = −7,52mm, vẫn cách tai 0,8mm.
- Không có va chạm tĩnh. Khi vỗ ở 0° / ±36° / ±45°, cánh không chạm thân.
- Trọng tâm servo lấy theo trọng tâm thể tích của model thật, nằm trước tâm khối hộp cũ 1mm. Vì vậy pin lùi từ x = −33,2 về **−36,0mm** để giữ trọng tâm máy.

**Kết quả**
- Khối lượng 69,7g. Trọng tâm 22,4mm sau mép trước gốc cánh. Điểm trung hòa 41,4mm. Dự trữ ổn định 19,0mm. α cân bằng 10,2°, lượn 4,35 m/s.
- Bay tự do ±20°: ổn định. 0,4s cuối: góc thân 17,5°, α 8,5°, tốc độ 4,82 m/s, leo 0,75 m/s. Giống §10.

## 12. Giữ servo chắc trong khung: bắt vít tai + rãnh ra dây

**Vấn đề của khung cũ**
- Servo chỉ được nhét vào một đai rộng 10mm, khe hở 0,2mm. Không có gì chặn servo theo phương chiều cao (trục x của máy).
- Mômen phản lực trên vỏ servo tới ~0,21 N·m và đổi chiều 5 lần mỗi giây. Servo sẽ gõ trong đai, mòn dần rồi trượt ra.
- Khi hạ cánh mạnh, phần thân (~30g) chỉ được giữ bằng ma sát.
- Model servo thật cho thấy thêm một lỗi: dây servo ra ở mặt đầu phía trục, sát đáy servo, đúng chỗ thành trên của đai đi qua, nên dây bị đè.

**Khung mới** (`PRINT_Frame_ServoMount`, 3,0 cm³, 3,7g; khung cũ 2,8g):
- **Tấm bắt tai dày 3mm** ngay sau tai servo, ở phía đáy servo. Mỗi tai bắt 1 vít M2 × 6 tự ren, cả máy 4 vít. Lỗ dẫn Ø1,6mm. Tâm lỗ được kiểm tra trùng với lỗ tai trong model STEP, ở z = 25,6 và −1,4mm, y = ±6,2mm.
- Đai được kéo dài từ tấm tai tới gần đáy servo để đỡ ngang đáy servo. Thành bên và thành trên có cửa sổ cho nhẹ; 3mm cuối đai giữ nguyên thành vòng kín.
- **Rãnh ra dây** rộng 4,3mm ở thành trên của đai, ngay chỗ dây ra (tâm y = ±6,2mm, cách đáy servo 0–5,7mm).
- Lắp servo từ phía sau: đẩy đáy servo xuyên qua cửa sổ tấm tai, cho tai áp vào tấm rồi bắt vít.

**Kiểm tra**
- Mỗi vít tai chịu cắt 7,8N (27mm giữa 2 vít của một servo). Ép mặt lên tấm PETG 1,3 MPa, giới hạn khoảng 8 MPa.
- Không có va chạm tĩnh. Khi vỗ ở 0° / ±36° / ±45°, cánh không chạm thân.
- Khung vẫn là 1 khối liền.
- Điểm yếu: thành nhựa giữa lỗ vít và cửa sổ chỉ dày 0,6mm (do lỗ tai servo nằm sát thân servo). Vì vậy không vặn vít quá lực; có thể nhỏ keo 502 vào lỗ.

**Cân lại:** khung nặng hơn ở phía trước nên pin lùi về x = −39,1mm.

**Kết quả**
- Khối lượng 70,7g. Trọng tâm 22,5mm. Điểm trung hòa 41,4mm. Dự trữ ổn định 18,9mm. α cân bằng 10,2°, lượn 4,38 m/s.
- Bay tự do ±20° (`results/freeflight/cg23_f2.5_a20_U4.0.csv`): ổn định. 0,4s cuối: góc thân 17,6°, α 8,5°, tốc độ 4,84 m/s, leo 0,76 m/s.

## 13. Tự hạ cánh khi mất sóng: quét biên độ và lệch biên độ

Mục đích: chọn kịch bản cho firmware khi mất sóng (`firmware/README.md`, mục 4). Thiết kế 70,7g, CG 22,5mm, 2,5 Hz, khởi đầu 4,0 m/s, α 9°; thân giữ cố định 0,8 s rồi thả tự do 2,4 s. `ptera_freeflight.py` nhận thêm tham số thứ 6 là biên độ cánh trái, để thử lệch biên độ. Xem 3D: `view_freeflight.py`.

| Biên độ (phải / trái) | Leo, nửa sau (m/s) | Roll lớn nhất (°) |
|---|---|---|
| 0° (lượn) | −0,11 | 0 |
| ±10° | +0,04 | 0 |
| ±12,5° | +0,12 | 0 |
| ±15° | +0,22 | 0 |
| ±20° | +0,49 | 0 |
| 11,5° / 13,5° | −0,07 | 31,9, vẫn tăng |
| 10,5° / 14,5° | mất ổn định sau 0,9 s | 19,7 rồi phân kỳ |

- Các điểm đối xứng khớp với công thức leo ≈ 0,0015·A² − 0,11 m/s, nên bay ngang ở khoảng ±8,6°. Bảng ở mục 5 (±15° → +0,10) là của cánh cũ; cánh v3.1 khỏe hơn.
- Lượn ổn định: pitch 2,6–10,9°, α 9–11°, không nghiêng.
- Lệch biên độ dù chỉ 1° cũng gây xoắn ốc (nghiêng tăng liên tục). Không có cảm biến góc nghiêng thì không thể lượn vòng khi tự hạ.
- **Firmware dùng:** mất sóng 0,5 s → giảm vỗ dần 10°/s → lượn với 2 cánh đều nhau. Vỗ nhẹ khi hạ là tùy chọn, bị chặn ≤ 8°. Độ lái mặc định hạ xuống 3°.
- Giới hạn: UVLM không nhớt (thực tế chìm nhanh hơn, leo chậm hơn); chỉ 2,4 s bay tự do, vẫn còn dao động dọc ban đầu (sụt 0,6–0,7 m ở mọi biên độ).
