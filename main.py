"""Simulasi dan perencanaan misi robot penyelamat.

Jalankan `python main.py` untuk demo rute dari PPT.
Jalankan `python main.py --manual` untuk mencoba aksi sendiri.
Jalankan `python main.py --astar` untuk mencari dan menyimulasikan rute otomatis.
Tambahkan `--peta 8x8` atau `--peta 10x10` untuk misi dengan tiga korban.
Jalankan `python main.py --dinamis` untuk demo rintangan di tengah misi 8x8.
Jalankan `python main.py --gui` untuk membuka tampilan Tkinter.
Di jendela Tkinter, klik Acak Peta untuk mencoba susunan misi yang berbeda.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, replace
from heapq import heappop, heappush
from itertools import count
from random import Random
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


def _jalur_acak(awal: Posisi, akhir: Posisi, rng: Random) -> set[Posisi]:
    """Sisakan jalur terpendek dengan urutan gerakan yang diacak."""
    b, k = awal
    db, dk = akhir[0] - b, akhir[1] - k
    gerak = [(1 if db > 0 else -1, 0)] * abs(db)
    gerak += [(0, 1 if dk > 0 else -1)] * abs(dk)
    rng.shuffle(gerak)
    petak = {awal}
    for turun, kanan in gerak:
        b, k = b + turun, k + kanan
        petak.add((b, k))
    return petak


def buat_peta_acak(
    acuan: PetaMisi, peta_lama: PetaMisi, rng: Random | None = None
) -> PetaMisi | None:
    """Acak objek dan rintangan, lalu validasi misi dengan A*."""
    rng = rng if rng is not None else Random()
    baris, kolom = len(acuan.petak), len(acuan.petak[0])
    koordinat = [(b, k) for b in range(1, baris + 1) for k in range(1, kolom + 1)]
    jarak_korban = (KAPASITAS_ENERGI - 1) // 2

    for _ in range(16):
        objek = {acuan.pos: "P"}
        jalur_bebas = {acuan.pos}
        sebelumnya = acuan.pos
        stasiun = []
        # Hubungkan pos dan stasiun dengan jarak yang bisa ditempuh sekali isi.
        for _ in acuan.stasiun:
            pilihan = [
                pos for pos in koordinat if pos not in objek
                and 2 <= manhattan(sebelumnya, pos) <= KAPASITAS_ENERGI - 2
            ]
            if not pilihan:
                break
            pos = rng.choice(pilihan)
            objek[pos] = "C"
            stasiun.append(pos)
            jalur_bebas.update(_jalur_acak(sebelumnya, pos, rng))
            sebelumnya = pos
        if len(stasiun) != len(acuan.stasiun):
            continue
        # Setiap korban dapat didatangi dan ditangani dari satu stasiun.
        for i in range(len(acuan.korban)):
            dekat = stasiun[i % len(stasiun)]
            pilihan = [
                pos for pos in koordinat if pos not in objek
                and 1 <= manhattan(dekat, pos) <= jarak_korban
            ]
            if not pilihan:
                break
            pos = rng.choice(pilihan)
            objek[pos] = "K"
            jalur_bebas.update(_jalur_acak(dekat, pos, rng))
        if len(objek) != 1 + len(acuan.stasiun) + len(acuan.korban):
            continue

        pilihan = [pos for pos in koordinat if pos not in jalur_bebas]
        jumlah = min(len(pilihan), round(baris * kolom * 0.18))
        rintangan = set(rng.sample(pilihan, jumlah))
        petak = tuple(
            "".join(objek.get((b, k), "X" if (b, k) in rintangan else ".")
                    for k in range(1, kolom + 1))
            for b in range(1, baris + 1)
        )
        if petak == peta_lama.petak:
            continue
        peta = PetaMisi.dari_baris(petak)
        if cari_rencana_astar(peta, kondisi_awal(peta)) is not None:
            return peta
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


class SesiMisi:
    """Kondisi simulasi yang diubah satu aksi pada setiap langkah."""

    def __init__(self, peta: PetaMisi) -> None:
        self.peta = peta
        self.kondisi = kondisi_awal(peta)
        self.biaya = 0
        self.status = "siap"
        self.aksi: deque[str] = deque()
        self.jejak = [self.kondisi.posisi]
        self.rute_lama: list[Posisi] = []
        self.rintangan_baru: set[Posisi] = set()
        self.pencarian_ulang = 0
        self.biaya_rencana: int | None = None

    def _rencanakan(self) -> bool:
        rencana = cari_rencana_astar(self.peta, self.kondisi)
        if rencana is None:
            self.aksi.clear()
            self.biaya_rencana = None
            self.status = "buntu"
            return False
        self.aksi = deque(rencana.aksi)
        self.biaya_rencana = self.biaya + rencana.biaya
        self.status = "selesai" if misi_selesai(self.peta, self.kondisi) else "berjalan"
        return True

    def mulai(self) -> bool:
        if self.status == "siap":
            return self._rencanakan()
        return self.status == "berjalan"

    def rute_aktif(self) -> list[Posisi]:
        return [self.kondisi.posisi] + lintasan_gerak(self.kondisi.posisi, self.aksi)

    def langkah(self) -> str:
        if self.status != "berjalan" or not self.aksi:
            return "Tidak ada aksi yang bisa dijalankan."
        aksi = self.aksi.popleft()
        hasil, biaya, pesan = terapkan_aksi(self.peta, self.kondisi, aksi)
        if not biaya:
            self.aksi.clear()
            self.biaya_rencana = None
            self.status = "buntu"
            return f"Misi berhenti: {pesan}"

        if hasil.posisi != self.kondisi.posisi:
            self.jejak.append(hasil.posisi)
        self.kondisi = hasil
        self.biaya += biaya

        if misi_selesai(self.peta, self.kondisi):
            self.status = "selesai"
            return "Misi selesai: semua korban ditangani dan robot kembali ke pos."
        if aksi == "tangani":
            korban = label_lokasi(self.peta.korban, "K")[hasil.posisi]
            return f"{korban} berhasil ditangani."
        if aksi == "isi":
            stasiun = label_lokasi(self.peta.stasiun, "C")[hasil.posisi]
            return f"Isi energi di {stasiun}. Energi kembali ke {KAPASITAS_ENERGI}."
        return f"Robot {aksi} ke petak {hasil.posisi}."

    def tambah_rintangan(self, posisi: Posisi) -> str:
        if self.status != "berjalan":
            raise ValueError("Mulai misi sebelum menambahkan rintangan.")
        if posisi == self.kondisi.posisi:
            raise ValueError("Robot sedang menempati petak ini.")
        self.peta = self.peta.dengan_rintangan(posisi)
        self.rintangan_baru.add(posisi)
        rute = self.rute_aktif()
        if posisi not in rute:
            return f"Rintangan di {posisi} berada di luar rute. Rencana tetap berlaku."

        self.rute_lama = rute
        self.pencarian_ulang += 1
        if not self._rencanakan():
            return f"Rintangan di {posisi}. Misi berhenti karena tidak ada rute alternatif."
        return (
            f"Rintangan di {posisi}. A* menemukan rute baru dari {self.kondisi.posisi}; "
            f"perkiraan total biaya {self.biaya_rencana}."
        )


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


class TampilanMisi:
    LATAR = "#0b1421"
    PANEL = "#132236"
    KANVAS = "#101c2c"
    GARIS = "#2a3d55"
    TINTA = "#f0f5fc"
    REDUP = "#acbdd0"
    AKTIF = "#52dfad"
    LAMA = "#ffc174"
    JEJAK = "#8298b5"

    def __init__(self, root, tk, ttk, nama_peta: str) -> None:
        self.root = root
        self.peta_awal = PETA_CONTOH[nama_peta]
        self.jenis_peta = "Peta contoh"
        self.sesi = SesiMisi(self.peta_awal)
        self.otomatis = False
        self.memilih = False
        self.timer = None
        self.geometri_peta = None
        self.info = "Tekan Mulai untuk berjalan otomatis atau Langkah untuk maju satu aksi."
        self.nama_peta = tk.StringVar(root, value=nama_peta)
        self.teks_peta = tk.StringVar(root)
        self.teks_status = tk.StringVar(root)
        self.teks_energi = tk.StringVar(root)
        self.teks_ringkas = tk.StringVar(root)
        self.teks_korban = tk.StringVar(root)
        self.teks_info = tk.StringVar(root)

        root.title("Robot Penyelamat | Simulasi A*")
        root.geometry("1080x720")
        root.minsize(850, 640)
        root.configure(bg=self.LATAR)
        root.protocol("WM_DELETE_WINDOW", self.tutup)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        gaya = ttk.Style(root)
        if "clam" in gaya.theme_names():
            gaya.theme_use("clam")
        gaya.configure(
            "Misi.TButton", padding=(12, 8), font=("TkDefaultFont", 10, "bold"),
            background="#20344d", foreground=self.TINTA, bordercolor=self.GARIS,
            lightcolor="#20344d", darkcolor="#20344d", focuscolor=self.GARIS,
        )
        gaya.map("Misi.TButton", background=[("disabled", "#18283b"), ("active", "#2c4665")],
                 foreground=[("disabled", "#8395ac")])
        gaya.configure(
            "Utama.Misi.TButton", background=self.AKTIF, foreground="#09261d",
            bordercolor=self.AKTIF, lightcolor=self.AKTIF, darkcolor=self.AKTIF,
        )
        gaya.map("Utama.Misi.TButton", background=[("disabled", "#1b3540"), ("active", "#80edc6")],
                 foreground=[("disabled", "#92aaa9")])
        gaya.configure(
            "Misi.TCombobox", fieldbackground="#20344d", foreground=self.TINTA,
            background="#20344d", arrowcolor=self.TINTA, bordercolor=self.GARIS, padding=5,
        )
        gaya.map("Misi.TCombobox", fieldbackground=[("readonly", "#20344d")],
                 foreground=[("readonly", self.TINTA)])
        for nama, warna in (("Energi", self.AKTIF), ("EnergiRendah", self.LAMA)):
            gaya.configure(
                f"{nama}.Horizontal.TProgressbar", background=warna,
                troughcolor=self.LATAR, bordercolor=self.LATAR,
                lightcolor=warna, darkcolor=warna, thickness=10,
            )

        header = tk.Frame(root, bg=self.PANEL, padx=22, pady=14)
        header.grid(row=0, column=0, sticky="ew")
        judul = tk.Frame(header, bg=self.PANEL)
        judul.pack(side="left")
        tk.Label(judul, text="Robot Penyelamat", bg=self.PANEL, fg=self.TINTA,
                 font=("TkDefaultFont", 19, "bold")).pack(anchor="w")
        tk.Label(judul, text="Perencanaan misi A*  ·  Peta dinamis", bg=self.PANEL,
                 fg=self.REDUP, font=("TkDefaultFont", 10)).pack(anchor="w", pady=(2, 0))
        alat_peta = tk.Frame(header, bg=self.PANEL)
        alat_peta.pack(side="right")
        tk.Label(alat_peta, text="Ukuran", bg=self.PANEL, fg=self.REDUP).pack(side="left", padx=(0, 8))
        pilihan = ttk.Combobox(alat_peta, textvariable=self.nama_peta, values=tuple(PETA_CONTOH),
                              state="readonly", width=6, style="Misi.TCombobox")
        pilihan.pack(side="left", padx=(0, 8))
        pilihan.bind("<<ComboboxSelected>>", self.peta_contoh)
        ttk.Button(alat_peta, text="Peta Contoh", command=self.peta_contoh,
                   style="Misi.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(alat_peta, text="Acak Peta", command=self.acak_peta,
                   style="Utama.Misi.TButton").pack(side="left")

        isi = tk.Frame(root, bg=self.LATAR)
        isi.grid(row=1, column=0, sticky="nsew", padx=18, pady=(14, 10))
        isi.columnconfigure(0, weight=1)
        isi.rowconfigure(0, weight=1)
        panel_peta = tk.Frame(isi, bg=self.PANEL, padx=12, pady=10,
                              highlightthickness=1, highlightbackground=self.GARIS)
        panel_peta.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        kepala_peta = tk.Frame(panel_peta, bg=self.PANEL)
        kepala_peta.pack(fill="x", pady=(0, 8))
        tk.Label(kepala_peta, text="Peta misi", fg=self.TINTA, bg=self.PANEL,
                 font=("TkDefaultFont", 12, "bold")).pack(side="left")
        tk.Label(kepala_peta, textvariable=self.teks_peta, fg=self.REDUP,
                 bg=self.PANEL).pack(side="right")
        self.kanvas = tk.Canvas(panel_peta, bg=self.KANVAS, highlightthickness=1,
                                highlightbackground=self.GARIS, width=480, height=360)
        self.kanvas.pack(fill="both", expand=True, pady=(0, 8))
        self.kanvas.bind("<Configure>", self.gambar_peta)
        self.kanvas.bind("<Button-1>", self.klik_peta)
        legenda = tk.Frame(panel_peta, bg=self.PANEL)
        legenda.pack(fill="x")
        for teks, warna in (
            ("Rute aktif", self.AKTIF), ("Rute lama (putus-putus)", self.LAMA),
            ("Jejak robot", self.JEJAK),
        ):
            tk.Label(legenda, text=teks, fg=warna, bg=self.PANEL,
                     font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=(0, 12))
        tk.Label(panel_peta, text="R: robot  ·  P: pos  ·  K: korban  ·  C: pengisian  ·  X: rintangan",
                 bg=self.PANEL, fg=self.REDUP, font=("TkDefaultFont", 9),
                 anchor="w").pack(fill="x", pady=(4, 1))

        panel = tk.Frame(isi, bg=self.PANEL, padx=16, pady=14,
                         highlightthickness=1, highlightbackground=self.GARIS)
        panel.grid(row=0, column=1, sticky="nsew")
        self._label(tk, panel, "STATUS MISI", kecil=True)
        self.label_status = self._label(tk, panel, variabel=self.teks_status,
                                        ukuran=15, tebal=True, bawah=12)
        self._label(tk, panel, "ENERGI ROBOT", kecil=True)
        self._label(tk, panel, variabel=self.teks_energi, ukuran=19, tebal=True, bawah=3)
        self.energi_bar = ttk.Progressbar(panel, maximum=KAPASITAS_ENERGI,
                                         style="Energi.Horizontal.TProgressbar")
        self.energi_bar.pack(fill="x", pady=(0, 9))
        self._label(tk, panel, variabel=self.teks_ringkas, bawah=12)
        self._label(tk, panel, "KORBAN", kecil=True)
        self._label(tk, panel, variabel=self.teks_korban, bawah=12)
        self._label(tk, panel, "AKSI TERAKHIR", kecil=True)
        self._label(tk, panel, variabel=self.teks_info, bawah=0)

        kontrol = tk.Frame(root, bg=self.LATAR)
        kontrol.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        self.btn_mulai = ttk.Button(kontrol, text="Mulai", command=self.mulai, style="Utama.Misi.TButton")
        self.btn_jeda = ttk.Button(kontrol, text="Jeda", command=self.jeda_lanjut, style="Misi.TButton")
        self.btn_langkah = ttk.Button(kontrol, text="Langkah", command=self.langkah, style="Misi.TButton")
        self.btn_rintangan = ttk.Button(kontrol, text="Tambah Rintangan", command=self.pilih_rintangan,
                                        style="Misi.TButton")
        btn_reset = ttk.Button(kontrol, text="Reset", command=self.reset, style="Misi.TButton")
        for tombol in (self.btn_mulai, self.btn_jeda, self.btn_langkah, self.btn_rintangan, btn_reset):
            tombol.pack(side="left", padx=(0, 8))
        self.perbarui()

    def _label(self, tk, panel, teks="", variabel=None, ukuran=10, tebal=False, kecil=False, bawah=4):
        label = tk.Label(
            panel, text=teks, textvariable=variabel, bg=self.PANEL,
            fg=self.REDUP if kecil else self.TINTA, anchor="w", justify="left",
            wraplength=250, width=32 if ukuran == 10 else 0,
            font=("TkDefaultFont", 9 if kecil else ukuran, "bold" if tebal or kecil else "normal"),
        )
        label.pack(fill="x", anchor="w", pady=(0, bawah))
        return label

    def perbarui(self) -> None:
        sesi = self.sesi
        kondisi = sesi.kondisi
        status = {"siap": "Siap", "selesai": "Misi selesai", "buntu": "Misi berhenti"}.get(
            sesi.status, "Berjalan" if self.otomatis else "Dijeda"
        )
        self.teks_status.set(status)
        self.label_status.configure(fg={
            "Misi selesai": self.AKTIF, "Misi berhenti": "#ffa59c", "Dijeda": self.LAMA,
        }.get(status, self.TINTA))
        ukuran = self.nama_peta.get().replace("x", "×")
        self.teks_peta.set(f"{ukuran}  ·  {self.jenis_peta}")
        self.teks_energi.set(f"{kondisi.energi} / {KAPASITAS_ENERGI}")
        gaya_energi = "EnergiRendah" if kondisi.energi <= 3 else "Energi"
        self.energi_bar.configure(value=kondisi.energi,
                                  style=f"{gaya_energi}.Horizontal.TProgressbar")
        estimasi = "-" if sesi.biaya_rencana is None else str(sesi.biaya_rencana)
        self.teks_ringkas.set(
            f"Posisi: {kondisi.posisi}\nBiaya terpakai: {sesi.biaya}  |  Rencana: {estimasi}\n"
            f"Pencarian ulang: {sesi.pencarian_ulang}"
        )
        nama = label_lokasi(sesi.peta.korban, "K")
        self.teks_korban.set("\n".join(
            f"{nama[p]}  ·  {'Ditangani' if p in kondisi.korban_ditangani else 'Menunggu'}"
            for p in sorted(nama)
        ))
        self.teks_info.set(self.info)
        berjalan = sesi.status == "berjalan"
        self.btn_mulai.configure(state="normal" if sesi.status == "siap" else "disabled")
        self.btn_jeda.configure(text="Jeda" if self.otomatis else "Lanjut",
                                state="normal" if berjalan and not self.memilih else "disabled")
        bisa_langkah = sesi.status in ("siap", "berjalan") and not (self.otomatis or self.memilih)
        self.btn_langkah.configure(state="normal" if bisa_langkah else "disabled")
        self.btn_rintangan.configure(text="Batal Pilih" if self.memilih else "Tambah Rintangan",
                                     state="normal" if berjalan else "disabled")
        self.kanvas.configure(cursor="crosshair" if self.memilih else "arrow")
        self.gambar_peta()

    def gambar_peta(self, _event=None) -> None:
        kanvas = self.kanvas
        w, h = kanvas.winfo_width(), kanvas.winfo_height()
        peta, kondisi = self.sesi.peta, self.sesi.kondisi
        baris, kolom = len(peta.petak), len(peta.petak[0])
        ukuran = min((w - 46) // kolom, (h - 34) // baris)
        kanvas.delete("all")
        self.geometri_peta = None
        if ukuran < 4:
            return
        x0 = (w - kolom * ukuran + 18) / 2
        y0 = (h - baris * ukuran + 16) / 2
        self.geometri_peta = (x0, y0, ukuran, baris, kolom)

        def kotak(posisi):
            b, k = posisi
            return x0 + (k - 1) * ukuran, y0 + (b - 1) * ukuran

        def pusat(posisi):
            x, y = kotak(posisi)
            return x + ukuran / 2, y + ukuran / 2

        warna_petak = {
            ".": ("#1b2b40", "#283c55"),
            "X": ("#30415a", "#42536a"),
            "P": ("#312b52", "#7c6bc4"),
            "K": ("#473323", "#966337"),
            "C": ("#173e54", "#397ca1"),
        }
        label = label_lokasi(peta.korban, "K")
        label.update(label_lokasi(peta.stasiun, "C"))
        label[peta.pos] = "P"
        for b, isi_baris in enumerate(peta.petak, 1):
            kanvas.create_text(x0 - 12, y0 + (b - 0.5) * ukuran, text=b, fill=self.REDUP)
            for k, simbol in enumerate(isi_baris, 1):
                posisi = (b, k)
                x, y = kotak(posisi)
                warna, tepi = warna_petak[simbol]
                if posisi in kondisi.korban_ditangani:
                    warna, tepi = "#143d36", "#339078"
                if posisi in self.sesi.rintangan_baru:
                    warna, tepi = "#63382f", "#e08c6a"
                kanvas.create_rectangle(x + 2, y + 2, x + ukuran - 2, y + ukuran - 2,
                                         fill=warna, outline=tepi)
                if simbol == "X" and posisi not in self.sesi.rintangan_baru:
                    cx, cy = pusat(posisi)
                    kanvas.create_text(cx, cy, text="X", fill="#a6b4c6",
                                       font=("TkDefaultFont", 9, "bold"))
        for k in range(1, kolom + 1):
            kanvas.create_text(x0 + (k - 0.5) * ukuran, y0 - 12, text=k, fill=self.REDUP)

        for lintasan, warna, lebar, putus in (
            (self.sesi.jejak, self.JEJAK, 2, None),
            (self.sesi.rute_lama, self.LAMA, 7, (6, 5)),
            (self.sesi.rute_aktif(), self.AKTIF, 4, None),
        ):
            if len(lintasan) > 1:
                koordinat = [v for posisi in lintasan for v in pusat(posisi)]
                opsi = {"dash": putus} if putus else {}
                kanvas.create_line(*koordinat, fill=warna, width=lebar,
                                   capstyle="round", joinstyle="round", **opsi)

        for posisi, nama in label.items():
            x, y = kotak(posisi)
            warna = {"K": self.LAMA, "P": "#ddd2ff", "C": "#a6dfff"}[nama[0]]
            if posisi in kondisi.korban_ditangani:
                warna = self.AKTIF
            ukuran_label = max(8, min(13, ukuran // 4))
            kanvas.create_text(x + 5, y + 4, anchor="nw", text=nama, fill=warna,
                               font=("TkDefaultFont", -ukuran_label, "bold"))
        for posisi in self.sesi.rintangan_baru:
            x, y = pusat(posisi)
            kanvas.create_text(x, y, text="X", fill="#ffba9c", font=("TkDefaultFont", 12, "bold"))

        if self.memilih:
            rute = self.sesi.rute_aktif()
            if len(rute) > 1 and peta.simbol(rute[1]) == ".":
                x, y = kotak(rute[1])
                kanvas.create_rectangle(x + 3, y + 3, x + ukuran - 3, y + ukuran - 3,
                                         outline=self.LAMA, dash=(4, 2), width=2)
        x, y = pusat(kondisi.posisi)
        radius = ukuran * 0.27
        kanvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                           fill=self.AKTIF, outline="#bbfbe1", width=2)
        kanvas.create_text(x, y, text="R", fill="#09261d",
                           font=("TkDefaultFont", -max(9, min(16, ukuran // 3)), "bold"))

    def _berhenti_otomatis(self) -> None:
        self.otomatis = False
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None

    def _jadwalkan(self) -> None:
        if self.otomatis and self.timer is None:
            self.timer = self.root.after(420, self._putar)

    def _putar(self) -> None:
        self.timer = None
        if not self.otomatis:
            return
        self.info = self.sesi.langkah()
        if self.sesi.status != "berjalan":
            self._berhenti_otomatis()
        self.perbarui()
        self._jadwalkan()

    def mulai(self) -> None:
        if self.sesi.status != "siap":
            return
        self.otomatis = self.sesi.mulai() and self.sesi.status == "berjalan"
        self.info = ("Rute ditemukan. Robot mulai bergerak." if self.otomatis
                     else "Tidak ada rute yang bisa menyelesaikan misi.")
        self.perbarui()
        self._jadwalkan()

    def jeda_lanjut(self) -> None:
        if self.sesi.status != "berjalan" or self.memilih:
            return
        if self.otomatis:
            self._berhenti_otomatis()
            self.info = "Misi dijeda. Kamu bisa menambah rintangan atau maju satu langkah."
        else:
            self.otomatis = True
            self.info = "Robot melanjutkan rute aktif."
            self._jadwalkan()
        self.perbarui()

    def langkah(self) -> None:
        if self.otomatis or self.memilih or self.sesi.status not in ("siap", "berjalan"):
            return
        self.info = (self.sesi.langkah() if self.sesi.mulai()
                     else "Tidak ada rute yang bisa menyelesaikan misi.")
        self.perbarui()

    def pilih_rintangan(self) -> None:
        if self.sesi.status != "berjalan":
            return
        self._berhenti_otomatis()
        self.memilih = not self.memilih
        self.info = ("Klik petak kosong di peta. Pilih petak pada rute hijau agar A* mencari ulang."
                     if self.memilih else "Pemilihan rintangan dibatalkan. Misi masih dijeda.")
        self.perbarui()

    def klik_peta(self, event) -> None:
        if not self.memilih or self.geometri_peta is None:
            return
        x0, y0, ukuran, baris, kolom = self.geometri_peta
        b = int((event.y - y0) // ukuran) + 1
        k = int((event.x - x0) // ukuran) + 1
        if not (1 <= b <= baris and 1 <= k <= kolom):
            return
        try:
            self.info = self.sesi.tambah_rintangan((b, k))
        except ValueError as pesan:
            self.info = f"{pesan} Pilih petak kosong lain."
        else:
            self.memilih = False
        self.perbarui()

    def _reset_misi(self, pesan: str) -> None:
        self._berhenti_otomatis()
        self.memilih = False
        self.sesi = SesiMisi(self.peta_awal)
        self.info = pesan
        self.perbarui()

    def reset(self) -> None:
        self._reset_misi("Misi direset. Susunan peta tetap sama.")

    def peta_contoh(self, _event=None) -> None:
        self.peta_awal = PETA_CONTOH[self.nama_peta.get()]
        self.jenis_peta = "Peta contoh"
        self._reset_misi("Peta contoh siap. Tekan Mulai atau Langkah.")

    def acak_peta(self) -> None:
        self._berhenti_otomatis()
        self.memilih = False
        peta = buat_peta_acak(PETA_CONTOH[self.nama_peta.get()], self.peta_awal)
        if peta is None:
            self.info = "Belum menemukan peta acak yang layak. Klik Acak Peta untuk mencoba lagi."
            self.perbarui()
            return
        self.peta_awal = peta
        self.jenis_peta = "Peta acak"
        self._reset_misi("Peta acak sudah diuji oleh A*. Tekan Mulai atau Langkah.")

    def tutup(self) -> None:
        self._berhenti_otomatis()
        self.root.destroy()


def jalankan_gui(nama_peta: str) -> int:
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError:
        print("Tkinter belum tersedia pada instalasi Python ini.")
        return 1
    try:
        root = tk.Tk()
    except tk.TclError:
        print("Jendela Tkinter tidak bisa dibuka. Jalankan dari terminal di desktop.")
        return 1
    TampilanMisi(root, tk, ttk, nama_peta)
    root.mainloop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulasi misi robot penyelamat.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--manual", action="store_true", help="kendalikan robot dari terminal")
    mode.add_argument("--astar", action="store_true", help="cari dan simulasikan rute dengan A*")
    mode.add_argument("--dinamis", action="store_true", help="demo perubahan rute di tengah misi")
    mode.add_argument("--gui", action="store_true", help="buka tampilan simulasi Tkinter")
    parser.add_argument(
        "--peta", choices=PETA_CONTOH, help="pilih ukuran peta (6x6; GUI dan dinamis: 8x8)"
    )
    parser.add_argument(
        "--rintangan", nargs=2, type=int, metavar=("BARIS", "KOLOM"),
        help="lokasi rintangan baru pada mode dinamis (bawaan: 2 5)",
    )
    args = parser.parse_args()
    if args.rintangan is not None and not args.dinamis:
        parser.error("--rintangan hanya bisa digunakan bersama --dinamis.")
    nama_peta = args.peta or ("8x8" if args.dinamis or args.gui else "6x6")
    if args.gui:
        return jalankan_gui(nama_peta)
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
