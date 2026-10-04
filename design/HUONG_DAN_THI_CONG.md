# Hướng dẫn thi công bướm RC 2 servo (cánh một tấm gấp)

Tất cả kích thước trong hướng dẫn này được sinh ra từ `butterfly_params.json` và `wing_geometry.py`, cùng nguồn với mô hình Fusion và mô phỏng. Nếu sửa thiết kế, chạy lại `fusion_build.py` (trong Fusion) và `make_drawings.py` để cập nhật bản vẽ.

## 1. File cần dùng

| File | Dùng để |
|---|---|
| `drawings/wing_template_A2.pdf` | Mẫu cánh 1:1 (trang 1: cánh phải, trang 2: cánh trái). In khổ A2, **100% / Actual size** |
| `drawings/wing_template_A4_tiles.pdf` | Mẫu như trên, chia trang A4 (4 trang mỗi cánh), ghép chồng 10mm theo nét chấm |
| `drawings/rod_cut_list.md` | Bảng cắt que carbon |
| `stl/*.stl` | Chi tiết in 3D |

**In xong phải đo thước 100mm và ô 50 × 50mm trên giấy.** Sai quá 0,5mm thì chỉnh tỉ lệ in rồi in lại.

## 2. Vật tư

| Vật tư | Số lượng |
|---|---|
| Servo PTK 7465Plus | 2 |
| ESP32‑C3 Super Mini, mạch buck 5V (khoảng 17 × 11mm), pin LiPo 2S 180mAh | 1 mỗi loại |
| Ống carbon 2,0 × 1,0mm | 2 × 318,9mm |
| Que carbon đặc 1,0mm | Đường gấp 2 × 214,9mm; que gốc 2 × 245,6mm; gân A 2 × 227,2mm |
| Que carbon đặc 0,8mm | Gân B 2 × 170,5mm; gân C 2 × 218,8mm |
| Ống carbon vuông 2mm | 1 × 250mm (xương sống) |
| Màng: mylar 12µm (chăn cứu sinh) hoặc vải dù diều P31N | Khoảng 2 tấm 40 × 45cm |
| Vít M2 × 6 | 2 (bắt khớp nối vào tay servo) |
| Keo 502 (CA), keo xịt 3M Super 77 (mylar) hoặc B7000 (vải), dây rút nhỏ, dây silicone 30AWG, jack JST 1,25 | — |

## 3. In 3D

| Chi tiết | Số lượng | Vật liệu / thông số |
|---|---|---|
| `PRINT_HornAdapter_R`, `_L` (khớp nối tay servo) | 1 mỗi bên | PETG hoặc PA12, **100% infill**, lớp 0,12mm. Đây là chi tiết chịu lực chính |
| `PRINT_ConnA/B/C_R`, `_L` (khớp gân) | 6 | PETG, 100% infill, lớp 0,12mm |
| `Frame_ServoMount` | 1 | PLA+ hoặc PETG, 4 vách |
| `Tray_Abdomen` | 1 | PLA+, 3 vách |

- Lỗ in thường bị nhỏ đi 0,1–0,2mm. Doa lại bằng mũi khoan tay 2,0 / 1,0 / 0,8mm đến khi que trượt vào vừa khít.
- Khớp nối tay servo có 3 lỗ que: cạnh trước (ống 2,0mm), đường gấp (1,0mm), que gốc (1,0mm). **Hướng các lỗ đã được thiết kế sẵn để tạo góc nhị diện 11° và góc gấp 7,3°** cho tấm sau. Đừng khoan lệch hướng.

## 4. Cắt que

- Cắt bằng đĩa cắt Dremel hoặc mài trên giấy nhám; không dùng kéo vì que carbon sẽ bị tưa sợi.
- Chiều dài cắt trong bảng đã trừ phần que cắm vào lỗ khớp: lỗ ở khớp nối tay servo bắt đầu cách điểm R 3mm; lỗ ở khớp gân bắt đầu cách mặt que gốc 1mm.

## 5. Cắt màng

1. Đặt mẫu in lên mặt phẳng, phủ màng lên trên, dán băng keo giữ 4 góc.
2. Cắt theo **nét liền** (đường bao), cắt luôn **mép bọc 6mm (nét đứt)** dọc que cạnh trước và que gốc.
3. Đánh dấu lên màng bằng bút lông dầu: đường gấp (nét đỏ), vị trí 3 khớp gân, và điểm R.
4. Cánh trái dùng trang 2, là ảnh gương của trang 1.

## 6. Ráp khung cánh (làm ngay trên mẫu in)

1. Cắm ống cạnh trước, que đường gấp và que gốc vào khớp nối tay servo. Chưa nhỏ keo.
2. Luồn khớp A và B vào ống cạnh trước, cách R 100mm và 220mm. Luồn khớp C vào que đường gấp, cách R 110mm.
3. Cắm gân A, B, C vào khớp.
4. Đặt khung lên mẫu sao cho mọi que trùng nét vẽ. Tấm sau nằm thấp hơn mặt phẳng tấm trước (xem bước 7). Kiểm tra xong mới nhỏ keo 502 vào từng mối.

## 7. Dán màng và gấp tấm sau

1. Xịt keo lên khung tấm trước (ống cạnh trước, gân A, B, que đường gấp) rồi đặt màng lên, vuốt từ gốc ra đầu cánh. **Để màng hơi chùng**, đừng căng như mặt trống.
2. Gập mép bọc 6mm quanh ống cạnh trước và dán.
3. Dán phần màng sau đường gấp lên que gốc và gân C, rồi gập mép bọc quanh que gốc.
4. Góc gấp được tạo sẵn bởi hướng lỗ trong khớp nối. Kiểm tra bằng cách đặt tấm trước phẳng trên bàn (úp cánh xuống, mặt dưới lên trên), rồi đo độ cao các điểm của tấm sau so với mặt bàn:

| Điểm | Cách đường gấp | Độ lệch so với mặt tấm trước |
|---|---|---|
| E, cuối que gốc | 138mm | **17,5mm** |
| Đỉnh thùy sau | 80mm | 10,1mm |
| Giữa mép gốc | 68mm | 8,6mm |
| Đầu gân C | 41mm | 5,2mm |

   Sai lệch nhỏ hơn ±2mm là đạt.
5. **Không** dán que dọc mép sau cánh. Mép sau phải tự do để màng tự xoắn khi vỗ; đây là điều kiện để có lực đẩy.

## 8. Ráp thân

1. Lắp 2 servo quay lưng vào nhau vào khung servo, **trục ra hướng về phía sau** (về phía đuôi).
2. Luồn xương sống 250mm qua ống kẹp của khung (thò ra trước 35mm), rồi luồn khay bụng.
3. Đặt ESP32‑C3 và mạch buck vào ô trên khay. Buộc pin dưới khay bằng 2 dây rút qua 2 rãnh. Tâm pin ở x = −66,9mm, tức là cách mặt phẳng khớp nối tay servo 67mm về phía sau.
4. Cho servo về vị trí giữa (1500 µs), lắp tay servo nằm ngang hướng ra ngoài, gắn khớp nối cánh vào tay servo và bắt vít M2.
5. Đi dây:
   - pin → mạch buck 5V → chân 5V của ESP32;
   - pin (8,4V) → dây đỏ của 2 servo;
   - mọi dây GND nối chung.
   Thêm tụ 100–220µF ở chỗ cấp nguồn servo.

## 9. Cân trọng tâm và bay thử

1. Trọng tâm phải nằm **20mm sau mép trước gốc cánh**, tức là 20mm sau mặt phẳng tâm 2 khớp nối tay servo. Đỡ bướm bằng 2 ngón tay tại đó: thân phải nằm ngang. Trượt pin 10mm thì trọng tâm dịch khoảng 1,8mm.
2. Ném lượn nhẹ, servo tắt. Theo mô phỏng, máy lượn ở khoảng 4 m/s với α khoảng 11°.
3. Bật vỗ ±20° ở 2,5 Hz (`fd` ≈ 222 µs, `ys` ≈ 11 100 µs). Mô phỏng cho thấy ±15° gần như bay ngang (leo 0,1 m/s) và ±30° leo 1,3 m/s, nên dùng biên độ như cần ga. Rẽ bằng lệch biên độ hai cánh.
4. Sau mỗi lần bay 2 phút, sờ thử nhiệt độ servo.
