# Panduan Dataset dan Evaluasi A*

Panduan ini menyiapkan progres proyek Python/Tkinter di branch `main`. Pengujian memakai fungsi A* asli dari `main.py` melalui skrip terpisah. Kode aplikasi utama dan rujukan baris pada Panduan Kode tetap dipertahankan.

## 1. Mulai dari hasil yang sudah tersedia

Buka [laporan eksperimen](hasil_evaluasi/laporan.md). Laporan berisi hasil nyata, tabel per ukuran, grafik, metode pengukuran, dan batas interpretasinya.

File yang dapat ditunjukkan kepada dosen:

| File | Isinya |
|---|---|
| [skenario.jsonl](data_evaluasi/skenario.jsonl) | Susunan lengkap 330 peta, koordinat objek, energi awal, seed, dan label. |
| [indeks_skenario.csv](data_evaluasi/indeks_skenario.csv) | Daftar singkat seluruh skenario; dapat dibuka di aplikasi spreadsheet. |
| [hasil_per_peta.csv](hasil_evaluasi/hasil_per_peta.csv) | Empat metrik dan hasil validasi setiap peta. |
| [waktu_per_ulangan.csv](hasil_evaluasi/waktu_per_ulangan.csv) | 1.650 catatan waktu, yaitu 330 peta × 5 pengulangan. |
| [ringkasan.csv](hasil_evaluasi/ringkasan.csv) | Ringkasan berdasarkan ukuran dan jenis kasus. |
| [metadata_run.json](hasil_evaluasi/metadata_run.json) | Versi Python, perangkat, seed urutan uji, waktu eksperimen, serta checksum sumber dan data. |

## 2. Menjelaskan dataset

Dataset bersifat **sintetis**: dibuat oleh program, bukan dikumpulkan dari kejadian penyelamatan nyata. Satu data berarti **satu skenario peta**, bukan satu petak atau satu langkah robot.

| Ukuran | Peta layak | Pos terkurung | Energi tidak cukup | Total |
|---|---:|---:|---:|---:|
| 6×6 | 100 | 5 | 5 | 110 |
| 8×8 | 100 | 5 | 5 | 110 |
| 10×10 | 100 | 5 | 5 | 110 |
| **Total** | **300** | **15** | **15** | **330** |

Peta 6×6 memiliki satu korban dan satu stasiun; 8×8 dan 10×10 masing-masing tiga korban dan tiga stasiun. Setiap peta punya satu pos, energi awal 10, dan biaya 1 untuk setiap aksi sah.

Peta layak dibuat menggunakan `buat_peta_acak()` asli pada `main.py`. Pos dan jumlah objek mengikuti peta contoh; lokasi korban, stasiun, dan rintangan diacak. Fungsi ini **sudah menyaring peta menggunakan A***, sehingga tingkat keberhasilan kelompok ini harus dibaca bersama proses penyaringan tersebut.

Dua jenis kasus negatif sengaja dibuat terpisah:

- **Pos terkurung:** kedua jalan keluar pos di sudut peta ditutup rintangan. Robot tidak dapat memulai perjalanan.
- **Energi tidak cukup:** korban dan stasiun tetap dapat dicapai jika hanya memperhatikan jalan, tetapi semuanya berjarak lebih dari 10 langkah dari pos. Robot kehabisan energi sebelum dapat mencapai kesempatan pengisian pertama.

Bukti kasus negatif diperiksa dengan BFS geometris sederhana. Pengujian A* kemudian memeriksa apakah algoritma juga mengembalikan hasil tanpa solusi. Respons tersebut dihitung sebagai **penolakan yang benar**, bukan sebagai kegagalan algoritma.

Semua susunan peta diperiksa unik berdasarkan SHA-256. Grid lengkap disimpan karena seed saja belum menjamin susunan identik jika kode atau versi perangkat lunak berubah.

Checksum file teks menormalkan akhir baris menjadi LF, sehingga pergantian LF/CRLF oleh Git pada Windows atau Linux tidak membatalkan verifikasi. BOM UTF-8 pada file CSV tetap dipertahankan.

## 3. Arti kolom dataset

| Kolom | Arti |
|---|---|
| `id` | Identitas unik skenario. |
| `ukuran` | 6x6, 8x8, atau 10x10. |
| `kelompok` | `layak` atau `tanpa_solusi`. |
| `jenis` | Cara skenario dibuat: acak tervalidasi, pos terkurung, atau energi tidak cukup. |
| `seed` | Angka pengendali pengacakan untuk kandidat peta tersebut. |
| `petak` | Daftar baris grid: P=pos, K=korban, C=stasiun, X=rintangan, titik=kosong. |
| `pos`, `korban`, `stasiun` | Koordinat (baris, kolom), mulai dari (1, 1). |
| `energi_awal`, `biaya_aksi` | Aturan awal yang digunakan saat pengujian. |
| `harapan_layak` | Apakah skenario diharapkan mempunyai solusi. |
| `sha256_peta` | Sidik susunan peta untuk memeriksa keunikan dan integritas. |

## 4. Empat metrik evaluasi

1. **Keberhasilan misi.** Rencana dijalankan ulang memakai `terapkan_aksi()`. Misi harus memenuhi `misi_selesai()`: seluruh korban ditangani dan robot kembali ke pos.
2. **Total biaya aksi.** Jumlah biaya gerak, tangani, dan isi. Ini dapat berbeda dari panjang lintasan gerak. Biaya pada kasus tanpa solusi dikosongkan, bukan diberi angka nol.
3. **Waktu pencarian.** Hanya durasi pemanggilan `cari_rencana_astar()`, diukur dengan `time.perf_counter_ns()`. Satu warmup dikeluarkan; lima ulangan terukur diringkas menggunakan median.
4. **State diperiksa.** Jumlah kondisi lengkap (posisi, energi, korban ditangani) yang diproses A*. Angka ini berbeda dari jumlah aksi atau jumlah petak.

Pada hasil tanpa solusi, fungsi asli mengembalikan `None` tanpa counter. Evaluator menjalankan satu pencarian tambahan dengan observer untuk membaca variabel lokal `diperiksa`. Pencarian tambahan ini **tidak masuk waktu benchmark** dan tidak mengubah algoritma.

Urutan peta diacak dengan seed tersendiri. Pembuatan data, validasi rencana, observer counter, tampilan GUI, dan penulisan file berada di luar timer. Dataset dan run menyimpan checksum `main.py` agar versi algoritma dapat diperiksa.

## 5. Mengulang eksperimen

Gunakan Python 3.10 atau lebih baru. Dataset dan evaluasi hanya membutuhkan pustaka bawaan Python.

Dataset bawaan sudah disertakan. Untuk menguji ulang dataset yang sama:

```powershell
python evaluasi.py jalankan
```

Perintah tersebut memperbarui hasil CSV dan laporan. Waktu pencarian dapat berbeda karena kondisi komputer berubah.

Untuk membuat dataset baru dengan parameter bawaan:

```powershell
python evaluasi.py buat-dataset --timpa
python evaluasi.py jalankan
```

Dataset bawaan: 100 peta layak dan 10 kasus negatif per ukuran, seed dasar `20261111`. Seed urutan evaluasi adalah `20261112`. Parameter dapat dipilih, misalnya untuk percobaan kecil:

```powershell
python evaluasi.py buat-dataset --jumlah 5 --negatif 2 --seed 42 --dataset data_percobaan/skenario.jsonl
python evaluasi.py jalankan --dataset data_percobaan/skenario.jsonl --keluaran hasil_percobaan --ulang 3
```

Jumlah negatif harus genap karena dibagi merata ke dua jenis kasus. Dataset yang sudah ada tidak ditimpa kecuali memakai `--timpa`. Hasil evaluasi pada folder keluaran yang sama diperbarui ketika perintah dijalankan ulang.

## 6. Grafik untuk presentasi

PNG dan SVG yang sudah tersedia dapat langsung dibuka tanpa memasang paket tambahan. Untuk membuat grafik baru dari hasil CSV:

```powershell
python -m pip install -r requirements-evaluasi.txt
python grafik_evaluasi.py
```

Matplotlib hanya diperlukan untuk membuat grafik. Aplikasi Tkinter, pembuatan dataset, dan pengujian A* tetap dapat dijalankan tanpa Matplotlib.

Empat grafik tersedia dalam format PNG dan SVG:

- `waktu_pencarian`: distribusi median waktu pada peta layak.
- `state_diperiksa`: distribusi jumlah state pada peta layak.
- `biaya_aksi`: distribusi total biaya pada peta layak.
- `hasil_pengujian`: hasil yang sesuai harapan pada setiap jenis skenario.

Boxplot memperlihatkan median, rentang kuartil, dan pencilan. Grafik waktu/biaya/state hanya memakai misi yang selesai; kasus tanpa solusi disajikan terpisah pada tabel laporan dan grafik kesesuaian hasil. Grafik lama tidak dimasukkan ke laporan run baru jika checksum hasil sudah berubah.

## 7. Batas kesimpulan

- Ini **evaluasi pencarian A***, bukan pelatihan model. Istilah training/testing machine learning tidak dipakai sebagai klaim kegiatan yang dilakukan.
- Jumlah 330 skenario merupakan rancangan eksperimen proyek, bukan standar minimum dataset universal.
- Peta layak telah lolos seleksi A*. Keberhasilan 100%, jika tercapai, harus dijelaskan dalam konteks ini.
- Perubahan ukuran grid juga disertai perubahan jumlah korban/stasiun. Pengaruh keduanya belum dipisahkan.
- Belum ada pembanding UCS; hasil ini tidak membuktikan A* lebih cepat atau lebih baik daripada algoritma lain.
- Hasil belum mewakili seluruh peta nyata, seluruh kondisi energi, atau perubahan rintangan di tengah misi.

## 8. Urutan progres kepada dosen

1. Jelaskan tujuan: menangani semua korban dan kembali ke pos dengan batas energi.
2. Tunjukkan satu contoh grid dan jelaskan arti P/K/C/X serta struktur state robot.
3. Jelaskan asal data sintetis, jumlah skenario, keunikan, seed, dan dua kelompok label.
4. Tunjukkan `heuristik()` dan `cari_rencana_astar()`, lalu jelaskan f = g + h.
5. Buka laporan, jelaskan empat metrik, dan tunjukkan satu grafik waktu atau jumlah state.
6. Sampaikan batas penelitian dan tanyakan apakah dosen meminta pembanding algoritma atau memang mewajibkan model yang dilatih.

Referensi pengukuran: [timer Python](https://docs.python.org/3/library/time.html#time.perf_counter_ns) dan [boxplot Matplotlib](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.boxplot.html).
