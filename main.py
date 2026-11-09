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


# PANDUAN MEMBACA FILE
# Alur utamanya: main() memilih mode -> peta dibaca -> kondisi awal dibuat ->
# A* mencari rencana -> simulasi menjalankan setiap aksi memakai aturan yang sama.
# Urutan bagian: aturan dasar, data peta/robot, rumus A*, peta acak, terminal,
# sesi misi, GUI Tkinter, lalu pemilihan mode dari argumen terminal.
# Tujuan pencarian adalah menangani SEMUA korban dan kembali ke pos dengan
# biaya aksi minimum. Mengunjungi petak korban saja belum berarti menanganinya.

# 1. ATURAN DASAR DAN KOORDINAT
# Energi dan biaya adalah dua hal berbeda: gerak/tangani menghabiskan 1 energi,
# sedangkan isi mengembalikan energi ke 10. Ketiganya tetap berbiaya 1 per aksi.
KAPASITAS_ENERGI = 10
BIAYA_AKSI = 1
# Posisi ditulis (baris, kolom), dimulai dari (1, 1) di kiri atas.
Posisi = Tuple[int, int]
# Nilai arah adalah perubahan (baris, kolom). Tidak ada gerakan diagonal.
ARAH = {
    "atas": (-1, 0),
    "bawah": (1, 0),
    "kiri": (0, -1),
    "kanan": (0, 1),
}
DAFTAR_AKSI = (*ARAH, "tangani", "isi")


# 2. DATA PETA
# frozen=True membuat atribut tidak bisa diganti langsung. Saat peta berubah,
# buat objek pengganti dengan replace(), sehingga peta contoh tetap tersimpan.
@dataclass(frozen=True)
class PetaMisi:
    # petak menyimpan simbol: P=pos, K=korban, C=stasiun, X=rintangan, .=kosong.
    # Koordinat objek disimpan juga agar pemeriksaan lokasi tidak perlu membaca
    # seluruh grid berulang kali. frozenset adalah himpunan yang tidak bisa diubah.
    petak: tuple[str, ...]
    pos: Posisi
    korban: frozenset[Posisi]
    stasiun: frozenset[Posisi]

    @classmethod
    def dari_baris(cls, petak: tuple[str, ...]) -> PetaMisi:
        # Ubah deretan teks menjadi PetaMisi setelah bentuk dan simbolnya valid.
        # Pemeriksaan ini memvalidasi struktur; kelayakan misi diuji oleh A*.
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
        # Batas ini mencegah robot keluar grid dan membatasi lokasi klik GUI.
        baris, kolom = posisi
        return 1 <= baris <= len(self.petak) and 1 <= kolom <= len(self.petak[0])

    def simbol(self, posisi: Posisi) -> str:
        # Koordinat misi mulai dari 1, sedangkan indeks tuple/string mulai dari 0.
        # Pemanggil memastikan posisi berada di dalam peta sebelum membacanya.
        baris, kolom = posisi
        return self.petak[baris - 1][kolom - 1]

    def dengan_rintangan(self, posisi: Posisi) -> PetaMisi:
        """Buat peta baru; hanya petak kosong yang boleh menjadi rintangan."""
        if not self.di_dalam(posisi):
            raise ValueError(f"Petak {posisi} berada di luar peta.")
        if self.simbol(posisi) != ".":
            raise ValueError(f"Petak {posisi} bukan petak kosong.")
        # String tidak bisa diedit per karakter. Sambungkan bagian sebelum dan
        # sesudah petak dengan X, lalu kembalikan salinan peta yang baru.
        # Pos, korban, dan stasiun tidak boleh ditimpa oleh fitur ini.
        baris, kolom = posisi
        petak = list(self.petak)
        lama = petak[baris - 1]
        petak[baris - 1] = lama[:kolom - 1] + "X" + lama[kolom:]
        return replace(self, petak=tuple(petak))


# SUSUNAN DEMO: 6x6 berisi 1 korban dan 1 stasiun; 8x8 serta 10x10
# masing-masing berisi 3 korban dan 3 stasiun. Pos tetap menjadi titik pulang.
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
# Pada rencana awal peta 8x8 dan 10x10, robot melewati petak ini setelah K1
# ditangani. Mode --dinamis memakainya untuk memperlihatkan pencarian ulang.
RINTANGAN_DEMO = (2, 5)


# 3. KONDISI ROBOT DAN ATURAN AKSI
@dataclass(frozen=True)
class KondisiRobot:
    # Inilah satu state/simpul pencarian A*: (posisi, energi, korban_ditangani).
    # Posisi sama dengan energi atau status korban berbeda adalah state berbeda,
    # karena pilihan aksi dan peluang menyelesaikan misinya bisa berbeda.
    # frozen=True dan frozenset membuat state dapat menjadi kunci dictionary A*.
    posisi: Posisi
    energi: int
    korban_ditangani: frozenset[Posisi]


def kondisi_awal(peta: PetaMisi) -> KondisiRobot:
    # Robot mulai di pos, energi penuh, dan belum menangani korban mana pun.
    return KondisiRobot(peta.pos, KAPASITAS_ENERGI, frozenset())


def misi_selesai(peta: PetaMisi, kondisi: KondisiRobot) -> bool:
    # Operator <= pada himpunan berarti semua anggota di kiri ada di kanan.
    # Dua syarat wajib bersamaan: semua korban ditangani DAN robot sudah pulang.
    # Tidak ada syarat energi minimum saat tiba di pos; energi 0 tetap sah.
    return kondisi.posisi == peta.pos and peta.korban <= kondisi.korban_ditangani


def terapkan_aksi(
    peta: PetaMisi, kondisi: KondisiRobot, aksi: str
) -> tuple[KondisiRobot, int, str]:
    """Kembalikan (kondisi hasil, biaya aksi, pesan).

    Aksi yang ditolak mengembalikan kondisi semula dengan biaya nol.
    """
    # Fungsi ini adalah sumber aturan bersama untuk A*, terminal, dan GUI.
    # A* memakainya untuk mencoba calon aksi; simulasi memakainya saat eksekusi.
    # Karena kondisi tidak diubah langsung, mencoba aksi tidak menggerakkan robot.
    if aksi in ARAH:
        # GERAK: harus punya energi, tujuan di dalam grid, dan tujuan bukan X.
        # Petak P/K/C boleh dilewati, tetapi tangani/isi perlu aksi tersendiri.
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
        # TANGANI: hanya sah di korban yang belum ditangani, dengan energi >= 1.
        if kondisi.posisi not in peta.korban:
            return kondisi, 0, "Robot harus berada di lokasi korban (K)."
        if kondisi.posisi in kondisi.korban_ditangani:
            return kondisi, 0, "Korban sudah ditangani."
        if kondisi.energi < 1:
            return kondisi, 0, "Energi tidak cukup untuk menangani korban."
        hasil = replace(
            kondisi,
            energi=kondisi.energi - 1,
            # Gabungan himpunan menambahkan korban ini tanpa menghapus yang lama.
            korban_ditangani=kondisi.korban_ditangani | {kondisi.posisi},
        )
        return hasil, BIAYA_AKSI, "Korban berhasil ditangani."

    if aksi == "isi":
        # ISI: hanya di stasiun dan saat energi belum penuh. Tidak memerlukan
        # energi awal, tetapi tetap menambah biaya aksi walau robot tidak pindah.
        if kondisi.posisi not in peta.stasiun:
            return kondisi, 0, "Robot harus berada di tempat pengisian (C)."
        if kondisi.energi >= KAPASITAS_ENERGI:
            return kondisi, 0, "Energi sudah penuh."
        # Fasilitas di C tetap bisa mengisi robot yang energinya nol.
        hasil = replace(kondisi, energi=KAPASITAS_ENERGI)
        return hasil, BIAYA_AKSI, "Energi diisi sampai penuh."

    return kondisi, 0, "Aksi tidak dikenal."


# 4. RUMUS HEURISTIK DAN ALGORITMA A*
def manhattan(awal: Posisi, tujuan: Posisi) -> int:
    # d(A, B) = |baris_A - baris_B| + |kolom_A - kolom_B|.
    # Contoh (1, 1) ke (3, 4): 2 + 3 = 5 langkah jika tidak ada rintangan.
    # Cocok untuk gerak empat arah; jalan memutar dapat membuat jarak nyata lebih jauh.
    return abs(awal[0] - tujuan[0]) + abs(awal[1] - tujuan[1])


def heuristik(peta: PetaMisi, kondisi: KondisiRobot) -> int:
    """Perkiraan biaya sisa misi tanpa menghitung rintangan atau pengisian."""
    # h adalah perkiraan biaya dari state sekarang sampai misi selesai.
    # Selisih himpunan menyisakan korban yang masih perlu aksi tangani.
    sisa = peta.korban - kondisi.korban_ditangani
    if not sisa:
        # Semua korban selesai: h = d(robot, pos) * biaya per aksi.
        return manhattan(kondisi.posisi, peta.pos) * BIAYA_AKSI
    # Jika masih ada korban, rumus yang dipakai adalah:
    # h = [max_K(d(robot, K) + d(K, pos)) + jumlah_korban_sisa] * BIAYA_AKSI.
    # Setiap misi lengkap wajib melewati setiap K lalu pulang. Karena itu, jarak
    # lewat satu K adalah batas minimum; ambil batas terbesar agar lebih informatif.
    # Jangan jumlahkan jarak lewat semua K karena bagian jalan bisa tumpang tindih
    # dan terhitung berkali-kali. Tambahkan 1 aksi tangani untuk setiap korban sisa.
    batas_gerak = max(
        manhattan(kondisi.posisi, korban) + manhattan(korban, peta.pos)
        for korban in sisa
    )
    # Rintangan, jalan ke stasiun, dan aksi isi sengaja diabaikan dalam h.
    # Akibatnya h tidak melebihi biaya sisa sebenarnya (admissible). Aturan energi
    # tetap diperiksa oleh terapkan_aksi(), jadi rencana harus tetap layak dijalankan.
    return (batas_gerak + len(sisa)) * BIAYA_AKSI


@dataclass(frozen=True)
class RencanaMisi:
    # aksi adalah urutan yang akan dijalankan; biaya menghitung semua aksi sah.
    # diperiksa menghitung state yang diproses, bukan jumlah langkah robot.
    aksi: tuple[str, ...]
    biaya: int
    diperiksa: int


def cari_rencana_astar(peta: PetaMisi, awal: KondisiRobot) -> RencanaMisi | None:
    """Cari rencana berbiaya minimum, atau None jika tidak ada rute layak."""
    # RUMUS UTAMA: f(n) = g(n) + h(n).
    # g(n): biaya nyata dari state awal pencarian sampai state n.
    # h(n): perkiraan minimum biaya dari n sampai semua korban selesai dan pulang.
    # f(n): perkiraan total biaya jika memilih jalur melalui n.
    # Contoh g=7 dan h=5 menghasilkan f=12; A* mendahulukan kandidat dengan f kecil.
    # Pencarian merencanakan seluruh misi, termasuk urutan korban dan waktu isi,
    # bukan hanya mencari jalan ke satu titik tujuan.
    urutan_masuk = count()
    # Heap/antrean prioritas menyimpan (f, nomor_masuk, g, kondisi).
    # heappop mengambil f terkecil. Nomor unik mengatasi f yang sama sehingga
    # Python tidak perlu membandingkan objek KondisiRobot secara langsung.
    # State awal punya g=0, maka f awal sama dengan h awal.
    antrean = [(heuristik(peta, awal), next(urutan_masuk), 0, awal)]
    # Catat g termurah untuk SETIAP state lengkap, bukan hanya koordinatnya.
    biaya_terbaik = {awal: 0}
    # asal mencatat state sebelumnya dan aksi yang membawa kita ke suatu state.
    # Data ini dipakai untuk menyusun kembali rute ketika tujuan tercapai.
    asal: dict[KondisiRobot, tuple[KondisiRobot, str]] = {}
    diperiksa = 0

    while antrean:
        # Ambil kandidat terbaik. Entri lama bisa masih ada di heap walaupun
        # belakangan ditemukan jalur yang lebih murah ke state yang sama.
        _, _, g, kondisi = heappop(antrean)
        if g != biaya_terbaik[kondisi]:
            continue  # Jalur yang lebih murah ke kondisi ini sudah ditemukan.
        diperiksa += 1

        if misi_selesai(peta, kondisi):
            # Tujuan diperiksa saat state diambil dari antrean. Dengan heuristik
            # batas bawah dan pembaruan g di bawah, rencana ini berbiaya minimum.
            # Telusuri asal dari tujuan ke awal, lalu balik agar urutan aksi benar.
            rute = []
            saat_ini = kondisi
            while saat_ini != awal:
                sebelumnya, aksi = asal[saat_ini]
                rute.append(aksi)
                saat_ini = sebelumnya
            return RencanaMisi(tuple(reversed(rute)), g, diperiksa)

        for aksi in DAFTAR_AKSI:
            # Bangkitkan tetangga lewat 4 gerakan, tangani, dan isi. Aksi yang
            # melanggar energi, lokasi, atau rintangan tidak menjadi jalur pencarian.
            kandidat, biaya_aksi, _ = terapkan_aksi(peta, kondisi, aksi)
            if biaya_aksi == 0:
                continue  # Aksi ditolak oleh aturan gerak, energi, atau lokasi.

            g_baru = g + biaya_aksi
            # State yang belum dikenal dianggap memiliki biaya tak terhingga.
            # Simpan kandidat hanya jika lebih murah; jalur seri tidak perlu diulang.
            if g_baru >= biaya_terbaik.get(kandidat, float("inf")):
                continue
            biaya_terbaik[kandidat] = g_baru
            asal[kandidat] = (kondisi, aksi)
            h = heuristik(peta, kandidat)
            # Di sinilah rumus f = g + h diterapkan untuk prioritas kandidat baru.
            f = g_baru + h
            heappush(antrean, (f, next(urutan_masuk), g_baru, kandidat))

    # Semua kandidat habis tanpa mencapai tujuan: misi tidak punya rute yang
    # memenuhi aturan. Jalan yang terhubung saja belum menjamin energi cukup.
    return None


# 5. FITUR ACAK PETA: BANGUN SUSUNAN, LALU UJI KELAYAKAN DENGAN A*
def _jalur_acak(awal: Posisi, akhir: Posisi, rng: Random) -> set[Posisi]:
    """Sisakan jalur terpendek dengan urutan gerakan yang diacak."""
    # Buat gerakan vertikal/horizontal sebanyak selisih koordinat, lalu acak
    # urutannya. Panjang jalur tetap sama dengan Manhattan, bentuknya bisa berbeda.
    # Hasilnya adalah himpunan petak yang harus dilindungi dari rintangan acak.
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
    # acuan menentukan ukuran, posisi pos, serta jumlah korban dan stasiun.
    # peta_lama dipakai agar hasil tidak sama persis dengan susunan sebelumnya.
    # rng dapat diberi Random(seed) agar susunan acak bisa diulang saat pengujian.
    rng = rng if rng is not None else Random()
    baris, kolom = len(acuan.petak), len(acuan.petak[0])
    koordinat = [(b, k) for b in range(1, baris + 1) for k in range(1, kolom + 1)]
    # Perjalanan stasiun -> korban -> stasiun membutuhkan 2*d + 1 energi,
    # termasuk aksi tangani. Jadi d <= floor((10 - 1) / 2) = 4.
    jarak_korban = (KAPASITAS_ENERGI - 1) // 2

    # Coba maksimal 16 susunan; jika semuanya gagal, GUI dapat meminta acak lagi.
    for _ in range(16):
        objek = {acuan.pos: "P"}
        jalur_bebas = {acuan.pos}
        sebelumnya = acuan.pos
        stasiun = []
        # Tahap 1: pos dipertahankan, stasiun diletakkan membentuk rantai.
        # Jarak tiap sambungan dibatasi 2..8 langkah (kapasitas - 2), lalu
        # disediakan jalur bebas agar sambungan bisa ditempuh sekali isi energi.
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
        # Tahap 2: letakkan korban dekat stasiun secara bergiliran dengan i %
        # jumlah_stasiun. Petak objek tidak boleh saling menimpa.
        # Jalur pergi-pulang ke stasiun dilindungi, sehingga tangani juga terjangkau.
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

        # Tahap 3: acak rintangan sekitar 18% luas peta, sebanyak petak tersedia,
        # hanya di luar jalur yang dilindungi. Kemudian susun kembali teks grid.
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
        # Tahap 4: A* menjadi pemeriksaan akhir seluruh misi dengan aturan energi.
        # Peta hanya diterima jika semua korban bisa ditangani dan robot bisa pulang.
        if cari_rencana_astar(peta, kondisi_awal(peta)) is not None:
            return peta
    return None


# 6. TAMPILAN TERMINAL DAN MODE DEMO/MANUAL
def label_lokasi(lokasi: frozenset[Posisi], simbol: str) -> dict[Posisi, str]:
    # Satu lokasi cukup K/C; beberapa lokasi diberi K1, K2 atau C1, C2, dst.
    # sorted menjaga nomor label tetap berdasarkan koordinat, bukan urutan set.
    if len(lokasi) == 1:
        return {next(iter(lokasi)): simbol}
    return {posisi: f"{simbol}{i}" for i, posisi in enumerate(sorted(lokasi), start=1)}


def tampilkan_peta(peta: PetaMisi, kondisi: KondisiRobot) -> None:
    # R hanya menimpa label tampilan pada posisi robot; isi peta tidak berubah.
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
    # Ringkas kemajuan korban untuk dipakai ulang oleh keluaran terminal.
    if len(peta.korban) == 1:
        return "sudah ditangani" if kondisi.korban_ditangani else "belum ditangani"
    label = label_lokasi(peta.korban, "K")
    nama = ", ".join(label[posisi] for posisi in sorted(kondisi.korban_ditangani))
    return f"{len(kondisi.korban_ditangani)}/{len(peta.korban)} ({nama or '-'})"


def tampilkan_kondisi(peta: PetaMisi, kondisi: KondisiRobot, biaya: int) -> None:
    # Biaya dicetak terpisah dari energi: biaya terus naik, energi bisa diisi lagi.
    status = status_korban(peta, kondisi)
    print(
        f"Posisi: {kondisi.posisi} | Energi: {kondisi.energi}/{KAPASITAS_ENERGI}"
        f" | Korban: {status} | Total biaya: {biaya}"
    )


def jalankan_aksi(
    peta: PetaMisi, kondisi: KondisiRobot, biaya: int, aksi: str
) -> tuple[KondisiRobot, int, bool]:
    # Pembungkus aturan aksi untuk terminal: tampilkan perubahan dan akumulasi
    # biaya. Nilai bool menunjukkan apakah aksi benar-benar diterima.
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
    # Demo bawaan memakai daftar aksi yang sudah ditulis, bukan hasil A*.
    # Percobaan menabrak X sengaja disertakan untuk menunjukkan penolakan aksi.
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
    # Input keyboard diterjemahkan ke nama aksi yang sama dengan aksi pada A*.
    # Pemain memilih aksi sendiri; aturan energi dan tujuan misi tetap sama.
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
    # Aksi isi/tangani tidak berpindah petak sehingga tidak menambah titik garis.
    # Hasil dipakai untuk menggambar rute dan mengecek rintangan yang memotongnya.
    baris, kolom = awal
    lintasan = []
    for aksi in aksi_rute:
        if aksi in ARAH:
            db, dk = ARAH[aksi]
            baris, kolom = baris + db, kolom + dk
            lintasan.append((baris, kolom))
    return lintasan


def ringkas_lintasan(lintasan: list[Posisi]) -> str:
    # Batasi tampilan terminal ke lima petak pertama agar rute panjang tetap terbaca.
    potongan = " -> ".join(map(str, lintasan[:5]))
    return potongan + (" -> ..." if len(lintasan) > 5 else "")


# 7. SESI MISI: MENJALANKAN RENCANA DAN MENCARI ULANG SAAT PETA BERUBAH
class SesiMisi:
    """Kondisi simulasi yang diubah satu aksi pada setiap langkah."""

    def __init__(self, peta: PetaMisi) -> None:
        # Sesi menyimpan pelaksanaan nyata, terpisah dari calon state di pencarian.
        # Status: siap -> berjalan -> selesai, atau buntu jika tidak bisa lanjut.
        self.peta = peta
        self.kondisi = kondisi_awal(peta)
        self.biaya = 0
        self.status = "siap"
        # deque adalah antrean aksi tersisa; popleft mengambil aksi paling depan.
        self.aksi: deque[str] = deque()
        # jejak = jalan yang sudah ditempuh; rute_lama = sisa rute sebelum terhalang.
        self.jejak = [self.kondisi.posisi]
        self.rute_lama: list[Posisi] = []
        self.rintangan_baru: set[Posisi] = set()
        self.pencarian_ulang = 0
        self.biaya_rencana: int | None = None

    def _rencanakan(self) -> bool:
        # Awal pencarian adalah kondisi TERAKHIR: posisi, energi, dan korban yang
        # sudah ditangani tetap dipertahankan; robot tidak dikembalikan ke pos.
        rencana = cari_rencana_astar(self.peta, self.kondisi)
        if rencana is None:
            self.aksi.clear()
            self.biaya_rencana = None
            self.status = "buntu"
            return False
        self.aksi = deque(rencana.aksi)
        # g pada pencarian ulang dimulai dari 0 untuk biaya SISA misi saja.
        # Estimasi total misi = biaya yang sudah terpakai + biaya rencana baru.
        self.biaya_rencana = self.biaya + rencana.biaya
        self.status = "selesai" if misi_selesai(self.peta, self.kondisi) else "berjalan"
        return True

    def mulai(self) -> bool:
        # Pencarian awal hanya sekali saat siap; melanjutkan misi memakai rute aktif.
        if self.status == "siap":
            return self._rencanakan()
        return self.status == "berjalan"

    def rute_aktif(self) -> list[Posisi]:
        # Sertakan posisi sekarang supaya garis rute dimulai tepat dari robot.
        return [self.kondisi.posisi] + lintasan_gerak(self.kondisi.posisi, self.aksi)

    def langkah(self) -> str:
        # Satu pemanggilan = satu aksi (bisa gerak, tangani, atau isi).
        # Fungsi ini dipakai tombol Langkah maupun animasi otomatis GUI.
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
            # Jejak hanya bertambah saat bergerak; biaya bertambah untuk semua aksi sah.
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
        # FITUR UBAH PETA SAAT MISI: hanya menambah X di petak kosong, bukan
        # memindahkan P/K/C. Petak tempat robot berdiri juga tidak boleh ditutup.
        if self.status != "berjalan":
            raise ValueError("Mulai misi sebelum menambahkan rintangan.")
        if posisi == self.kondisi.posisi:
            raise ValueError("Robot sedang menempati petak ini.")
        self.peta = self.peta.dengan_rintangan(posisi)
        self.rintangan_baru.add(posisi)
        rute = self.rute_aktif()
        if posisi not in rute:
            # Penambahan X di luar rute tidak membatalkan aksi yang sudah direncanakan.
            return f"Rintangan di {posisi} berada di luar rute. Rencana tetap berlaku."

        self.rute_lama = rute
        self.pencarian_ulang += 1
        # Rute terpotong: simpan garis lama untuk pembanding, lalu jalankan A* lagi.
        # Jika tidak ada alternatif, X tetap terpasang dan status menjadi buntu.
        if not self._rencanakan():
            return f"Rintangan di {posisi}. Misi berhenti karena tidak ada rute alternatif."
        return (
            f"Rintangan di {posisi}. A* menemukan rute baru dari {self.kondisi.posisi}; "
            f"perkiraan total biaya {self.biaya_rencana}."
        )


# 8. EKSEKUSI A* DI TERMINAL, TERMASUK DEMO PETA DINAMIS
def tampilkan_kolom_rute() -> None:
    print(
        f"{'No':>3}  {'Aksi':<8} {'Posisi':<10} {'Energi':>6} "
        f"{'Korban':<16} {'g':>3} {'h':>3} {'f':>3}"
    )


def tampilkan_langkah(
    peta: PetaMisi, nomor: int, aksi: str, kondisi: KondisiRobot, biaya: int
) -> None:
    # Tabel ini menampilkan nilai SETELAH aksi: g adalah biaya total pelaksanaan
    # sejak awal misi, h adalah estimasi sisa, dan f = g + h untuk baris tersebut.
    # Saat pencarian ulang, g internal A* dihitung lagi dari 0 untuk sisa rencana.
    h = heuristik(peta, kondisi)
    status = status_korban(peta, kondisi)
    print(
        f"{nomor:>3}  {aksi:<8} {str(kondisi.posisi):<10} {kondisi.energi:>6} "
        f"{status:<16} {biaya:>3} {h:>3} {biaya + h:>3}"
    )


def jalankan_astar(peta: PetaMisi, rintangan_baru: Posisi | None = None) -> int:
    # Tanpa rintangan_baru, cukup cari lalu jalankan rencana sampai selesai.
    # Jika ada, siapkan peta pengganti untuk diaktifkan setelah tangani pertama.
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
        # Jalankan rencana dengan aturan yang sama seperti saat pencarian.
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
        # Seperti SesiMisi, pencarian memakai kondisi terkini dan peta yang berubah.
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
    # Pastikan biaya eksekusi sesuai rencana terakhir dan tujuan benar-benar tercapai.
    if biaya != biaya_target or not misi_selesai(peta, kondisi):
        print("Simulasi tidak menghasilkan kondisi akhir yang direncanakan.")
        return 1
    print("MISI SELESAI: semua korban ditangani dan robot kembali ke pos.")
    return 0


# 9. GUI TKINTER: MENAMPILKAN SESI DAN MENGHUBUNGKAN TOMBOL KE AKSI
# Perhitungan misi tetap berada di fungsi aturan/A* dan SesiMisi. Kelas ini
# mengatur tampilan, input klik, dan kapan satu langkah simulasi dijalankan.
class TampilanMisi:
    # Palet tampilan: hijau untuk rute aktif, kuning untuk rute lama, abu untuk jejak.
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
        # peta_awal adalah susunan dasar untuk Reset; sesi.peta bisa berbeda jika
        # pengguna menambahkan rintangan saat misi. Keduanya dipisah agar bisa reset.
        self.peta_awal = PETA_CONTOH[nama_peta]
        self.jenis_peta = "Peta contoh"
        self.sesi = SesiMisi(self.peta_awal)
        # otomatis mengatur animasi; memilih menandai mode klik tambah rintangan.
        # Jeda hanya menghentikan animasi, tidak menghapus kondisi/rencana sesi.
        self.otomatis = False
        self.memilih = False
        self.timer = None
        self.geometri_peta = None
        self.info = "Tekan Mulai untuk berjalan otomatis atau Langkah untuk maju satu aksi."
        # StringVar menghubungkan teks widget dengan data yang diperbarui lewat set().
        self.nama_peta = tk.StringVar(root, value=nama_peta)
        self.teks_peta = tk.StringVar(root)
        self.teks_status = tk.StringVar(root)
        self.teks_energi = tk.StringVar(root)
        self.teks_ringkas = tk.StringVar(root)
        self.teks_korban = tk.StringVar(root)
        self.teks_info = tk.StringVar(root)

        # Siapkan jendela dan atur area tengah agar membesar saat jendela diperlebar.
        root.title("Robot Penyelamat | Simulasi A*")
        root.geometry("1080x720")
        root.minsize(850, 640)
        root.configure(bg=self.LATAR)
        root.protocol("WM_DELETE_WINDOW", self.tutup)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        # Gaya widget dan warna energi rendah hanya mengubah tampilan.
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

        # Bagian atas: judul, pilihan ukuran, Peta Contoh, dan Acak Peta.
        # Memilih ukuran memanggil peta_contoh; tombol acak memakai ukuran terpilih.
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

        # Bagian tengah: kanvas peta di kiri dan informasi misi di kanan.
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
        # Configure menggambar ulang saat ukuran berubah; Button-1 menangani klik kiri.
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

        # Bagian bawah: command menunjuk fungsi yang dijalankan saat tombol ditekan.
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
        # Pembantu untuk membuat label panel dengan gaya dan jarak yang konsisten.
        label = tk.Label(
            panel, text=teks, textvariable=variabel, bg=self.PANEL,
            fg=self.REDUP if kecil else self.TINTA, anchor="w", justify="left",
            wraplength=250, width=32 if ukuran == 10 else 0,
            font=("TkDefaultFont", 9 if kecil else ukuran, "bold" if tebal or kecil else "normal"),
        )
        label.pack(fill="x", anchor="w", pady=(0, bawah))
        return label

    def perbarui(self) -> None:
        # Sinkronkan status, energi, biaya, korban, dan tombol dengan sesi terkini.
        # Fungsi ini menggambar keadaan sekarang; tidak menjalankan aksi robot.
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
        # Tombol aktif sesuai keadaan: Langkah hanya saat animasi berhenti dan
        # tidak sedang memilih rintangan; Mulai hanya ketika sesi masih siap.
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
        # Ubah koordinat grid menjadi piksel kanvas. Ukuran sel mengambil batas
        # terkecil dari lebar/tinggi yang tersedia supaya petak tetap persegi.
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
            # Titik kiri atas sel; x mengikuti kolom dan y mengikuti baris.
            b, k = posisi
            return x0 + (k - 1) * ukuran, y0 + (b - 1) * ukuran

        def pusat(posisi):
            # Pusat sel menjadi titik sambungan garis rute dan posisi lingkaran robot.
            x, y = kotak(posisi)
            return x + ukuran / 2, y + ukuran / 2

        # Lapisan pertama adalah petak. Korban tertangani dan rintangan baru
        # mendapat warna khusus, tetapi simbol dasar peta tetap dibaca dari sesi.
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

        # Lapisan kedua: jejak yang sudah ditempuh, sisa rute lama putus-putus,
        # lalu sisa rute aktif. Garis ini memvisualisasikan hasil, bukan mencari rute.
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

        # Lapisan terakhir: label objek dan robot agar tetap terlihat di atas garis.
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
            # Sorot petak gerak berikutnya jika kosong sebagai contoh lokasi yang
            # bisa memotong rute. Pengguna tetap boleh memilih petak kosong lain.
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
        # Batalkan callback yang masih menunggu supaya robot tidak bergerak lagi
        # setelah Jeda, Reset, ganti peta, atau tutup jendela.
        self.otomatis = False
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None

    def _jadwalkan(self) -> None:
        # after menjadwalkan satu aksi 420 milidetik lagi tanpa memblokir event loop.
        # Hanya satu timer boleh menunggu, supaya tidak ada animasi ganda.
        if self.otomatis and self.timer is None:
            self.timer = self.root.after(420, self._putar)

    def _putar(self) -> None:
        # Callback timer: kosongkan penanda timer, jalankan satu aksi, perbarui
        # layar, lalu jadwalkan aksi selanjutnya selama misi masih berjalan.
        self.timer = None
        if not self.otomatis:
            return
        self.info = self.sesi.langkah()
        if self.sesi.status != "berjalan":
            self._berhenti_otomatis()
        self.perbarui()
        self._jadwalkan()

    def mulai(self) -> None:
        # Tombol Mulai meminta rencana awal dari sesi, lalu menyalakan animasi.
        if self.sesi.status != "siap":
            return
        self.otomatis = self.sesi.mulai() and self.sesi.status == "berjalan"
        self.info = ("Rute ditemukan. Robot mulai bergerak." if self.otomatis
                     else "Tidak ada rute yang bisa menyelesaikan misi.")
        self.perbarui()
        self._jadwalkan()

    def jeda_lanjut(self) -> None:
        # Jeda tidak mengubah status sesi menjadi siap. Lanjut memakai antrean
        # aksi yang tersisa, tanpa mengulang misi atau mengisi energi secara otomatis.
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
        # Tombol Langkah juga bisa membuat rencana pertama jika sesi masih siap,
        # kemudian menjalankan tepat satu aksi tanpa menyalakan animasi.
        if self.otomatis or self.memilih or self.sesi.status not in ("siap", "berjalan"):
            return
        self.info = (self.sesi.langkah() if self.sesi.mulai()
                     else "Tidak ada rute yang bisa menyelesaikan misi.")
        self.perbarui()

    def pilih_rintangan(self) -> None:
        # FITUR TAMBAH RINTANGAN: hentikan animasi agar posisi robot tidak berubah
        # saat pengguna memilih petak. Menekan tombol lagi membatalkan mode pilih.
        if self.sesi.status != "berjalan":
            return
        self._berhenti_otomatis()
        self.memilih = not self.memilih
        self.info = ("Klik petak kosong di peta. Pilih petak pada rute hijau agar A* mencari ulang."
                     if self.memilih else "Pemilihan rintangan dibatalkan. Misi masih dijeda.")
        self.perbarui()

    def klik_peta(self, event) -> None:
        # Klik biasa diabaikan; pengeditan hanya aktif setelah Tambah Rintangan.
        if not self.memilih or self.geometri_peta is None:
            return
        x0, y0, ukuran, baris, kolom = self.geometri_peta
        # Konversi piksel klik ke (baris, kolom): kurangi offset gambar, bagi ukuran
        # sel dengan //, lalu tambah 1 karena koordinat misi tidak dimulai dari 0.
        b = int((event.y - y0) // ukuran) + 1
        k = int((event.x - x0) // ukuran) + 1
        if not (1 <= b <= baris and 1 <= k <= kolom):
            return
        try:
            # Sesi memeriksa petak dan mencari ulang jika X memotong rute aktif.
            # Jika petak tidak sah, tampilkan alasan dan tetap di mode pilih.
            self.info = self.sesi.tambah_rintangan((b, k))
        except ValueError as pesan:
            self.info = f"{pesan} Pilih petak kosong lain."
        else:
            # Setelah penambahan berhasil, misi tetap dijeda sampai Lanjut/Langkah.
            self.memilih = False
        self.perbarui()

    def _reset_misi(self, pesan: str) -> None:
        # Pembantu bersama untuk Reset dan pergantian peta: batalkan timer lama,
        # buat sesi baru dari peta_awal, dan perbarui tampilan. Energi kembali 10,
        # biaya 0, korban belum ditangani, serta jejak/rute/rintangan tambahan kosong.
        self._berhenti_otomatis()
        self.memilih = False
        self.sesi = SesiMisi(self.peta_awal)
        self.info = pesan
        self.perbarui()

    def reset(self) -> None:
        # RESET memakai susunan dasar terakhir, termasuk jika hasil Acak Peta.
        # Rintangan tambahan saat misi dibuang karena hanya tersimpan di sesi lama.
        self._reset_misi("Misi direset. Susunan peta tetap sama.")

    def peta_contoh(self, _event=None) -> None:
        # PETA CONTOH (juga saat ganti ukuran): ambil susunan demo yang tersimpan
        # di PETA_CONTOH dan mulai sesi baru, sehingga susunan acak sebelumnya diganti.
        self.peta_awal = PETA_CONTOH[self.nama_peta.get()]
        self.jenis_peta = "Peta contoh"
        self._reset_misi("Peta contoh siap. Tekan Mulai atau Langkah.")

    def acak_peta(self) -> None:
        # ACAK PETA membuat misi baru pada ukuran terpilih. Pos dan jumlah objek
        # mengikuti acuan; lokasi korban, stasiun, serta rintangan diacak.
        # Validasi A* berlangsung sebelum hasil dipasang sebagai peta_awal baru.
        self._berhenti_otomatis()
        self.memilih = False
        peta = buat_peta_acak(PETA_CONTOH[self.nama_peta.get()], self.peta_awal)
        if peta is None:
            # Jika gagal menemukan susunan layak, sesi lama tetap ada dalam keadaan
            # dijeda. Pengguna bisa mencoba acak lagi atau melanjutkan misi lama.
            self.info = "Belum menemukan peta acak yang layak. Klik Acak Peta untuk mencoba lagi."
            self.perbarui()
            return
        self.peta_awal = peta
        self.jenis_peta = "Peta acak"
        self._reset_misi("Peta acak sudah diuji oleh A*. Tekan Mulai atau Langkah.")

    def tutup(self) -> None:
        # Hentikan timer sebelum menghancurkan widget agar callback tidak tertinggal.
        self._berhenti_otomatis()
        self.root.destroy()


# 10. MENJALANKAN JENDELA DAN MEMILIH MODE PROGRAM
def jalankan_gui(nama_peta: str) -> int:
    # Tkinter baru diimpor saat mode GUI dipilih; mode terminal tidak memerlukannya.
    # Pisahkan kegagalan modul dan kegagalan membuka jendela agar pesannya jelas.
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
    # Event loop menunggu klik, resize, dan timer sampai jendela ditutup.
    root.mainloop()
    return 0


def main() -> int:
    # argparse membaca opsi terminal. Grup mutually exclusive memastikan hanya
    # satu mode (--manual/--astar/--dinamis/--gui) dipilih dalam satu perintah.
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
    # Ukuran bawaan: GUI/dinamis memakai 8x8, mode lain memakai 6x6.
    # --rintangan BARIS KOLOM khusus demo dinamis; penambahan lewat GUI memakai klik.
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
    # Tanpa opsi, jalankan demo 6x6 dengan urutan aksi tetap dari contoh PPT.
    return jalankan_demo()


if __name__ == "__main__":
    # Jalankan main hanya saat file dieksekusi langsung, bukan saat diimpor.
    # Kode keluar 0 berarti berhasil; nilai lain menunjukkan kendala/argumen salah.
    raise SystemExit(main())
