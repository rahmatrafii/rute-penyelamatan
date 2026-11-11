"""Dataset dan evaluasi A* asli main.py, tanpa mengubah aplikasi utama.

python evaluasi.py buat-dataset
python evaluasi.py jalankan
python grafik_evaluasi.py   # Matplotlib hanya diperlukan untuk grafik.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import platform
from random import Random
from statistics import mean, median
import sys
from time import get_clock_info, perf_counter_ns

import main as aplikasi

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "data_evaluasi" / "skenario.jsonl"
HASIL = ROOT / "hasil_evaluasi"
UKURAN = tuple(aplikasi.PETA_CONTOH)
JENIS = ("acak_tervalidasi", "pos_terkurung", "energi_tidak_cukup")
JAKARTA = timezone(timedelta(hours=7))
GRAFIK = ("waktu_pencarian", "state_diperiksa", "biaya_aksi", "hasil_pengujian")


def sha_file(path: Path) -> str:
    # Git/Windows dapat mengganti LF menjadi CRLF tanpa mengubah isi logis.
    # Normalisasi teks menjaga checksum tetap sama setelah clone lintas OS.
    data = path.read_bytes()
    if path.suffix.lower() in {".py", ".json", ".jsonl", ".csv", ".md", ".txt", ".svg"}:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def sha_peta(rows) -> str:
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def tulis_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tulis_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Tidak ada baris untuk ditulis.")
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def jarak_bebas(rows, start=(1, 1)) -> dict:
    """BFS geometris tanpa energi, untuk membuktikan label kasus negatif."""
    distances = {tuple(start): 0}
    queue = deque(distances)
    while queue:
        row, column = queue.popleft()
        for dr, dc in aplikasi.ARAH.values():
            point = row + dr, column + dc
            r, c = point
            if (1 <= r <= len(rows) and 1 <= c <= len(rows[0])
                    and rows[r - 1][c - 1] != "X" and point not in distances):
                distances[point] = distances[(row, column)] + 1
                queue.append(point)
    return distances


def peta_negatif(size: str, jenis: str, rng: Random) -> aplikasi.PetaMisi:
    reference = aplikasi.PETA_CONTOH[size]
    n = len(reference.petak)
    grid = [["."] * n for _ in range(n)]
    grid[0][0] = "P"
    if jenis == "pos_terkurung":
        grid[0][1] = grid[1][0] = "X"
    else:
        # Satu pintu di ujung baris kedua membuat jalan pertama ke objek >10.
        for column in range(n - 1):
            grid[1][column] = "X"
    distances = jarak_bebas(grid)
    available = [(r + 1, c + 1) for r in range(n) for c in range(n)
                 if grid[r][c] == "." and (jenis == "pos_terkurung"
                                          or distances.get((r + 1, c + 1), -1) > aplikasi.KAPASITAS_ENERGI)]
    rng.shuffle(available)
    symbols = ["K"] * len(reference.korban) + ["C"] * len(reference.stasiun)
    if len(available) < len(symbols):
        raise ValueError("Tidak cukup lokasi untuk konstruksi kasus negatif.")
    for (row, column), symbol in zip(available, symbols):
        grid[row - 1][column - 1] = symbol
    if jenis == "pos_terkurung":
        empty = [(r, c) for r in range(n) for c in range(n) if grid[r][c] == "."]
        for r, c in rng.sample(empty, min(len(empty), max(0, round(n * n * 0.18) - 2))):
            grid[r][c] = "X"
    return aplikasi.PetaMisi.dari_baris(tuple("".join(row) for row in grid))


def entri_peta(peta, size: str, jenis: str, seed: int, number: int) -> dict:
    return {
        "id": f"{size}-{jenis}-{number:03d}", "ukuran": size,
        "kelompok": "layak" if jenis == JENIS[0] else "tanpa_solusi", "jenis": jenis,
        "seed": seed, "sha256_peta": sha_peta(peta.petak), "petak": list(peta.petak),
        "pos": list(peta.pos), "korban": [list(p) for p in sorted(peta.korban)],
        "stasiun": [list(p) for p in sorted(peta.stasiun)],
        "energi_awal": aplikasi.KAPASITAS_ENERGI, "biaya_aksi": aplikasi.BIAYA_AKSI,
        "harapan_layak": jenis == JENIS[0],
    }


def buat_dataset(path=DATASET, jumlah=100, negatif=10, seed=20261111, timpa=False) -> list[dict]:
    path = Path(path)
    if jumlah < 1 or negatif < 0 or negatif % 2:
        raise ValueError("Jumlah peta layak minimal 1; jumlah negatif harus genap dan tidak negatif.")
    if path.exists() and not timpa:
        raise ValueError(f"Dataset sudah ada: {path}. Gunakan --timpa jika ingin menggantinya.")
    rows, fingerprints, attempts = [], set(), {}
    for size_index, size in enumerate(UKURAN):
        for kind_index, jenis in enumerate(JENIS):
            target = jumlah if kind_index == 0 else negatif // 2
            accepted = attempted = 0
            while accepted < target:
                attempted += 1
                if attempted > target * 100:
                    raise RuntimeError("Terlalu banyak percobaan; dataset belum memenuhi jumlah peta unik.")
                item_seed = seed + size_index * 1_000_000 + kind_index * 100_000 + attempted
                rng = Random(item_seed)
                peta = (aplikasi.buat_peta_acak(aplikasi.PETA_CONTOH[size], aplikasi.PETA_CONTOH[size], rng)
                        if kind_index == 0 else peta_negatif(size, jenis, rng))
                if peta is None or sha_peta(peta.petak) in fingerprints:
                    continue
                fingerprints.add(sha_peta(peta.petak))
                accepted += 1
                rows.append(entri_peta(peta, size, jenis, item_seed, accepted))
                if accepted % 20 == 0:
                    print(f"Dataset {size} / {jenis}: {accepted}/{target}", flush=True)
            attempts[f"{size}/{jenis}"] = {"diterima": accepted, "percobaan": attempted}
            print(f"Selesai {size} / {jenis}: {accepted} peta unik", flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    tulis_json(path.with_suffix(".metadata.json"), {
        "versi_format": 2, "dibuat_jakarta": datetime.now(JAKARTA).isoformat(timespec="seconds"),
        "normalisasi_checksum": "Akhir baris teks dinormalisasi LF; BOM UTF-8 CSV dipertahankan.",
        "seed_dasar": seed, "layak_per_ukuran": jumlah, "negatif_per_ukuran": negatif,
        "jumlah_skenario": len(rows), "percobaan": attempts, "sha256_dataset": sha_file(path),
        "sha256_main_py": sha_file(ROOT / "main.py"), "python": platform.python_version(),
        "sumber": "Sintetis; peta layak dibuat dan disaring buat_peta_acak() asli main.py.",
        "label_negatif": {
            "pos_terkurung": "Semua tetangga pos adalah X; robot tidak dapat memulai perjalanan.",
            "energi_tidak_cukup": "Semua korban/stasiun terhubung secara geometris, tetapi berjarak >10 dari pos; belum ada kesempatan mengisi energi.",
        },
    })
    tulis_csv(path.parent / "indeks_skenario.csv", [{
        key: row[key] for key in ("id", "ukuran", "kelompok", "jenis", "seed", "harapan_layak", "sha256_peta")
    } for row in rows])
    return rows


def baca_dataset(path=DATASET) -> list[dict]:
    path = Path(path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("Dataset kosong.")
    ids, fingerprints = set(), set()
    for row in rows:
        peta = aplikasi.PetaMisi.dari_baris(tuple(row["petak"]))
        size = row["ukuran"]
        if (size not in UKURAN or len(peta.petak) != int(size.split("x")[0])
                or len(peta.petak[0]) != len(peta.petak)):
            raise ValueError("Ukuran peta tidak cocok dengan metadata.")
        if row["id"] in ids or row["sha256_peta"] in fingerprints:
            raise ValueError("ID atau susunan peta duplikat.")
        if sha_peta(peta.petak) != row["sha256_peta"]:
            raise ValueError("Checksum peta tidak cocok.")
        ids.add(row["id"])
        fingerprints.add(row["sha256_peta"])
        if (row["pos"] != list(peta.pos) or row["korban"] != [list(p) for p in sorted(peta.korban)]
                or row["stasiun"] != [list(p) for p in sorted(peta.stasiun)]):
            raise ValueError("Koordinat objek tidak cocok dengan grid.")
        if row["energi_awal"] != aplikasi.KAPASITAS_ENERGI or row["biaya_aksi"] != aplikasi.BIAYA_AKSI:
            raise ValueError("Aturan dataset berbeda dari main.py saat ini.")
        if (row["jenis"] not in JENIS or type(row["harapan_layak"]) is not bool
                or row["harapan_layak"] != (row["jenis"] == JENIS[0])
                or row["kelompok"] != ("layak" if row["harapan_layak"] else "tanpa_solusi")):
            raise ValueError("Label skenario tidak konsisten.")
        distances = jarak_bebas(peta.petak, peta.pos)
        if row["jenis"] == "pos_terkurung" and len(distances) != 1:
            raise ValueError("Bukti pos terkurung tidak terpenuhi.")
        if row["jenis"] == "energi_tidak_cukup" and not all(
            p in distances and distances[p] > row["energi_awal"] for p in peta.korban | peta.stasiun
        ):
            raise ValueError("Bukti keterbatasan energi tidak terpenuhi.")
    manifest = json.loads(path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    if manifest["sha256_dataset"] != sha_file(path) or manifest["jumlah_skenario"] != len(rows):
        raise ValueError("Isi dataset berbeda dari manifest.")
    if manifest["sha256_main_py"] != sha_file(ROOT / "main.py"):
        raise ValueError("main.py berbeda dari versi pembuat dataset; buat dataset ulang untuk versi baru.")
    return rows


def verifikasi_rencana(peta, rencana) -> dict:
    state, total = aplikasi.kondisi_awal(peta), 0
    for action in rencana.aksi:
        state, cost, message = aplikasi.terapkan_aksi(peta, state, action)
        if cost <= 0:
            raise RuntimeError(f"Rencana memiliki aksi tidak sah: {action}: {message}")
        total += cost
    if not aplikasi.misi_selesai(peta, state) or total != rencana.biaya:
        raise RuntimeError("Eksekusi rencana tidak memenuhi hasil misi/biaya yang dijanjikan.")
    counts = Counter(rencana.aksi)
    return {
        "biaya_total": total, "jumlah_aksi": len(rencana.aksi),
        "gerak": sum(counts[arah] for arah in aplikasi.ARAH),
        "tangani": counts["tangani"], "isi": counts["isi"], "energi_akhir": state.energi,
        "sha256_aksi": hashlib.sha256("|".join(rencana.aksi).encode()).hexdigest(),
    }


def state_tanpa_solusi(peta) -> int:
    """Baca counter lokal saat A* mengembalikan None; di luar pengukuran waktu.

    API asli hanya mengembalikan counter ketika solusi ada. Observer ini tidak
    mengganti algoritma dan dipasang hanya untuk satu pencarian tambahan kasus negatif.
    """
    counter = None
    code = aplikasi.cari_rencana_astar.__code__

    def observe(frame, event, arg):
        nonlocal counter
        if event == "return" and frame.f_code is code:
            counter = frame.f_locals.get("diperiksa")

    previous = sys.getprofile()
    try:
        sys.setprofile(observe)
        result = aplikasi.cari_rencana_astar(peta, aplikasi.kondisi_awal(peta))
    finally:
        sys.setprofile(previous)
    if result is not None or not isinstance(counter, int):
        raise RuntimeError("Counter pencarian tanpa solusi tidak dapat diverifikasi.")
    return counter


def signature(plan):
    return None if plan is None else (plan.aksi, plan.biaya, plan.diperiksa)


def evaluasi_satu(row: dict, ulang: int) -> tuple[dict, list[dict]]:
    peta = aplikasi.PetaMisi.dari_baris(tuple(row["petak"]))
    initial = aplikasi.kondisi_awal(peta)
    warmup = aplikasi.cari_rencana_astar(peta, initial)
    expected = signature(warmup)
    raw = []
    for repeat in range(1, ulang + 1):
        started = perf_counter_ns()
        plan = aplikasi.cari_rencana_astar(peta, initial)
        elapsed = perf_counter_ns() - started
        if signature(plan) != expected:
            raise RuntimeError("Hasil A* berubah antarulangan pada peta yang sama.")
        raw.append({"id": row["id"], "ulangan": repeat, "waktu_ns": elapsed,
                    "waktu_ms": round(elapsed / 1_000_000, 6)})
    solved = plan is not None
    details = verifikasi_rencana(peta, plan) if solved else {
        "biaya_total": None, "jumlah_aksi": None, "gerak": None, "tangani": None,
        "isi": None, "energi_akhir": None, "sha256_aksi": "",
    }
    times = [item["waktu_ns"] / 1_000_000 for item in raw]
    result = {
        "id": row["id"], "ukuran": row["ukuran"], "kelompok": row["kelompok"],
        "jenis": row["jenis"], "seed": row["seed"], "sha256_peta": row["sha256_peta"],
        "jumlah_korban": len(peta.korban), "jumlah_stasiun": len(peta.stasiun),
        "jumlah_rintangan": sum(line.count("X") for line in peta.petak),
        "harapan_layak": int(row["harapan_layak"]), "misi_selesai": int(solved),
        "sesuai_harapan": int(solved == row["harapan_layak"]), **details,
        "state_diperiksa": plan.diperiksa if solved else state_tanpa_solusi(peta),
        "waktu_median_ms": round(median(times), 6), "waktu_min_ms": round(min(times), 6),
        "waktu_max_ms": round(max(times), 6), "pengulangan": ulang,
    }
    return result, raw


def ringkas(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["ukuran"], row["jenis"])].append(row)
    summary = []
    for (size, jenis), group in sorted(groups.items(), key=lambda item: (UKURAN.index(item[0][0]), JENIS.index(item[0][1]))):
        solved = [row for row in group if row["misi_selesai"]]
        summary.append({
            "ukuran": size, "jenis": jenis, "jumlah_peta": len(group), "misi_selesai": len(solved),
            "misi_selesai_persen": round(100 * len(solved) / len(group), 3),
            "sesuai_harapan_persen": round(100 * mean(row["sesuai_harapan"] for row in group), 3),
            "biaya_rata_rata": round(mean(row["biaya_total"] for row in solved), 3) if solved else None,
            "waktu_median_ms": round(median(row["waktu_median_ms"] for row in group), 6),
            "state_rata_rata": round(mean(row["state_diperiksa"] for row in group), 3),
        })
    return summary


def jalankan(dataset=DATASET, keluaran=HASIL, ulang=5, seed=20261112) -> list[dict]:
    if ulang < 1:
        raise ValueError("Pengulangan minimal 1.")
    dataset, output = Path(dataset), Path(keluaran)
    scenarios = baca_dataset(dataset)
    Random(seed).shuffle(scenarios)
    rows, measurements = [], []
    started = datetime.now(JAKARTA)
    for index, scenario in enumerate(scenarios, 1):
        row, raw = evaluasi_satu(scenario, ulang)
        row["urutan_uji"] = index
        rows.append(row)
        measurements.extend(raw)
        if index % 20 == 0 or index == len(scenarios):
            print(f"Evaluasi {index}/{len(scenarios)} peta; {index * ulang} pencarian terukur", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    rows.sort(key=lambda row: row["id"])
    tulis_csv(output / "hasil_per_peta.csv", rows)
    tulis_csv(output / "waktu_per_ulangan.csv", measurements)
    tulis_csv(output / "ringkasan.csv", ringkas(rows))
    tulis_json(output / "metadata_run.json", {
        "mulai_jakarta": started.isoformat(timespec="seconds"),
        "selesai_jakarta": datetime.now(JAKARTA).isoformat(timespec="seconds"),
        "python": platform.python_version(), "implementasi_python": platform.python_implementation(),
        "os": platform.platform(), "cpu": platform.processor(),
        "jumlah_skenario": len(rows), "pengulangan": ulang, "jumlah_pencarian_terukur": len(measurements),
        "seed_urutan_uji": seed, "warmup_per_peta": 1,
        "timer": "time.perf_counter_ns", "resolusi_timer_ns": get_clock_info("perf_counter").resolution * 1e9,
        "sha256_main_py": sha_file(ROOT / "main.py"), "sha256_evaluasi_py": sha_file(Path(__file__)),
        "sha256_dataset": sha_file(dataset), "dataset": dataset.name,
        "sha256_hasil": sha_file(output / "hasil_per_peta.csv"),
        "normalisasi_checksum": "Akhir baris teks dinormalisasi LF; BOM UTF-8 CSV dipertahankan.",
        "counter_tanpa_solusi": "Satu pencarian tambahan dengan sys.setprofile; tidak masuk pengukuran waktu.",
    })
    buat_laporan(output)
    return rows


def baca_hasil(output=HASIL) -> list[dict]:
    with (Path(output) / "hasil_per_peta.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    integers = ("misi_selesai", "sesuai_harapan", "state_diperiksa", "pengulangan", "biaya_total")
    for row in rows:
        for key in integers:
            row[key] = int(row[key]) if row[key] != "" else None
        row["waktu_median_ms"] = float(row["waktu_median_ms"])
    return rows


def buat_laporan(output=HASIL) -> Path:
    output = Path(output)
    rows = baca_hasil(output)
    meta = json.loads((output / "metadata_run.json").read_text(encoding="utf-8"))
    if meta["sha256_hasil"] != sha_file(output / "hasil_per_peta.csv"):
        raise ValueError("Checksum hasil berbeda dari metadata run.")
    positive = [row for row in rows if row["kelompok"] == "layak"]
    negative = [row for row in rows if row["kelompok"] == "tanpa_solusi"]
    solved = sum(row["misi_selesai"] for row in positive)
    rejected = sum(not row["misi_selesai"] for row in negative)
    matching = sum(row["sesuai_harapan"] for row in rows)
    lines = [
        "# Laporan Evaluasi A* — Robot Penyelamat", "",
        f"Pengujian nyata: **{len(rows)} peta unik**, **{meta['pengulangan']} pengulangan per peta**, "
        f"dan **{meta['jumlah_pencarian_terukur']} pencarian terukur**.", "",
        f"- Misi selesai pada peta layak: **{solved}/{len(positive)}**.",
        f"- Penolakan benar pada kasus tanpa solusi: **{rejected}/{len(negative)}**.",
        f"- Seluruh hasil sesuai label skenario: **{matching}/{len(rows)}**.", "",
        "Ini adalah evaluasi algoritma pencarian. Tidak ada pelatihan model atau pembagian training/testing.", "",
        "## 1. Data dan sumbernya", "",
        "Data bersifat **sintetis**. Satu baris dataset adalah satu skenario peta, bukan satu petak. "
        "Peta layak dihasilkan fungsi `buat_peta_acak()` asli main.py; fungsi tersebut sudah menyaring peta menggunakan A*. "
        "Karena itu, keberhasilan tinggi pada kelompok ini tidak membuktikan keberhasilan pada sembarang peta.", "",
        "Kasus negatif dibagi dua: pos terkurung rintangan; dan seluruh korban/stasiun terhubung secara geometris "
        "tetapi berjarak lebih dari 10 langkah sebelum robot dapat mengisi energi. Label negatif dibuktikan "
        "melalui konstruksi peta dan BFS geometris, terpisah dari A* yang diuji.", "",
        "Susunan grid lengkap, koordinat, seed, label, dan checksum disimpan di `data_evaluasi/skenario.jsonl`. "
        "Jumlah korban/stasiun: 6×6 memiliki 1/1; 8×8 dan 10×10 memiliki 3/3. Energi awal 10 dan biaya tiap aksi 1.", "",
        "## 2. Metode pengukuran", "",
        "- Memanggil `cari_rencana_astar()` asli tanpa mengubah main.py.",
        "- Urutan skenario diacak dengan seed yang tercatat; satu warmup per peta tidak dihitung.",
        f"- Setiap peta dicari {meta['pengulangan']} kali. Timer hanya membungkus pencarian A*: "
        "pembuatan peta, validasi, GUI, cetak terminal, dan penulisan file tidak dihitung.",
        "- Waktu per peta adalah median ulangan. Waktu pada tabel berikut adalah median antar-peta dari median tersebut.",
        "- Semua urutan aksi dieksekusi ulang dengan aturan asli di luar timer untuk memeriksa biaya, energi, korban, dan kepulangan ke pos.",
        "- State diperiksa adalah kondisi lengkap (posisi, energi, korban ditangani), bukan jumlah gerak robot.",
        "- Untuk kasus tanpa solusi, counter lokal A* dibaca pada pencarian tambahan dengan observer; pencarian tersebut tidak dihitung waktunya.", "",
        "## 3. Hasil peta layak", "",
        "| Ukuran | Peta | Misi selesai | Biaya rata-rata | Median waktu (ms) | State rata-rata |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    summary = ringkas(rows)
    for group in summary:
        if group["jenis"] == JENIS[0]:
            cost = "—" if group["biaya_rata_rata"] is None else f"{group['biaya_rata_rata']:.2f}"
            lines.append(f"| {group['ukuran']} | {group['jumlah_peta']} | {group['misi_selesai']} | {cost} | "
                         f"{group['waktu_median_ms']:.3f} | {group['state_rata_rata']:.2f} |")
    lines += ["", "## 4. Kasus tanpa solusi", "",
              "Hasil `None` pada kelompok ini adalah keluaran yang benar. Biaya rute dikosongkan, bukan ditulis nol.", "",
              "| Ukuran | Jenis | Peta | Penolakan benar | Median waktu (ms) | State rata-rata |",
              "|---|---|---:|---:|---:|---:|"]
    for group in summary:
        if group["jenis"] != JENIS[0]:
            lines.append(f"| {group['ukuran']} | {group['jenis']} | {group['jumlah_peta']} | "
                         f"{group['jumlah_peta'] - group['misi_selesai']} | {group['waktu_median_ms']:.3f} | "
                         f"{group['state_rata_rata']:.2f} |")
    plot_meta = output / "metadata_grafik.json"
    plots_current = plot_meta.exists() and json.loads(plot_meta.read_text(encoding="utf-8")).get("sha256_hasil") == meta["sha256_hasil"]
    lines += ["", "## 5. Grafik", ""]
    if plots_current:
        for name in GRAFIK:
            lines += [f"![{name.replace('_', ' ').capitalize()}]({name}.png)", ""]
    else:
        lines += ["Grafik untuk run ini belum dibuat. Jalankan `python grafik_evaluasi.py`.", ""]
    lines += [
        "## 6. Batas interpretasi", "",
        "- Ukuran peta 6×6 juga memiliki korban/stasiun lebih sedikit. Perbedaan waktu tidak dapat diatribusikan hanya kepada ukuran grid.",
        "- Peta layak sudah dipilih oleh A*. Kasus negatif merupakan kasus terstruktur, bukan sampel semua kemungkinan peta.",
        "- Belum ada pembanding UCS atau pengukuran optimalitas independen; hasil ini tidak membuktikan A* lebih cepat dari algoritma lain.",
        "- Waktu bergantung pada perangkat, versi Python, dan beban komputer. Ulangi pada kondisi yang konsisten untuk perbandingan baru.", "",
        "## 7. Kalimat untuk progres dosen", "",
        f"> Saya menguji A* pada {len(rows)} skenario peta sintetis. Sebanyak {len(positive)} peta layak "
        f"dan {len(negative)} kasus tanpa solusi dilaporkan terpisah. Setiap peta diuji {meta['pengulangan']} kali. "
        "Evaluasinya meliputi keberhasilan misi, biaya aksi, waktu pencarian, dan jumlah state yang diperiksa.", "",
        "## 8. Jejak eksperimen", "",
        f"- Waktu mulai (Asia/Jakarta): `{meta['mulai_jakarta']}`.",
        f"- Python: `{meta['python']}`; OS: `{meta['os']}`; CPU: `{meta['cpu']}`.",
        f"- Seed urutan pengujian: `{meta['seed_urutan_uji']}`.",
        f"- SHA-256 main.py: `{meta['sha256_main_py']}`.",
        f"- SHA-256 dataset: `{meta['sha256_dataset']}`.",
        "- Checksum teks memakai akhir baris LF agar konsisten antara checkout Windows dan Linux.",
        "- Data hasil: [per peta](hasil_per_peta.csv), [setiap ulangan](waktu_per_ulangan.csv), [ringkasan](ringkasan.csv), [metadata](metadata_run.json).", "",
    ]
    target = output / "laporan.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Dataset dan evaluasi A* untuk progres proyek Python.")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("buat-dataset", help="buat peta unik dan manifest")
    create.add_argument("--jumlah", type=int, default=100, help="peta layak per ukuran")
    create.add_argument("--negatif", type=int, default=10, help="kasus negatif per ukuran, harus genap")
    create.add_argument("--seed", type=int, default=20261111)
    create.add_argument("--dataset", type=Path, default=DATASET)
    create.add_argument("--timpa", action="store_true")
    run = sub.add_parser("jalankan", help="ukur pencarian dan validasi rencana")
    run.add_argument("--dataset", type=Path, default=DATASET)
    run.add_argument("--keluaran", type=Path, default=HASIL)
    run.add_argument("--ulang", type=int, default=5)
    run.add_argument("--seed", type=int, default=20261112)
    report = sub.add_parser("laporan", help="perbarui laporan dari hasil CSV")
    report.add_argument("--keluaran", type=Path, default=HASIL)
    args = parser.parse_args()
    try:
        if args.command == "buat-dataset":
            rows = buat_dataset(args.dataset, args.jumlah, args.negatif, args.seed, args.timpa)
            print(f"Dataset tersimpan: {args.dataset} ({len(rows)} skenario)")
        elif args.command == "jalankan":
            rows = jalankan(args.dataset, args.keluaran, args.ulang, args.seed)
            print(f"Hasil tersimpan: {args.keluaran}; {sum(row['sesuai_harapan'] for row in rows)}/{len(rows)} sesuai harapan")
        else:
            print(buat_laporan(args.keluaran))
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, f"Evaluasi gagal: {error}\n")


if __name__ == "__main__":
    main()
