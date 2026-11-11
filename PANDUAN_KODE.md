# Panduan lokasi kode penting

Panduan ini membantu menjelaskan proyek **Perencanaan Misi Robot Penyelamat dengan Keterbatasan Energi Menggunakan Algoritma A*** kepada dosen.

Klik nomor baris pada tabel untuk membuka `main.py` lokal pada bagian kode yang dimaksud. Buka panduan ini melalui editor yang mendukung tautan ke baris kode dengan penanda `#L`, seperti pratinjau Markdown di VS Code.

Nomor baris mengacu pada `main.py` di proyek ini. Tautan memakai path relatif sehingga tetap berlaku jika folder proyek dipindahkan. Jika susunan kode berubah, perbarui nomor baris pada tautannya.

## 1. Data, aturan, dan perencanaan misi

| Bagian | Baris (klik untuk membuka kode) | Penjelasan |
|---|---|---|
| Kapasitas energi dan daftar aksi | [34–45](main.py#L34-L45) | Menentukan energi maksimum 10, biaya setiap aksi 1, dan empat arah gerakan. |
| `PetaMisi` | [51–104](main.py#L51-L104) | Menyimpan grid serta lokasi pos, korban, dan stasiun. Memvalidasi bentuk peta dan membuat peta dengan rintangan tambahan. |
| `PETA_CONTOH` | [109–140](main.py#L109-L140) | Menyimpan susunan demo ukuran 6×6, 8×8, dan 10×10. |
| **`KondisiRobot`: penyimpanan state** | [147–155](main.py#L147-L155) | Satu state terdiri dari posisi, sisa energi, dan korban yang sudah ditangani. Posisi sama dengan energi atau status korban berbeda merupakan state berbeda. |
| `kondisi_awal()` | [158–160](main.py#L158-L160) | Membuat state awal: robot di pos, energi penuh, dan belum menangani korban. |
| `misi_selesai()` | [163–167](main.py#L163-L167) | Memeriksa dua syarat sekaligus: semua korban sudah ditangani dan robot kembali ke pos. |
| `terapkan_aksi()` | [170–222](main.py#L170-L222) | Memeriksa dan menerapkan aturan gerak, tangani, serta isi energi. Aksi tidak sah ditolak tanpa tambahan biaya. Dipakai bersama oleh pencarian dan simulasi. |
| `manhattan()` | [226–230](main.py#L226-L230) | Menghitung jarak dari selisih baris dan kolom untuk gerakan empat arah. |
| **`heuristik()`: perhitungan h** | [233–254](main.py#L233-L254) | Memperkirakan biaya sisa dari jarak Manhattan dan jumlah korban yang belum ditangani, tanpa menghitung rintangan atau pengisian. |
| **`RencanaMisi`: hasil perencanaan** | [257–263](main.py#L257-L263) | Menyimpan urutan aksi hasil A*, biaya rencana, dan jumlah state yang diperiksa. |
| **`cari_rencana_astar()`** | [266–329](main.py#L266-L329) | Mencari rencana seluruh misi berbiaya minimum dengan mempertimbangkan posisi, energi, dan status korban. |
| `_jalur_acak()` | [333–347](main.py#L333-L347) | Membentuk jalur Manhattan dengan urutan gerak acak; petaknya dilindungi dari rintangan saat membuat peta acak. |
| `buat_peta_acak()` | [350–421](main.py#L350-L421) | Mengacak korban, stasiun, dan rintangan sesuai ukuran serta jumlah objek acuan. Pos dipertahankan. Peta diterima setelah A* membuktikan misi dapat diselesaikan. |

## 2. Bagian inti algoritma A*

Rumus prioritasnya adalah **f(n) = g(n) + h(n)**. Nilai g adalah biaya dari awal pencarian sampai kondisi sekarang, sedangkan h memperkirakan biaya sisa misi. Antrean mendahulukan kandidat dengan f terkecil.

| Proses | Baris (klik untuk membuka kode) |
|---|---|
| Penjelasan rumus f = g + h | [268–274](main.py#L268-L274) |
| Antrean prioritas, biaya terbaik, dan catatan asal state | [275–285](main.py#L275-L285) |
| Mengambil kandidat dengan prioritas terkecil dan melewati entri yang sudah kalah murah | [288–294](main.py#L288-L294) |
| Memeriksa tujuan dan menyusun kembali urutan aksi | [296–306](main.py#L296-L306) |
| Mencoba aksi dan menolak aksi tidak sah | [308–313](main.py#L308-L313) |
| Menghitung g baru dan menyimpan jalur yang lebih murah | [315–321](main.py#L315-L321) |
| Menghitung h dan f, lalu memasukkan kandidat ke antrean | [322–325](main.py#L322-L325) |
| Mengembalikan None jika tidak ada rencana layak | [327–329](main.py#L327-L329) |

Heuristik memakai jarak pulang ke pos jika semua korban selesai. Jika masih ada korban, rumusnya adalah **[max_K(d(robot, K) + d(K, pos)) + jumlah korban sisa] × biaya aksi**, dengan K sebagai korban yang belum ditangani. Perkiraan ini merupakan batas bawah; kelayakan energi tetap diperiksa melalui `terapkan_aksi()`.

## 3. Penyimpanan dan pelaksanaan simulasi

| Bagian | Baris (klik untuk membuka kode) | Fungsi |
|---|---|---|
| **`SesiMisi.__init__()`** | [585–599](main.py#L585-L599) | Menyimpan kondisi robot saat ini, biaya terpakai, status, antrean aksi tersisa, jejak, rute lama, rintangan baru, dan jumlah pencarian ulang. |
| **`SesiMisi._rencanakan()`** | [601–615](main.py#L601-L615) | Memanggil A* dari kondisi saat ini, menyimpan rencana dalam deque, dan menghitung estimasi total biaya. |
| `SesiMisi.mulai()` | [617–621](main.py#L617-L621) | Memulai pencarian jika sesi masih siap; sesi yang sudah berjalan memakai rencana aktif. |
| `SesiMisi.rute_aktif()` | [623–625](main.py#L623-L625) | Menghasilkan posisi sekarang beserta lintasan yang masih akan dilalui robot. |
| **`SesiMisi.langkah()`** | [627–655](main.py#L627-L655) | Mengambil satu aksi dari antrean, menerapkannya, memperbarui state dan biaya, lalu memeriksa tujuan. |
| **`SesiMisi.tambah_rintangan()`** | [657–680](main.py#L657-L680) | Menambah rintangan di petak kosong. Jika memotong rute aktif, menyimpan rute lama dan mencari ulang dari kondisi terakhir. |
| `jalankan_astar()` | [705–790](main.py#L705-L790) | Menjalankan pencarian dan simulasi melalui terminal, termasuk demo perubahan rute setelah korban pertama ditangani. |

Saat mencari ulang, **posisi, energi, korban yang sudah ditangani, dan biaya terpakai dipertahankan**. Biaya rencana baru hanya menghitung sisa misi. Estimasi total adalah biaya terpakai ditambah biaya rencana baru. Jika tidak ada alternatif yang layak, sesi menjadi buntu.

## 4. GUI dan fitur ubah peta

| Fitur | Fungsi | Baris (klik untuk membuka kode) |
|---|---|---|
| Membuat tampilan dan menghubungkan tombol | `TampilanMisi.__init__()` | [808–952](main.py#L808-L952) |
| Memperbarui status, energi, biaya, korban, dan tombol | `perbarui()` | [965–1005](main.py#L965-L1005) |
| Menggambar grid, robot, jejak, serta rute lama dan aktif | `gambar_peta()` | [1007–1103](main.py#L1007-L1103) |
| Menghentikan dan menjadwalkan animasi otomatis | `_berhenti_otomatis()`, `_jadwalkan()`, `_putar()` | [1105–1129](main.py#L1105-L1129) |
| Tombol Mulai | `mulai()` | [1131–1139](main.py#L1131-L1139) |
| Jeda/Lanjut | `jeda_lanjut()` | [1141–1153](main.py#L1141-L1153) |
| Menjalankan satu aksi tanpa animasi otomatis | `langkah()` | [1155–1162](main.py#L1155-L1162) |
| Mengaktifkan atau membatalkan pemilihan rintangan | `pilih_rintangan()` | [1164–1173](main.py#L1164-L1173) |
| Mengubah koordinat klik menjadi petak dan meminta sesi menambah rintangan | `klik_peta()` | [1175–1195](main.py#L1175-L1195) |
| Membuat sesi baru pada susunan dasar terakhir | `_reset_misi()`, `reset()` | [1197–1210](main.py#L1197-L1210) |
| Mengembalikan Peta Contoh atau mengganti ukuran | `peta_contoh()` | [1212–1217](main.py#L1212-L1217) |
| Membuat dan memasang peta acak yang sudah divalidasi | `acak_peta()` | [1219–1234](main.py#L1219-L1234) |
| Membuka jendela dan menjalankan event loop Tkinter | `jalankan_gui()` | [1243–1260](main.py#L1243-L1260) |
| Memilih mode berdasarkan argumen terminal | `main()` | [1263–1302](main.py#L1263-L1302) |

**Perbedaan fitur peta:** Reset mengulang misi pada susunan dasar terakhir dan menghapus rintangan tambahan saat misi. Peta Contoh mengganti susunan dengan demo bawaan. Acak Peta membuat susunan baru yang layak. Tambah Rintangan mengubah peta sesi berjalan dan dapat memicu pencarian ulang.

## 5. Urutan menunjukkan kode saat presentasi

1. **State robot:** `KondisiRobot` — data apa yang dibutuhkan A*.
2. **Aturan aksi:** `terapkan_aksi()` — batas gerak, energi, tangani, dan isi.
3. **Perencanaan:** `heuristik()` lalu `cari_rencana_astar()` — bagaimana h, g, dan f dihitung.
4. **Hasil dan pelaksanaan:** `RencanaMisi` lalu `SesiMisi` — perbedaan rencana dengan kondisi simulasi nyata.
5. **Perubahan rute:** `tambah_rintangan()` — pencarian ulang dari kondisi terakhir.
6. **Demo GUI:** mulai, jeda, tambah rintangan pada petak kosong di rute aktif, lalu lanjutkan.

**Tiga struktur yang perlu dibedakan:** `KondisiRobot` menyimpan keadaan robot, `RencanaMisi` menyimpan hasil pencarian, dan `SesiMisi` menyimpan serta menjalankan perkembangan misi.
