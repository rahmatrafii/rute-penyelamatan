# rute-penyelamatan

Proyek kuliah AI: **Perencanaan Misi Robot Penyelamat dengan Keterbatasan Energi Menggunakan Algoritma A***.

Simulasi Python dan Tkinter untuk merencanakan misi menangani semua korban dan kembali ke pos dengan biaya aksi minimum. Robot bergerak dalam empat arah, menghindari rintangan, dan mengisi energi di stasiun dengan kapasitas maksimum 10.

## Menjalankan

Gunakan Python 3.10 atau lebih baru. Mode GUI memerlukan Tkinter.

```bash
python main.py --gui
python main.py --astar --peta 8x8
python main.py --dinamis
python main.py --manual
```

Ukuran peta tersedia: `6x6`, `8x8`, dan `10x10`.

GUI menyediakan Mulai, Jeda/Lanjut, Langkah, Tambah Rintangan, Reset, Acak Peta, dan Peta Contoh. Jika rintangan baru memotong rute aktif, A* mencari ulang dari kondisi robot terakhir. Peta acak divalidasi dengan A* sebelum digunakan.

Kode utama dan komentar penjelasan algoritma berada di `main.py`.

## Dataset dan evaluasi A*

Evaluasi terpisah tersedia untuk progres proyek Python: **300 peta layak dan 30 kasus tanpa solusi**, dengan susunan peta, seed, serta hasil pengujian yang disimpan. Empat metriknya adalah keberhasilan misi, biaya aksi, waktu pencarian, dan jumlah state yang diperiksa.

Buka [laporan hasil](hasil_evaluasi/laporan.md) dan [panduan evaluasi](PANDUAN_EVALUASI.md). Untuk menguji ulang dataset yang sama:

```powershell
python evaluasi.py jalankan
```

Grafik dapat dibuat dari hasil CSV dengan `python grafik_evaluasi.py` setelah memasang `requirements-evaluasi.txt`. Peta layak sudah disaring oleh A*; kasus negatif dilaporkan terpisah. Kegiatan ini adalah evaluasi pencarian, tanpa pelatihan model.

## Panduan aplikasi

Lihat [Panduan Menjalankan dan Fitur Aplikasi](PANDUAN_APLIKASI.md) untuk perintah menjalankan, pilihan ukuran peta, cara memakai setiap tombol, aturan energi, dan contoh mencoba fitur.

## Panduan kode

Lihat [Panduan Lokasi Kode Penting](PANDUAN_KODE.md) untuk penjelasan bagian utama, urutan presentasi, serta tautan ke baris kode `main.py` lokal.
