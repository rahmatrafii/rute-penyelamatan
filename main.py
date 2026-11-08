"""Simulasi dan perencanaan misi robot penyelamat.

Jalankan `python main.py` untuk demo rute dari PPT.
Jalankan `python main.py --manual` untuk mencoba aksi sendiri.
Jalankan `python main.py --astar` untuk mencari dan menyimulasikan rute otomatis.
Tambahkan `--peta 8x8` atau `--peta 10x10` untuk misi dengan tiga korban.
Jalankan `python main.py --dinamis` untuk demo rintangan di tengah misi 8x8.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, replace
from heapq import heappop, heappush
from itertools import count
from typing import Tuple


KAPASITAS_ENERGI = 10
BIAYA_AKSI = 1
Posisi = Tuple[int, int]
ARAH = {
    "atas": (-1, 0),
    "bawah": (1, 0),
    "kiri": (0, -1),
    "kanan": (0, 1),
}
DAFTAR_AKSI = (*ARAH, "tangani", "isi")


@dataclass(frozen=True)
class PetaMisi:
    petak: tuple[str, ...]
    pos: Posisi
    korban: frozenset[Posisi]
    stasiun: frozenset[Posisi]

    @classmethod
    def dari_baris(cls, petak: tuple[str, ...]) -> PetaMisi:
        if not petak or not petak[0] or any(len(row) != len(petak[0]) for row in petak):
            raise ValueError("Peta harus memiliki baris dan kolom dengan ukuran tetap.")
        lokasi = {simbol: set() for simbol in "PKC"}
        for baris, isi_baris in enumerate(petak, start=1):
            for kolom, simbol in enumerate(isi_baris, start=1):
                if simbol in lokasi:
                    lokasi[simbol].add((baris, kolom))
                elif simbol not in ".X":
                    raise ValueError(f"Simbol peta tidak dikenal: {simbol}.")
        if len(lokasi["P"]) != 1 or not lokasi["K"] or not lokasi["C"]:
            raise ValueError("Peta harus punya satu pos, minimal satu korban dan satu stasiun.")
        return cls(
            petak, next(iter(lokasi["P"])), frozenset(lokasi["K"]), frozenset(lokasi["C"])
        )

    def di_dalam(self, posisi: Posisi) -> bool:
        baris, kolom = posisi
        return 1 <= baris <= len(self.petak) and 1 <= kolom <= len(self.petak[0])

    def simbol(self, posisi: Posisi) -> str:
        baris, kolom = posisi
        return self.petak[baris - 1][kolom - 1]

    def dengan_rintangan(self, posisi: Posisi) -> PetaMisi:
        """Buat peta baru; hanya petak kosong yang boleh menjadi rintangan."""
        if not self.di_dalam(posisi):
            raise ValueError(f"Petak {posisi} berada di luar peta.")
        if self.simbol(posisi) != ".":
            raise ValueError(f"Petak {posisi} bukan petak kosong.")
        baris, kolom = posisi
        petak = list(self.petak)
        lama = petak[baris - 1]
        petak[baris - 1] = lama[:kolom - 1] + "X" + lama[kolom:]
        return replace(self, petak=tuple(petak))


# Koordinat dibaca sebagai (baris, kolom), mulai dari 1.
PETA_CONTOH = {
    "6x6": PetaMisi.dari_baris((
        "P.X..K",
        "..X.X.",
        "..XCX.",
        "......",
        ".XXX..",
        "......",
    )),
    "8x8": PetaMisi.dari_baris((
        "P.C.K...",
        ".XX..X..",
        "...X...C",
        ".X...X..",
        "..C..X.K",
        ".X..X...",
        "....K...",
        "...X....",
    )),
    "10x10": PetaMisi.dari_baris((
        "P.C.K.....",
        ".XX..X..X.",
        "...X...C..",
        ".X...X..X.",
        ".....X...K",
        ".XC.X...X.",
        "..........",
        "...XK.X...",
        "..........",
        "..........",
    )),
}
# Pada rencana awal, kedua peta melewati petak ini setelah K1 ditangani.
RINTANGAN_DEMO = (2, 5)


@dataclass(frozen=True)
class KondisiRobot:
    posisi: Posisi
    energi: int
    korban_ditangani: frozenset[Posisi]


def kondisi_awal(peta: PetaMisi) -> KondisiRobot:
    return KondisiRobot(peta.pos, KAPASITAS_ENERGI, frozenset())


def misi_selesai(peta: PetaMisi, kondisi: KondisiRobot) -> bool:
    return kondisi.posisi == peta.pos and peta.korban <= kondisi.korban_ditangani


def terapkan_aksi(
    peta: PetaMisi, kondisi: KondisiRobot, aksi: str
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
        if not peta.di_dalam((baris, kolom)):
            return kondisi, 0, "Petak tujuan berada di luar peta."
        if peta.simbol((baris, kolom)) == "X":
            return kondisi, 0, f"Petak {(baris, kolom)} adalah rintangan."
        hasil = replace(kondisi, posisi=(baris, kolom), energi=kondisi.energi - 1)
        return hasil, BIAYA_AKSI, f"Bergerak ke {aksi}."

    if aksi == "tangani":
        if kondisi.posisi not in peta.korban:
            return kondisi, 0, "Robot harus berada di lokasi korban (K)."
        if kondisi.posisi in kondisi.korban_ditangani:
            return kondisi, 0, "Korban sudah ditangani."
        if kondisi.energi < 1:
            return kondisi, 0, "Energi tidak cukup untuk menangani korban."
        hasil = replace(
            kondisi,
            energi=kondisi.energi - 1,
            korban_ditangani=kondisi.korban_ditangani | {kondisi.posisi},
        )
        return hasil, BIAYA_AKSI, "Korban berhasil ditangani."

    if aksi == "isi":
        if kondisi.posisi not in peta.stasiun:
            return kondisi, 0, "Robot harus berada di tempat pengisian (C)."
        if kondisi.energi >= KAPASITAS_ENERGI:
            return kondisi, 0, "Energi sudah penuh."
        # Fasilitas di C tetap bisa mengisi robot yang energinya nol.
        hasil = replace(kondisi, energi=KAPASITAS_ENERGI)
        return hasil, BIAYA_AKSI, "Energi diisi sampai penuh."

    return kondisi, 0, "Aksi tidak dikenal."


def manhattan(awal: Posisi, tujuan: Posisi) -> int:
    return abs(awal[0] - tujuan[0]) + abs(awal[1] - tujuan[1])


def heuristik(peta: PetaMisi, kondisi: KondisiRobot) -> int:
    """Perkiraan biaya sisa misi tanpa menghitung rintangan atau pengisian."""
    sisa = peta.korban - kondisi.korban_ditangani
    if not sisa:
        return manhattan(kondisi.posisi, peta.pos) * BIAYA_AKSI
    # Misi harus melewati setiap korban tersisa sebelum pulang.
    # Ambil batas terbesar, tanpa menjumlahkan jarak yang bisa tumpang tindih.
    batas_gerak = max(
        manhattan(kondisi.posisi, korban) + manhattan(korban, peta.pos)
        for korban in sisa
    )
    return (batas_gerak + len(sisa)) * BIAYA_AKSI


@dataclass(frozen=True)
class RencanaMisi:
    aksi: tuple[str, ...]
    biaya: int
    diperiksa: int


def cari_rencana_astar(peta: PetaMisi, awal: KondisiRobot) -> RencanaMisi | None:
    """Cari rencana berbiaya minimum, atau None jika tidak ada rute layak."""
    urutan_masuk = count()
    # Antrean mengurutkan kandidat berdasarkan f. Nomor masuk memecahkan nilai seri.
    antrean = [(heuristik(peta, awal), next(urutan_masuk), 0, awal)]
    biaya_terbaik = {awal: 0}
    asal: dict[KondisiRobot, tuple[KondisiRobot, str]] = {}
    diperiksa = 0

    while antrean:
        _, _, g, kondisi = heappop(antrean)
        if g != biaya_terbaik[kondisi]:
            continue  # Jalur yang lebih murah ke kondisi ini sudah ditemukan.
        diperiksa += 1

        if misi_selesai(peta, kondisi):
            rute = []
            saat_ini = kondisi
            while saat_ini != awal:
                sebelumnya, aksi = asal[saat_ini]
                rute.append(aksi)
                saat_ini = sebelumnya
            return RencanaMisi(tuple(reversed(rute)), g, diperiksa)

        for aksi in DAFTAR_AKSI:
            kandidat, biaya_aksi, _ = terapkan_aksi(peta, kondisi, aksi)
            if biaya_aksi == 0:
                continue  # Aksi ditolak oleh aturan gerak, energi, atau lokasi.

            g_baru = g + biaya_aksi
            if g_baru >= biaya_terbaik.get(kandidat, float("inf")):
                continue
            biaya_terbaik[kandidat] = g_baru
            asal[kandidat] = (kondisi, aksi)
            h = heuristik(peta, kandidat)
            f = g_baru + h
            heappush(antrean, (f, next(urutan_masuk), g_baru, kandidat))

    return None


def label_lokasi(lokasi: frozenset[Posisi], simbol: str) -> dict[Posisi, str]:
    if len(lokasi) == 1:
        return {next(iter(lokasi)): simbol}
    return {posisi: f"{simbol}{i}" for i, posisi in enumerate(sorted(lokasi), start=1)}


def tampilkan_peta(peta: PetaMisi, kondisi: KondisiRobot) -> None:
    label = label_lokasi(peta.korban, "K")
    label.update(label_lokasi(peta.stasiun, "C"))
    label[kondisi.posisi] = "R"
    lebar = max(2, max(map(len, label.values())))
    print("    " + " ".join(f"{i:>{lebar}}" for i in range(1, len(peta.petak[0]) + 1)))
    for baris, isi_baris in enumerate(peta.petak, start=1):
        isi = [label.get((baris, col), simbol) for col, simbol in enumerate(isi_baris, 1)]
        print(f"{baris:>2}  " + " ".join(f"{simbol:>{lebar}}" for simbol in isi))
    print("R = robot, P = pos, K = korban, C = pengisian, X = rintangan")


def status_korban(peta: PetaMisi, kondisi: KondisiRobot) -> str:
    if len(peta.korban) == 1:
        return "sudah ditangani" if kondisi.korban_ditangani else "belum ditangani"
    label = label_lokasi(peta.korban, "K")
    nama = ", ".join(label[posisi] for posisi in sorted(kondisi.korban_ditangani))
    return f"{len(kondisi.korban_ditangani)}/{len(peta.korban)} ({nama or '-'})"


def tampilkan_kondisi(peta: PetaMisi, kondisi: KondisiRobot, biaya: int) -> None:
    status = status_korban(peta, kondisi)
    print(
        f"Posisi: {kondisi.posisi} | Energi: {kondisi.energi}/{KAPASITAS_ENERGI}"
        f" | Korban: {status} | Total biaya: {biaya}"
    )


def jalankan_aksi(
    peta: PetaMisi, kondisi: KondisiRobot, biaya: int, aksi: str
) -> tuple[KondisiRobot, int, bool]:
    hasil, biaya_aksi, pesan = terapkan_aksi(peta, kondisi, aksi)
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
    peta = PETA_CONTOH["6x6"]
    kondisi, biaya = kondisi_awal(peta), 0
    print("PROGRESS 1 - Simulasi Misi Robot Penyelamat")
    print("Demo menjalankan urutan aksi manual dari contoh misi di PPT.\n")
    tampilkan_peta(peta, kondisi)
    tampilkan_kondisi(peta, kondisi, biaya)

    print("\n1. Pos ke tempat pengisian (C)")
    kondisi, biaya, berhasil = jalankan_aksi(peta, kondisi, biaya, "kanan")
    if not berhasil:
        return 1
    # Percobaan kedua mengarah ke X di (1, 3) dan seharusnya ditolak.
    kondisi, biaya, berhasil = jalankan_aksi(peta, kondisi, biaya, "kanan")
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
            kondisi, biaya, berhasil = jalankan_aksi(peta, kondisi, biaya, aksi)
            if not berhasil:
                print("Demo berhenti: aksi pada rute contoh tidak dapat dijalankan.")
                return 1

    print()
    tampilkan_peta(peta, kondisi)
    tampilkan_kondisi(peta, kondisi, biaya)
    if misi_selesai(peta, kondisi):
        print("MISI SELESAI: korban sudah ditangani dan robot kembali ke pos.")
        return 0
    print("MISI BELUM SELESAI.")
    return 1


def jalankan_manual(peta: PetaMisi) -> None:
    perintah = {
        "w": "atas",
        "s": "bawah",
        "a": "kiri",
        "d": "kanan",
        "h": "tangani",
        "c": "isi",
    }
    kondisi, biaya = kondisi_awal(peta), 0
    print("Mode manual: w/s/a/d = gerak, h = tangani, c = isi, q = keluar.")
    while True:
        print()
        tampilkan_peta(peta, kondisi)
        tampilkan_kondisi(peta, kondisi, biaya)
        if misi_selesai(peta, kondisi):
            print("MISI SELESAI: semua korban ditangani dan robot kembali ke pos.")
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
        kondisi, biaya, _ = jalankan_aksi(peta, kondisi, biaya, perintah[tombol])


def lintasan_gerak(awal: Posisi, aksi_rute: deque[str]) -> list[Posisi]:
    """Ubah aksi pada rencana menjadi urutan petak yang akan dilalui."""
    baris, kolom = awal
    lintasan = []
    for aksi in aksi_rute:
        if aksi in ARAH:
            db, dk = ARAH[aksi]
            baris, kolom = baris + db, kolom + dk
            lintasan.append((baris, kolom))
    return lintasan


def ringkas_lintasan(lintasan: list[Posisi]) -> str:
    potongan = " -> ".join(map(str, lintasan[:5]))
    return potongan + (" -> ..." if len(lintasan) > 5 else "")


def tampilkan_kolom_rute() -> None:
    print(
        f"{'No':>3}  {'Aksi':<8} {'Posisi':<10} {'Energi':>6} "
        f"{'Korban':<16} {'g':>3} {'h':>3} {'f':>3}"
    )


def tampilkan_langkah(
    peta: PetaMisi, nomor: int, aksi: str, kondisi: KondisiRobot, biaya: int
) -> None:
    h = heuristik(peta, kondisi)
    status = status_korban(peta, kondisi)
    print(
        f"{nomor:>3}  {aksi:<8} {str(kondisi.posisi):<10} {kondisi.energi:>6} "
        f"{status:<16} {biaya:>3} {h:>3} {biaya + h:>3}"
    )


def jalankan_astar(peta: PetaMisi, rintangan_baru: Posisi | None = None) -> int:
    kondisi, biaya = kondisi_awal(peta), 0
    peta_setelah_perubahan = None
    if rintangan_baru is not None:
        try:
            peta_setelah_perubahan = peta.dengan_rintangan(rintangan_baru)
        except ValueError as pesan:
            print(f"Rintangan tidak bisa ditambahkan: {pesan}")
            return 2
    judul = "PENCARIAN A* DINAMIS" if rintangan_baru is not None else "PENCARIAN A*"
    print(f"{judul} - Simulasi Misi Robot Penyelamat\n")
    tampilkan_peta(peta, kondisi)
    tampilkan_kondisi(peta, kondisi, biaya)
    print("\nMencari rute misi...")
    rencana = cari_rencana_astar(peta, kondisi)
    if rencana is None:
        print("Tidak ada rencana misi yang memenuhi batas energi dan aturan aksi.")
        return 1

    print(f"Rute ditemukan. Kondisi yang diperiksa: {rencana.diperiksa}.")
    print(f"Biaya rencana awal: {rencana.biaya}.")
    print("\nUrutan aksi hasil A* (nilai setelah setiap aksi):")
    tampilkan_kolom_rute()
    nomor, jumlah_pencarian_ulang = 0, 0
    biaya_target = rencana.biaya
    sisa_aksi = deque(rencana.aksi)
    tampilkan_langkah(peta, nomor, "awal", kondisi, biaya)

    while sisa_aksi:
        aksi = sisa_aksi.popleft()
        hasil, biaya_aksi, pesan = terapkan_aksi(peta, kondisi, aksi)
        if biaya_aksi == 0:
            print(f"Simulasi berhenti: {pesan}")
            return 1
        kondisi = hasil
        biaya += biaya_aksi
        nomor += 1
        tampilkan_langkah(peta, nomor, aksi, kondisi, biaya)

        # Skenario demo: rintangan muncul tepat setelah korban pertama ditangani.
        if peta_setelah_perubahan is None or aksi != "tangani":
            continue
        peta = peta_setelah_perubahan
        peta_setelah_perubahan = None
        print(f"\nRINTANGAN BARU di {rintangan_baru} setelah korban pertama ditangani.")
        tampilkan_peta(peta, kondisi)
        tampilkan_kondisi(peta, kondisi, biaya)
        rute_lama = lintasan_gerak(kondisi.posisi, sisa_aksi)
        if rintangan_baru not in rute_lama:
            print("Rintangan berada di luar sisa rute. Robot melanjutkan rencana awal.\n")
            tampilkan_kolom_rute()
            continue

        print(f"Awal sisa rute lama: {ringkas_lintasan(rute_lama)}")
        print("Sisa rute terhalang. A* mencari ulang dari kondisi robot saat ini.")
        jumlah_pencarian_ulang += 1
        rencana_baru = cari_rencana_astar(peta, kondisi)
        if rencana_baru is None:
            print("MISI BERHENTI: tidak ada rute alternatif untuk menyelesaikan misi.")
            print(f"Jumlah pencarian ulang: {jumlah_pencarian_ulang}")
            return 1

        sisa_aksi = deque(rencana_baru.aksi)
        rute_baru = lintasan_gerak(kondisi.posisi, sisa_aksi)
        print(f"Awal sisa rute baru: {ringkas_lintasan(rute_baru)}")
        biaya_target = biaya + rencana_baru.biaya
        print(
            f"Perkiraan biaya misi: {biaya} sudah terpakai + "
            f"{rencana_baru.biaya} tersisa = {biaya_target}.\n"
        )
        tampilkan_kolom_rute()

    print()
    tampilkan_kondisi(peta, kondisi, biaya)
    if rintangan_baru is not None:
        print(f"Jumlah pencarian ulang: {jumlah_pencarian_ulang}")
    if biaya != biaya_target or not misi_selesai(peta, kondisi):
        print("Simulasi tidak menghasilkan kondisi akhir yang direncanakan.")
        return 1
    print("MISI SELESAI: semua korban ditangani dan robot kembali ke pos.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulasi misi robot penyelamat.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--manual", action="store_true", help="kendalikan robot dari terminal")
    mode.add_argument("--astar", action="store_true", help="cari dan simulasikan rute dengan A*")
    mode.add_argument("--dinamis", action="store_true", help="demo perubahan rute di tengah misi")
    parser.add_argument(
        "--peta", choices=PETA_CONTOH, help="pilih ukuran peta (6x6; mode dinamis: 8x8)"
    )
    parser.add_argument(
        "--rintangan", nargs=2, type=int, metavar=("BARIS", "KOLOM"),
        help="lokasi rintangan baru pada mode dinamis (bawaan: 2 5)",
    )
    args = parser.parse_args()
    if args.rintangan is not None and not args.dinamis:
        parser.error("--rintangan hanya bisa digunakan bersama --dinamis.")
    nama_peta = args.peta or ("8x8" if args.dinamis else "6x6")
    peta = PETA_CONTOH[nama_peta]
    if args.dinamis:
        if nama_peta == "6x6" and args.rintangan is None:
            parser.error("Untuk demo dinamis pada peta 6x6, tentukan --rintangan BARIS KOLOM.")
        rintangan = RINTANGAN_DEMO
        if args.rintangan is not None:
            baris, kolom = args.rintangan
            rintangan = (baris, kolom)
        return jalankan_astar(peta, rintangan)
    if args.manual:
        jalankan_manual(peta)
        return 0
    if args.astar or nama_peta != "6x6":
        return jalankan_astar(peta)
    return jalankan_demo()


if __name__ == "__main__":
    raise SystemExit(main())
