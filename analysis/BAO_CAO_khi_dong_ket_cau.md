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
| Khối lượng (Fusion) | **60,4g**; tải cánh 3,7 g/dm² |
| Trọng tâm | **20,0mm** sau mép trước gốc cánh, 6,9mm dưới gốc cánh |
| Servo | 2 × PTK 7465Plus quay ngược, thân servo làm "ngực" phía trước gốc cánh |
| Thân | Xương sống ống carbon vuông 2mm × 250mm. Khay "bụng" ESP32‑C3 + buck; pin 2S 180mAh buộc dưới khay (tâm x = −66,9mm) |
| **Cánh** | **Một tấm màng liền mỗi bên.** Mép trước thẳng theo ống carbon 2,0 × 1,0mm; mép gốc thẳng theo que 1,0mm |
| **Đường gấp** | Que 1,0mm từ gốc R tới đỉnh chỗ khuyết N. Tấm sau gập xuống **7,26°**, cho góc cúi **−5°** và rủ thêm 5,3°. Hướng lỗ trong khớp nối tay servo tạo sẵn góc này |
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
- Dùng thư viện `ESP32Servo`, `setPeriodHertz(333)`, và hẹn giờ `micros()` thay cho `delayMicroseconds()`.

## 7. Phần mềm

| Phần mềm | Vai trò |
|---|---|
| **Ptera Software** (UVLM + MuJoCo) | Lực khí động không dừng, ổn định, bay tự do 6 bậc tự do |
| `butterfly_aero.py` | Quét nhanh tần số, biên độ, que, giới hạn servo |
| Fusion 360 | CAD, khớp `Flap_R` / `Flap_L`, kiểm tra va chạm (không va chạm ở ±45°), xuất STL |
| Nếu cần sâu hơn | OpenFOAM / Fluent (CFD có thất tốc); preCICE + CalculiX (tương tác khí – màng) |
