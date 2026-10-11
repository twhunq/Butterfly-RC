# Hướng dẫn thi công bướm RC 2 servo (cánh một tấm gấp)

Tất cả kích thước trong hướng dẫn này được sinh ra từ `butterfly_params.json` và `wing_geometry.py`, cùng nguồn với mô hình Fusion và mô phỏng. Nếu sửa thiết kế, chạy lại `fusion_build.py` (trong Fusion) và `make_drawings.py` để cập nhật bản vẽ.

## 1. File cần dùng

| File | Dùng để |
|---|---|
| `drawings/wing_template_A2.pdf` | Mẫu cánh 1:1 (trang 1: cánh phải, trang 2: cánh trái). In khổ A2, **100% / Actual size** |
| `drawings/wing_template_A4_tiles.pdf` | Mẫu như trên, chia trang A4 (4 trang mỗi cánh), ghép chồng 10mm theo nét chấm |
| `drawings/rod_cut_list.md` | Bảng cắt que carbon |
| `stl/*.stl` | Chi tiết in 3D |
| `cad/PTK_7465.step` | Model 3D servo PTK 7465 (dùng cho bản dựng Fusion) |

**In xong phải đo thước 100mm và ô 50 × 50mm trên giấy.** Sai quá 0,5mm thì chỉnh tỉ lệ in rồi in lại.

## 2. Vật tư

| Vật tư | Số lượng |
|---|---|
| Servo PTK 7465Plus | 2 |
| Arduino Nano V3 (ATmega328P, 43,2 × 18,6mm), **tháo hết header**, hàn dây trực tiếp | 1 |
| Module NRF24L01 anten mạch in (29 × 15mm), **tháo header 2×4** | 1 (cộng 1 bộ nữa cho trạm phát) |
| LDO 3,3V (MCP1700‑3302 hoặc HT7333) + tụ 10µF (thêm tụ 0,1µF nếu có) | 1 bộ |
| Trạm phát: board ESP32 hoặc ESP32‑C3 + NRF24 ở trên + tụ 10–100µF (điều khiển bằng điện thoại, xem `firmware/README.md`) | 1 |
| Pin LiPo 2S 180mAh (32 × 20 × 11mm) | 1 |
| Ống carbon 2,0 × 1,0mm | 2 × 316,4mm |
| Que carbon đặc 1,0mm | Đường gấp 2 × 277,7mm; que gốc 2 × 250,2mm; gân A 2 × 255,5mm |
| Que carbon đặc 0,8mm | Gân B 2 × 208,4mm; gân C 2 × 270,0mm; gân D 2 × 180,0mm |
| Ống carbon tròn 3 × 2mm | 1 × 154mm (xương sống) |
| Màng: mylar 12µm (chăn cứu sinh) hoặc vải dù diều P31N | Khoảng 2 tấm 40 × 45cm |
| Bulông M2 × 10 + đai ốc M2 | 4 (mỗi hub gốc cánh kẹp tay servo bằng 2 bulông xuyên qua) |
| Vít M2 × 6 tự ren (loại vít bắt tai servo) | 4 (mỗi tai servo 1 vít, bắt vào tấm tai của khung) |
| Keo 502 (CA), keo xịt 3M Super 77 (mylar) hoặc B7000 (vải), dây rút nhỏ, dây silicone 30AWG, jack JST 1,25 | — |

## 3. In 3D

| Chi tiết | Số lượng | Vật liệu / thông số |
|---|---|---|
| `PRINT_WingHub_R`, `_L` (hub gốc cánh, một khối liền) | 1 mỗi bên | **PETG** (hoặc PA12), **100% infill**, lớp 0,12mm. Đây là chi tiết chịu lực chính |
| `PRINT_ConnA/B/C/D_R`, `_L` (khớp gân, thành 1,2mm) | 8 | PETG, 100% infill, lớp 0,12mm |
| `Frame_ServoMount` (thành 1,6mm, tấm bắt tai 3mm) | 1 | **PETG**, 100% infill. In nằm nghiêng (một thành bên úp xuống bàn), bật support dạng cây cho ống luồn xương sống |
| `PRINT_BattMount` (kẹp pin, trượt trên ống carbon) | 1 | PETG, 100% infill. In nằm, tấm đỡ pin úp xuống bàn |
| `PRINT_AvionicsMount` (kẹp Nano + NRF24) | 1 | PETG, 100% infill. In đúng tư thế lắp (ống luồn nằm dưới, song song mặt bàn), bật support dạng cây cho ống luồn và thanh ray |

Hub gốc cánh là một khối liền gồm 4 phần:
- **khối kẹp** ôm đầu tay servo, thành 2mm mỗi bên, bắt 2 bulông M2 xuyên qua;
- **khối sau** chôn gốc các ống cắm;
- **3 ống cắm dày**: que cạnh trước Ø7,2mm cắm sâu 18mm; que đường gấp và que gốc Ø4,6mm cắm sâu 14mm;
- **gân liền** nối giữa các ống.

Kiểm tra bền (`analysis/printed_parts_check.py`, với tải xấu nhất): ứng suất gốc ống cắm 3,8–5,0 MPa, hệ số an toàn mỏi 1,6–2,1. Bản cũ là 22–27 MPa, sẽ nứt.

- **Hướng đặt khi in:** đặt hub sao cho **các ống cắm nằm ngang trên bàn in**, mặt phẳng cánh song song mặt bàn. Lực uốn khi đó chạy dọc theo sợi nhựa, không xé ngang giữa các lớp. Dùng support dạng cây cho khối kẹp. Khớp gân cũng đặt nằm, với ống luồn que nằm ngang.
- Lỗ in thường nhỏ đi 0,1–0,2mm. Doa lại bằng mũi khoan tay 2,0 / 1,0 / 0,8mm đến khi que trượt vào vừa khít, rồi cố định bằng keo 502 hoặc epoxy.
- **Tay servo:** khoan 2 lỗ Ø2,2mm trên tay servo zin, trùng 2 lỗ của hub. Vị trí lỗ cách tâm trục 7,8mm và 12,8mm (đo trên mô hình hoặc lấy dấu bằng chính hub).
- Hướng các lỗ trong hub đã tạo sẵn **góc nhị diện 11° và góc gấp 7,3°** cho tấm sau. Đừng khoan lệch hướng.

## 4. Cắt que

- Cắt bằng đĩa cắt Dremel hoặc mài trên giấy nhám; không dùng kéo vì que carbon sẽ bị tưa sợi.
- Chiều dài cắt trong bảng đã trừ phần que cắm vào lỗ khớp: lỗ ở hub gốc cánh bắt đầu cách điểm R 3mm; lỗ ở khớp gân bắt đầu cách mặt que gốc 1mm.

## 5. Cắt màng

1. Đặt mẫu in lên mặt phẳng, phủ màng lên trên, dán băng keo giữ 4 góc.
2. Cắt theo **nét liền** (đường bao), cắt luôn **mép bọc 6mm (nét đứt)** dọc que cạnh trước và que gốc.
3. Đánh dấu lên màng bằng bút lông dầu: đường gấp (nét đỏ), vị trí 4 khớp gân, và điểm R.
4. Mép sau cánh sau có 6 múi lượn sóng: cắt bằng dao mũi nhọn theo đúng nét, các khía chữ V giữa hai múi chỉ cắt tới đáy khía, không xẻ sâu hơn (để màng không bị rách lan khi vỗ).
5. Cánh trái dùng trang 2, là ảnh gương của trang 1.

## 6. Ráp khung cánh (làm ngay trên mẫu in)

1. Cắm ống cạnh trước, que đường gấp và que gốc vào hub gốc cánh. Chưa nhỏ keo.
2. Luồn khớp A và B vào ống cạnh trước, cách R 70mm và 170mm. Luồn khớp C và D vào que đường gấp, cách R 70mm và 170mm.
3. Cắm gân A, B, C, D vào khớp. Các gân toả ra từ gốc như gân bướm thật, đầu gân dừng cách mép màng 6–8mm (gân C, D dừng ở giữa một múi lượn sóng).
4. Đặt khung lên mẫu sao cho mọi que trùng nét vẽ. Tấm sau nằm thấp hơn mặt phẳng tấm trước (xem bước 7). Kiểm tra xong mới nhỏ keo 502 vào từng mối.

## 7. Dán màng và gấp tấm sau

1. Xịt keo lên khung tấm trước (ống cạnh trước, gân A, B, que đường gấp) rồi đặt màng lên, vuốt từ gốc ra đầu cánh. **Để màng hơi chùng**, đừng căng như mặt trống.
2. Gập mép bọc 6mm quanh ống cạnh trước và dán.
3. Dán phần màng sau đường gấp lên que gốc và gân C, D, rồi gập mép bọc quanh que gốc.
4. Góc gấp được tạo sẵn bởi hướng lỗ trong khớp nối. Kiểm tra bằng cách đặt tấm trước phẳng trên bàn (úp cánh xuống, mặt dưới lên trên), rồi đo độ cao các điểm của tấm sau so với mặt bàn:

| Điểm | Cách đường gấp | Độ lệch so với mặt tấm trước |
|---|---|---|
| E, cuối que gốc | 163mm | **18,7mm** |
| Múi xa nhất của mép sau (x −287, y 68) | 172mm | 19,9mm |
| Đầu gân C | 134mm | 15,5mm |
| Giữa que gốc | 81mm | 9,4mm |
| Đầu gân D | 72mm | 8,3mm |

   Sai lệch nhỏ hơn ±2mm là đạt.
5. **Không** dán que dọc mép sau cánh. Mép sau phải tự do để màng tự xoắn khi vỗ; đây là điều kiện để có lực đẩy.

## 8. Ráp thân

1. Lắp 2 servo cạnh nhau vào khung, **trục ra hướng về phía sau** (về phía đuôi). Đẩy đáy servo xuyên qua cửa sổ của tấm tai vào đai sau, tới khi 4 tai servo áp sát tấm tai. Dây servo luồn ra qua rãnh ở thành trên của đai; không để dây bị kẹp dưới thành đai. Bắt 4 vít M2 × 6 tự ren qua lỗ tai vào lỗ Ø1,6 của tấm tai. Vặn vừa chặt: thành nhựa giữa lỗ vít và cửa sổ chỉ dày 0,6mm, vặn quá lực sẽ toác. Có thể nhỏ 1 giọt keo 502 vào mỗi lỗ trước khi vặn.
2. Luồn xương sống (ống carbon tròn 3 × 2mm, dài 154mm) qua ống kẹp của khung servo, thò ra trước 35mm. Nhỏ keo 502 vào ống kẹp.
3. **Kẹp pin** (`PRINT_BattMount`): luồn vào ống carbon từ phía sau, tấm đỡ quay xuống. Đặt pin dưới tấm (dán 1 lớp xốp 2 mặt mỏng ~0,6mm). Dùng 2 dây rút đặt vào 4 khía ở mép tấm: mỗi dây vòng quanh pin, tấm đỡ và **cả ống carbon** (ngoài đoạn ống luồn), nên khi siết thì kẹp cũng bị khóa trên ống. Tâm pin ở x = −39,1mm, tức là 39mm sau mặt phẳng hub gốc cánh. Đây là chỗ chỉnh trọng tâm (bước 9), nên chưa nhỏ keo.
4. **Kẹp điện tử** (`PRINT_AvionicsMount`): luồn vào đuôi ống carbon cho tới khi đầu ống chạm đáy ống luồn (đầu kín). Nhỏ keo 502.
5. **Nano**: cổng USB quay **về phía trước** (về phía pin). Nghiêng mạch, đẩy mép trước vào dưới 2 vấu trước cho chạm chặn, rồi ấn mép sau xuống giữa 2 vấu sau. Dán một mẩu băng dính 2 mặt mỏng trên thanh ngang sau để mạch không rung. Muốn nạp code thì cắm cáp mini‑USB từ phía trước, không cần tháo mạch.
6. **NRF24**: đầu có chân hàn quay về phía Nano, đầu anten quay ra đuôi. Đẩy đầu anten vào dưới 2 vấu cuối, ấn đầu chân hàn xuống giữa 2 gờ dẫn, dán băng dính 2 mặt. Ống carbon dừng ngay dưới đầu chân hàn, nên anten nằm trên phần nhựa. **Không** đi dây hay dán băng nhôm/carbon trên vùng anten.
7. Cho servo về vị trí giữa (1500 µs), lắp tay servo nằm ngang hướng ra ngoài, gắn khớp nối cánh vào tay servo và bắt vít M2.
8. Đi dây (dây silicone 30AWG, hàn thẳng vào lỗ chân của Nano):

   | Từ | Tới | Ghi chú |
   |---|---|---|
   | Pin 2S (+) | Nano **VIN** | Ổn áp 5V trên Nano chạy được tới khi pin còn ~6,4V |
   | Pin 2S (+) | dây đỏ 2 servo | Servo HV chạy thẳng 2S. Tụ 100–220µF/16V sát chỗ cấp nguồn servo |
   | Pin (−) | GND Nano, GND servo, GND NRF24 | Nối chung một điểm |
   | Servo phải / trái (tín hiệu) | **D9 / D10** | Chân PWM của Timer1, dùng cho xung 333 Hz |
   | Nano **5V** | LDO 3,3V vào | LDO đặt ngay đầu NRF24, tụ 10µF giữa VCC và GND của NRF24 |
   | LDO 3,3V ra | NRF24 VCC | **Không** cấp 5V cho NRF24. Không dùng chân 3V3 của Nano bản clone (CH340 cấp không đủ dòng) |
   | NRF24 CE / CSN | **D7 / D8** | |
   | NRF24 SCK / MOSI / MISO | **D13 / D11 / D12** | SPI phần cứng |
   | NRF24 IRQ | không nối | |
   | Pin (+) qua cầu chia 20k/10k | **A0** (tùy chọn) | Đo áp pin: V_pin = V_A0 × 3 |

## 9. Cân trọng tâm và bay thử

1. Trọng tâm phải nằm **22,4mm sau mép trước gốc cánh**, tức là 22,4mm sau mặt phẳng tâm 2 hub gốc cánh (dự trữ ổn định 19mm; chấp nhận 18–25mm). Đỡ bướm bằng 2 ngón tay tại đó: thân phải nằm ngang. Trượt kẹp pin 10mm thì trọng tâm dịch khoảng 1,6mm. Chỉnh xong thì siết dây rút và nhỏ 1 giọt keo 502 vào ống luồn.
2. Ném lượn nhẹ, servo tắt. Theo mô phỏng, máy lượn ở khoảng 4,35 m/s với α khoảng 10°.
3. Bật vỗ ±20° ở 2,5 Hz (`fd` ≈ 222 µs, `ys` ≈ 11 100 µs). Mô phỏng bay tự do với cánh v3.1 cho thấy ±20° leo khoảng 0,5–0,7 m/s (cánh cũ: 0,4 m/s), ±15° leo 0,2 m/s, và khoảng ±9° là bay ngang (mô phỏng không nhớt nên thực tế cần lớn hơn một chút). Dùng biên độ như cần ga. Rẽ bằng lệch biên độ hai cánh, nhưng rất nhẹ: lệch 1° đã làm bướm nghiêng 32° sau 2,4 s. Điều khiển bằng điện thoại và chế độ tự hạ cánh khi mất sóng: `firmware/README.md`.
4. Sau mỗi lần bay 2 phút, sờ thử nhiệt độ servo.
