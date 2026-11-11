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

## Panduan aplikasi

Lihat [Panduan Menjalankan dan Fitur Aplikasi](PANDUAN_APLIKASI.md) untuk perintah menjalankan, pilihan ukuran peta, cara memakai setiap tombol, aturan energi, dan contoh mencoba fitur.

## Panduan kode

Lihat [Panduan Lokasi Kode Penting](PANDUAN_KODE.md) untuk penjelasan bagian utama, urutan presentasi, serta tautan ke baris kode `main.py` lokal.
