"""Free-flight comparison chart (dataviz method: one axis per panel, fixed categorical order,
legend + direct labels, recessive grid, text in ink tokens). Reads results/freeflight/cg*_f2.5_a*.csv.

Run:  .venv/Scripts/python plot_freeflight.py
"""
import glob
import re
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).parent
FONTS = Path(r"C:\Users\Admin\.claude\skills\synced\84c7a5b4-017e-4de4-8045-680fd6db7772_92c80b8d-8e49-4727-88f7-7316049f950a\canvas-design\canvas-fonts")
for f in ("WorkSans-Regular.ttf", "IBMPlexMono-Regular.ttf", "Jura-Medium.ttf"):
    if (FONTS / f).exists():
        font_manager.fontManager.addfont(str(FONTS / f))
plt.rcParams.update({"font.family": ["Work Sans", "DejaVu Sans"], "font.size": 9})

SURFACE, TEXT1, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e4df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]        # reference categorical slots 1-4, fixed order
RELEASE = 0.8                                                 # s, prescribed -> free flight


def main():
    files = sorted(glob.glob(str(HERE / "results" / "freeflight" / "cg20_f2.5_a*_U*.csv")),
                   key=lambda f: int(re.search(r"_a(\d+)_", f).group(1)))
    runs = []
    for f in files:
        amp = int(re.search(r"_a(\d+)_", f).group(1))
        r = np.loadtxt(f, delimiter=",", skiprows=1)
        runs.append((amp, r))
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), facecolor=SURFACE)
    panels = [(5, "Góc thân (°)", lambda r: r[:, 5]), (9, "Độ cao (m)", lambda r: -r[:, 9]), (1, "Tốc độ (m/s)", lambda r: r[:, 1])]
    for ax, (_, lab, fn) in zip(axes, panels):
        ax.set_facecolor(SURFACE)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.tick_params(colors=TEXT2, length=0)
        ax.axvline(RELEASE, color=TEXT2, lw=0.8, ls=(0, (2, 3)))
        ends = []
        for k, (amp, r) in enumerate(runs):
            y = fn(r)
            ax.plot(r[:, 0], y, color=SERIES[k], lw=1.6, solid_capstyle="round", label="±%d°" % amp)
            ends.append([y[-1], r[-1, 0], amp])
        # direct labels at the line ends, spread apart so they never collide
        lo, hi = ax.get_ylim()
        gap = 0.07 * (hi - lo)
        ends.sort(key=lambda e: e[0])
        for i in range(1, len(ends)):
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + gap)
        for yl, xl, amp in ends:
            ax.text(xl + 0.04, yl, "±%d°" % amp, color=TEXT1, fontsize=8, va="center", family="IBM Plex Mono")
        ax.set_title(lab, loc="left", color=TEXT1, fontsize=10, pad=8)
        ax.set_xlabel("thời gian (s)", color=TEXT2)
        ax.set_xlim(0, max(r[-1, 0] for _, r in runs) + 0.35)
    axes[0].text(RELEASE + 0.05, axes[0].get_ylim()[1], "thả tự do", color=TEXT2, fontsize=8, va="top")
    axes[0].legend(frameon=False, loc="lower right", fontsize=8, labelcolor=TEXT1, title="biên độ vỗ", title_fontsize=8)
    fig.suptitle("Bay tự do 6 bậc tự do — cánh một tấm gấp, CG 20 mm, 2,5 Hz (Ptera UVLM + MuJoCo)",
                 x=0.01, ha="left", color=TEXT1, fontsize=11, family="Jura")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = HERE / "results" / "freeflight_v3.png"
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    # table view (relief rule for the low-contrast slot)
    rows = ["| Biên độ | Góc thân TB (°) | α TB (°) | Tốc độ TB (m/s) | Tốc độ leo (m/s) |", "|---|---|---|---|---|"]
    for amp, r in runs:
        last = r[r[:, 0] >= r[-1, 0] - 0.4]
        climb = -(last[-1, 9] - last[0, 9]) / (last[-1, 0] - last[0, 0])
        rows.append("| ±%d° | %.1f | %.1f | %.2f | %+.2f |" % (amp, last[:, 5].mean(), last[:, 2].mean(), last[:, 1].mean(), climb))
    (HERE / "results" / "freeflight_v3_table.md").write_text("\n".join(rows), encoding="utf-8")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
