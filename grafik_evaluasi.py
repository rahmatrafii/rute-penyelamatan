"""Buat grafik PNG/SVG dari hasil eksperimen, tanpa menjalankan A* ulang."""

import argparse
import json
from pathlib import Path
import platform

import evaluasi


def buat_grafik(output=evaluasi.HASIL):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError("Pasang kebutuhan grafik: python -m pip install -r requirements-evaluasi.txt") from error
    output = Path(output)
    rows = evaluasi.baca_hasil(output)
    run = json.loads((output / "metadata_run.json").read_text(encoding="utf-8"))
    if run["sha256_hasil"] != evaluasi.sha_file(output / "hasil_per_peta.csv"):
        raise ValueError("Checksum hasil berbeda dari metadata run.")
    positive = [row for row in rows if row["kelompok"] == "layak" and row["misi_selesai"]]
    sizes = [size for size in evaluasi.UKURAN if any(row["ukuran"] == size for row in positive)]
    if not sizes:
        raise ValueError("Tidak ada misi selesai untuk grafik biaya dan performa.")
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 14,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "svg.fonttype": "none",
    })
    colors = ["#347e8b", "#629852", "#b68038"]
    figures = []

    def save(figure, name):
        figure.savefig(output / f"{name}.png", dpi=180, facecolor="white")
        figure.savefig(output / f"{name}.svg", facecolor="white")
        plt.close(figure)
        figures.append(name)

    for name, field, title, ylabel in (
        ("waktu_pencarian", "waktu_median_ms", "Waktu pencarian A* pada peta layak", "Median waktu per peta (ms)"),
        ("state_diperiksa", "state_diperiksa", "State yang diperiksa pada peta layak", "Jumlah state diperiksa"),
        ("biaya_aksi", "biaya_total", "Biaya misi pada peta layak", "Total biaya aksi"),
    ):
        data = [[row[field] for row in positive if row["ukuran"] == size] for size in sizes]
        figure, axis = plt.subplots(figsize=(8.2, 5.0))
        figure.subplots_adjust(left=0.13, right=0.96, bottom=0.23, top=0.85)
        boxes = axis.boxplot(data, tick_labels=[size.replace("x", " × ") for size in sizes],
                             patch_artist=True, widths=0.46,
                             medianprops={"color": "#172b36", "linewidth": 1.7},
                             flierprops={"markersize": 3, "markeredgecolor": "#6d7880", "alpha": 0.55})
        for patch, color in zip(boxes["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.55)
        axis.set_title(title, pad=17, loc="left", fontweight="bold")
        axis.set_ylabel(ylabel)
        axis.set_xlabel("Ukuran peta")
        axis.set_ylim(bottom=0)
        axis.set_axisbelow(True)
        axis.grid(axis="y", alpha=0.2)
        for index, values in enumerate(data, 1):
            axis.text(index, 1.025, f"n = {len(values)}", transform=axis.get_xaxis_transform(),
                      ha="center", fontsize=9, color="#5e6c76")
        figure.text(0.13, 0.07,
                    "Kotak: kuartil 1–3; garis: median; titik: pencilan (aturan 1,5 × IQR).\n"
                    "6×6: 1 korban/1 stasiun; 8×8 dan 10×10: 3 korban/3 stasiun.",
                    fontsize=9, color="#5e6c76", linespacing=1.6)
        save(figure, name)

    figure, axis = plt.subplots(figsize=(8.2, 5.2))
    figure.subplots_adjust(left=0.12, right=0.97, bottom=0.29, top=0.83)
    labels = ("Layak: misi selesai", "Pos terkurung: ditolak", "Energi kurang: ditolak")
    for kind_index, (kind, label, color) in enumerate(zip(evaluasi.JENIS, labels, colors)):
        positions, rates, counts = [], [], []
        for size_index, size in enumerate(evaluasi.UKURAN):
            group = [row for row in rows if row["ukuran"] == size and row["jenis"] == kind]
            if not group:
                continue
            positions.append(size_index + (kind_index - 1) * 0.24)
            rates.append(100 * sum(row["sesuai_harapan"] for row in group) / len(group))
            counts.append(len(group))
        bars = axis.bar(positions, rates, width=0.21, color=color, label=label)
        for bar, rate, count in zip(bars, rates, counts):
            axis.text(bar.get_x() + bar.get_width() / 2, rate + 2.5,
                      f"{rate:g}%\nn={count}", ha="center", va="bottom", fontsize=8)
    axis.set_title("Kesesuaian hasil dengan label skenario", loc="left", pad=16, fontweight="bold")
    axis.set_xticks(range(len(evaluasi.UKURAN)), [size.replace("x", " × ") for size in evaluasi.UKURAN])
    axis.set_ylabel("Hasil sesuai harapan (%)")
    axis.set_xlabel("Ukuran peta")
    axis.set_ylim(0, 120)
    axis.set_yticks([0, 25, 50, 75, 100])
    axis.set_axisbelow(True)
    axis.grid(axis="y", alpha=0.2)
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3,
                frameon=False, fontsize=8, columnspacing=1.2, handlelength=1.6)
    figure.text(0.12, 0.025, "Peta layak telah disaring A*. Kasus negatif dibuat dengan konstruksi khusus;\n"
                "angka ini bukan akurasi model terlatih atau bukti untuk semua peta.", fontsize=9, color="#5e6c76")
    save(figure, "hasil_pengujian")
    evaluasi.tulis_json(output / "metadata_grafik.json", {
        "sha256_hasil": run["sha256_hasil"], "matplotlib": matplotlib.__version__,
        "python": platform.python_version(), "sha256_script": evaluasi.sha_file(Path(__file__)),
        "grafik": figures,
    })
    evaluasi.buat_laporan(output)
    print(f"{len(figures)} grafik PNG dan SVG tersimpan di {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keluaran", type=Path, default=evaluasi.HASIL)
    args = parser.parse_args()
    try:
        buat_grafik(args.keluaran)
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, f"Pembuatan grafik gagal: {error}\n")
