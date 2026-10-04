# Butterfly RC — bướm điều khiển từ xa 2 servo

ESP32‑C3 Super Mini, 2 servo PTK 7465Plus, cánh một tấm màng gấp, sải cánh 805mm, khối lượng 60g.

## Bắt đầu từ đâu

| Muốn | Mở file |
|---|---|
| Xem tổng thể thiết kế | `design/drawings/butterfly_cover.pdf` (hoặc `.png`) |
| Thi công | `design/HUONG_DAN_THI_CONG.md` |
| In mẫu cắt cánh 1:1 | `design/drawings/wing_template_A2.pdf` (khổ A2) hoặc `wing_template_A4_tiles.pdf` (ghép A4) |
| Cắt que carbon | `design/drawings/rod_cut_list.md` |
| In 3D | `design/stl/*.stl` |
| Xem chuyển động | `simulation/*.gif` (bản cũ trong `v1_old/`, `v2_two_panels/`) |
| Phân tích khí động, kết cấu, ổn định, bay tự do | `analysis/BAO_CAO_khi_dong_ket_cau.md`, `analysis/results/` |

## Một nguồn kích thước duy nhất

Mọi kích thước nằm trong `design/butterfly_params.json`. Hình học cánh nằm trong `design/wing_geometry.py`, dùng chung cho Fusion, bản vẽ và mô phỏng.

Khi sửa thiết kế:
1. Sửa `design/butterfly_params.json`.
2. Trong Fusion, chạy `design/fusion_build.py`. Script dựng lại mô hình và xuất `fusion_mass_properties.json`.
3. Tạo lại bản vẽ:
   ```
   analysis/.venv/Scripts/python design/make_drawings.py
   analysis/.venv/Scripts/python design/make_cover.py
   ```
4. Chạy lại mô phỏng:
   ```
   cd analysis
   .venv/Scripts/python butterfly_aero.py         # chuẩn tĩnh: lực, servo, uốn que
   .venv/Scripts/python ptera_stability.py        # ổn định dọc (UVLM)
   .venv/Scripts/python ptera_freeflight.py 192 4.0 9 20 2.5   # bay tự do: bước, U0, α0, biên độ, tần số
   .venv/Scripts/python plot_freeflight.py
   ```

Môi trường Python (`analysis/.venv`, không đưa vào git) tạo lại bằng lệnh:

```
python -m venv analysis/.venv
analysis/.venv/Scripts/python -m pip install numpy scipy matplotlib pterasoftware shapely pymupdf
```
