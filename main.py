"""Progress 1: simulasi aturan misi robot penyelamat.

Jalankan `python main.py` untuk demo rute dari PPT.
Jalankan `python main.py --manual` untuk mencoba aksi sendiri.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace


# Peta slide 4. Koordinat dibaca sebagai (baris, kolom), mulai dari 1.
PETA = (
    "P.X..K",
    "..X.X.",
    "..XCX.",
    "......",
    ".XXX..",
    "......",
)
KAPASITAS_ENERGI = 10
BIAYA_AKSI = 1
ARAH = {
    "atas": (-1, 0),
    "bawah": (1, 0),
    "kiri": (0, -1),
    "kanan": (0, 1),
}


def cari_lokasi(simbol: str) -> tuple[int, int]:
    for baris, isi_baris in enumerate(PETA, start=1):
        for kolom, isi_petak in enumerate(isi_baris, start=1):
            if isi_petak == simbol:
                return baris, kolom
    raise ValueError(f"Simbol {simbol} tidak ditemukan di peta.")


POS = cari_lokasi("P")
KORBAN = cari_lokasi("K")
PENGISIAN = cari_lokasi("C")


@dataclass(frozen=True)
class KondisiRobot:
    posisi: tuple[int, int]
    energi: int
    korban_ditangani: bool


KONDISI_AWAL = KondisiRobot(POS, KAPASITAS_ENERGI, False)


def misi_selesai(kondisi: KondisiRobot) -> bool:
    return kondisi.posisi == POS and kondisi.korban_ditangani


def terapkan_aksi(
    kondisi: KondisiRobot, aksi: str
) -> tuple[KondisiRobot, int, str]:
    """Kembalikan (kondisi hasil, biaya aksi, pesan).

    Aksi yang ditolak mengembalikan kondisi semula dengan biaya nol.
    """
    if aksi in ARAH:
        if kondisi.energi < 1:
            return kondisi, 0, "Energi tidak cukup untuk bergerak."
        delta_baris, delta_kolom = ARAH[aksi]
        baris = kondisi.posisi[0] + delta_baris
        kolom = kondisi.posisi[1] + delta_kolom
        if not (1 <= baris <= len(PETA) and 1 <= kolom <= len(PETA[baris - 1])):
            return kondisi, 0, "Petak tujuan berada di luar peta."
        if PETA[baris - 1][kolom - 1] == "X":
            return kondisi, 0, f"Petak {(baris, kolom)} adalah rintangan."
        hasil = replace(kondisi, posisi=(baris, kolom), energi=kondisi.energi - 1)
        return hasil, BIAYA_AKSI, f"Bergerak ke {aksi}."

    if aksi == "tangani":
        if kondisi.posisi != KORBAN:
            return kondisi, 0, "Robot harus berada di lokasi korban (K)."
        if kondisi.korban_ditangani:
            return kondisi, 0, "Korban sudah ditangani."
        if kondisi.energi < 1:
            return kondisi, 0, "Energi tidak cukup untuk menangani korban."
        hasil = replace(kondisi, energi=kondisi.energi - 1, korban_ditangani=True)
        return hasil, BIAYA_AKSI, "Korban berhasil ditangani."

    if aksi == "isi":
        if kondisi.posisi != PENGISIAN:
            return kondisi, 0, "Robot harus berada di tempat pengisian (C)."
        if kondisi.energi >= KAPASITAS_ENERGI:
            return kondisi, 0, "Energi sudah penuh."
        # Fasilitas di C tetap bisa mengisi robot yang energinya nol.
        hasil = replace(kondisi, energi=KAPASITAS_ENERGI)
        return hasil, BIAYA_AKSI, "Energi diisi sampai penuh."

    return kondisi, 0, "Aksi tidak dikenal."


def tampilkan_peta(kondisi: KondisiRobot) -> None:
    print("    " + " ".join(str(kolom) for kolom in range(1, len(PETA[0]) + 1)))
    for baris, isi_baris in enumerate(PETA, start=1):
        petak = list(isi_baris)
        if kondisi.posisi[0] == baris:
            petak[kondisi.posisi[1] - 1] = "R"
        print(f"{baris:>2}  " + " ".join(petak))
    print("R = robot, P = pos, K = korban, C = pengisian, X = rintangan")


def tampilkan_kondisi(kondisi: KondisiRobot, biaya: int) -> None:
    status = "sudah ditangani" if kondisi.korban_ditangani else "belum ditangani"
    print(
        f"Posisi: {kondisi.posisi} | Energi: {kondisi.energi}/{KAPASITAS_ENERGI}"
        f" | Korban: {status} | Total biaya: {biaya}"
    )


def jalankan_aksi(
    kondisi: KondisiRobot, biaya: int, aksi: str
) -> tuple[KondisiRobot, int, bool]:
    hasil, biaya_aksi, pesan = terapkan_aksi(kondisi, aksi)
    total_baru = biaya + biaya_aksi
    label = "OK" if biaya_aksi else "DITOLAK"
    print(f"  [{label}] {pesan}")
    print(
        f"       Posisi {kondisi.posisi} -> {hasil.posisi}"
        f" | Energi {kondisi.energi} -> {hasil.energi}"
        f" | Biaya {biaya} -> {total_baru}"
    )
    return hasil, total_baru, biaya_aksi > 0


def jalankan_demo() -> int:
    kondisi, biaya = KONDISI_AWAL, 0
    print("PROGRESS 1 - Simulasi Misi Robot Penyelamat")
    print("Demo menjalankan urutan aksi manual dari contoh misi di PPT.\n")
    tampilkan_peta(kondisi)
    tampilkan_kondisi(kondisi, biaya)

    print("\n1. Pos ke tempat pengisian (C)")
    kondisi, biaya, berhasil = jalankan_aksi(kondisi, biaya, "kanan")
    if not berhasil:
        return 1
    # Percobaan kedua mengarah ke X di (1, 3) dan seharusnya ditolak.
    kondisi, biaya, berhasil = jalankan_aksi(kondisi, biaya, "kanan")
    if berhasil:
        print("Demo berhenti: petak (1, 3) seharusnya berupa rintangan.")
        return 1

    tahap_demo = (
        ("   Lanjutkan memutar menuju C", ("bawah",) * 3 + ("kanan",) * 2 + ("atas",)),
        ("2. Isi energi di C", ("isi",)),
        ("3. Dari C menuju korban (K)", ("atas",) * 2 + ("kanan",) * 2),
        ("4. Tangani korban", ("tangani",)),
        ("5. Kembali ke C", ("kiri",) * 2 + ("bawah",) * 2),
        ("6. Isi energi kembali", ("isi",)),
        ("7. Kembali ke pos (P)", ("bawah",) + ("kiri",) * 3 + ("atas",) * 3),
    )
    for judul, urutan_aksi in tahap_demo:
        print(f"\n{judul}")
        for aksi in urutan_aksi:
            kondisi, biaya, berhasil = jalankan_aksi(kondisi, biaya, aksi)
            if not berhasil:
                print("Demo berhenti: aksi pada rute contoh tidak dapat dijalankan.")
                return 1

    print()
    tampilkan_peta(kondisi)
    tampilkan_kondisi(kondisi, biaya)
    if misi_selesai(kondisi):
        print("MISI SELESAI: korban sudah ditangani dan robot kembali ke pos.")
        return 0
    print("MISI BELUM SELESAI.")
    return 1


def jalankan_manual() -> None:
    perintah = {
        "w": "atas",
        "s": "bawah",
        "a": "kiri",
        "d": "kanan",
        "h": "tangani",
        "c": "isi",
    }
    kondisi, biaya = KONDISI_AWAL, 0
    print("Mode manual: w/s/a/d = gerak, h = tangani, c = isi, q = keluar.")
    while True:
        print()
        tampilkan_peta(kondisi)
        tampilkan_kondisi(kondisi, biaya)
        if misi_selesai(kondisi):
            print("MISI SELESAI: korban sudah ditangani dan robot kembali ke pos.")
            return
        try:
            tombol = input("Aksi: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nSimulasi dihentikan.")
            return
        if tombol == "q":
            return
        if tombol not in perintah:
            print("Perintah tidak dikenal. Gunakan w, s, a, d, h, c, atau q.")
            continue
        kondisi, biaya, _ = jalankan_aksi(kondisi, biaya, perintah[tombol])


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulasi misi robot penyelamat.")
    parser.add_argument("--manual", action="store_true", help="kendalikan robot dari terminal")
    if parser.parse_args().manual:
        jalankan_manual()
        return 0
    return jalankan_demo()


if __name__ == "__main__":
    raise SystemExit(main())
