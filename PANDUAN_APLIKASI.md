# Panduan Menjalankan dan Fitur Aplikasi

Aplikasi ini menyimulasikan robot penyelamat yang harus menangani seluruh korban dan kembali ke pos. Algoritma **A\*** membantu robot merencanakan misi dengan mempertimbangkan rintangan, sisa energi, dan kebutuhan mengisi energi.

## 1. Cara menjalankan aplikasi

Buka terminal di folder proyek yang berisi `main.py`, lalu jalankan:

```powershell
python main.py --gui
```

Perintah tersebut membuka jendela aplikasi dengan peta awal **8×8**. Setelah jendela terbuka, tekan **Mulai** untuk menjalankan robot secara otomatis.

### Memilih ukuran peta sejak awal

Jalankan salah satu perintah berikut sesuai ukuran yang diinginkan:

```powershell
python main.py --gui --peta 6x6
python main.py --gui --peta 8x8
python main.py --gui --peta 10x10
```

Gunakan huruf `x` pada perintah, misalnya `8x8`. Ukuran juga dapat diganti langsung dari jendela aplikasi.

### Kebutuhan sebelum menjalankan

- **Python 3.10 atau lebih baru.** Cek versi dengan `python --version`.
- **Tkinter** untuk membuka tampilan jendela. Mode terminal dapat berjalan tanpa Tkinter.
- Program memakai pustaka bawaan Python; tidak ada paket tambahan yang perlu dipasang melalui `pip`.

Jika perintah `python` tidak dikenali tetapi Python sudah terpasang di Windows, coba gunakan `py`, misalnya `py main.py --gui`.

## 2. Tujuan dan aturan dasar misi

Robot mulai dari **pos (P)** dengan **energi 10** dan biaya awal **0**. Misi baru selesai jika **seluruh korban sudah ditangani dan robot sudah kembali ke pos**.

Aturan yang berlaku:

- Robot bergerak satu petak ke **atas, bawah, kiri, atau kanan**. Tidak ada gerakan diagonal.
- Robot tidak boleh keluar dari peta atau melewati rintangan.
- Mendatangi petak korban belum menyelesaikan penyelamatan; robot harus melakukan aksi **tangani**.
- Mendatangi stasiun belum menambah energi; robot harus melakukan aksi **isi**.
- Dalam mode otomatis, A* merencanakan aksi gerak, tangani, dan isi tersebut.
- Robot boleh tiba kembali di pos dengan energi **0**, selama semua korban sudah ditangani.

## 3. Pilihan ukuran dan isi peta

| Ukuran | Jumlah petak | Pos | Korban | Stasiun pengisian |
|---|---:|---:|---:|---:|
| **6×6** | 36 | 1 | 1 | 1 |
| **8×8** | 64 | 1 | 3 | 3 |
| **10×10** | 100 | 1 | 3 | 3 |

Jumlah objek pada tabel berlaku untuk peta contoh dan peta acak pada ukuran yang sama.

### Mengganti ukuran dari jendela aplikasi

1. Cari pilihan **Ukuran** di bagian atas jendela.
2. Pilih `6x6`, `8x8`, atau `10x10`.
3. Aplikasi memasang **peta contoh** untuk ukuran tersebut dan mengulang kondisi misi dari awal.
4. Tekan **Mulai** atau **Langkah** untuk menjalankannya.

Mengganti ukuran menghentikan simulasi yang sedang berjalan. Jika ingin susunan acak pada ukuran baru, tekan **Acak Peta** setelah memilih ukuran.

## 4. Arti simbol dan tampilan peta

| Simbol | Arti | Penjelasan |
|---|---|---|
| **R** | Robot | Menunjukkan posisi robot saat ini. |
| **P** | Pos | Tempat robot memulai dan mengakhiri misi. |
| **K**, **K1**, **K2**, **K3** | Korban | Lokasi korban yang harus ditangani. Nomor digunakan jika korban lebih dari satu. |
| **C**, **C1**, **C2**, **C3** | Stasiun pengisian | Tempat robot dapat mengisi energi hingga 10. |
| **X** | Rintangan | Petak yang tidak dapat dilewati robot. |
| **.** pada terminal | Petak kosong | Petak yang dapat dilewati; pada jendela ditampilkan sebagai kotak tanpa label objek. |

Peta dilengkapi nomor baris dan kolom. Koordinat ditulis **(baris, kolom)** dan dimulai dari **(1, 1)** di kiri atas. Contoh `(2, 5)` berarti baris kedua, kolom kelima.

Ukuran gambar petak menyesuaikan saat jendela diperbesar atau diperkecil. Perubahan ini hanya memengaruhi tampilan, bukan jumlah petak peta.

## 5. Tombol dan fitur pada jendela aplikasi

### Mulai

Mencari rencana misi menggunakan A*, lalu menjalankan robot secara otomatis. Animasi menjalankan satu aksi sekitar setiap **0,42 detik**. Jika tidak ada rencana yang memenuhi aturan, aplikasi menampilkan bahwa misi tidak dapat dilanjutkan.

### Jeda / Lanjut

- **Jeda** menghentikan animasi sementara agar kondisi robot dapat diamati.
- **Lanjut** meneruskan aksi yang masih tersisa pada rencana aktif.
- Posisi robot, energi, biaya, dan status korban tetap tersimpan selama jeda.

### Langkah

Menjalankan **tepat satu aksi** dari rencana A*. Tombol ini dapat dipakai saat misi masih siap atau saat animasi dijeda.

Satu aksi bisa berupa gerakan, menangani korban, atau mengisi energi. Karena itu, menekan **Langkah** tidak selalu membuat robot berpindah petak.

Jika dipakai sebelum **Mulai**, aplikasi mencari rencana terlebih dahulu, lalu menjalankan satu aksi. Pengguna dapat terus menekan **Langkah** untuk mengamati misi secara bertahap.

### Tambah Rintangan

Memungkinkan pengguna menambahkan rintangan baru saat misi sudah dimulai dan belum selesai atau buntu.

Cara menggunakannya:

1. Tekan **Mulai**, atau tekan **Langkah** untuk memulai misi secara bertahap.
2. Tekan **Tambah Rintangan**. Animasi otomatis berhenti sementara.
3. Klik petak kosong yang ingin dijadikan rintangan.
4. Baca informasi hasil penambahan pada panel **Aksi Terakhir**.
5. Jika misi masih dapat berjalan, tekan **Lanjut** atau **Langkah** untuk meneruskan.

Rintangan hanya boleh ditambahkan pada **petak kosong yang tidak sedang ditempati robot**. Petak pos, korban, stasiun, dan rintangan yang sudah ada tidak dapat dipilih. Klik yang tidak sah menampilkan alasan, lalu pengguna dapat memilih petak lain.

Saat memilih rintangan, tombol berubah menjadi **Batal Pilih**. Menekannya membatalkan pemilihan dan membiarkan misi tetap dijeda. Penambahan dapat dilakukan lagi selama misi masih dapat berjalan.

### Reset

Mengulang misi pada **susunan dasar terakhir**. Robot kembali ke pos dengan energi 10, biaya kembali 0, dan semua korban kembali berstatus belum ditangani. Jejak, rute, jumlah pencarian ulang, serta rintangan tambahan selama misi dibersihkan.

Jika susunan terakhir berasal dari **Acak Peta**, Reset tetap memakai susunan acak tersebut.

### Peta Contoh

Mengganti susunan peta dengan **susunan bawaan** untuk ukuran yang sedang dipilih, lalu mengulang misi dari awal. Tombol ini dapat digunakan untuk kembali ke peta bawaan setelah mencoba peta acak.

### Acak Peta

Membuat susunan baru pada ukuran yang sedang dipilih:

- Pos tetap berada pada lokasi yang sama dengan peta contoh.
- Jumlah korban dan stasiun tetap mengikuti ukuran peta.
- Lokasi korban, stasiun, dan susunan rintangan diacak.
- Susunan yang diterima berbeda dari susunan dasar sebelumnya.
- A* memeriksa bahwa semua korban dapat ditangani dan robot dapat kembali ke pos dengan aturan energi yang berlaku.

Jika berhasil, susunan baru dipasang dan misi kembali ke kondisi awal. Tekan **Mulai** atau **Langkah** untuk menjalankannya.

Jika belum menemukan susunan yang layak, aplikasi menampilkan pesan untuk mencoba lagi. Sesi sebelumnya tetap tersedia, dengan animasi dihentikan.

### Perbedaan tiga tombol pengatur ulang peta

| Tombol | Susunan peta setelah ditekan | Kondisi misi |
|---|---|---|
| **Reset** | Susunan dasar terakhir, termasuk jika berupa peta acak. Rintangan tambahan selama misi dihapus. | Diulang dari awal. |
| **Peta Contoh** | Susunan bawaan untuk ukuran terpilih. | Diulang dari awal. |
| **Acak Peta** | Susunan acak baru yang sudah diuji kelayakannya, jika pembuatan berhasil. | Diulang dari awal jika berhasil. |

## 6. Pencarian rute otomatis dengan A*

A* merencanakan **seluruh misi**, termasuk urutan mengunjungi korban, kapan mengisi energi, dan jalan kembali ke pos. Tujuannya adalah mencari rencana dengan **total biaya aksi paling kecil** yang memenuhi aturan.

Setiap kondisi yang dipertimbangkan mencakup posisi robot, sisa energi, serta korban yang sudah ditangani. Dua kondisi pada petak yang sama dapat menghasilkan pilihan berbeda jika energi atau status korbannya berbeda.

Rumus prioritas A* adalah **f = g + h**:

| Nilai | Arti sederhana |
|---|---|
| **g** | Biaya aksi yang sudah diperlukan untuk mencapai suatu kondisi dari awal pencarian. |
| **h** | Perkiraan biaya yang masih diperlukan untuk menyelesaikan misi. |
| **f** | Jumlah g dan h; membantu menentukan kondisi mana yang diperiksa terlebih dahulu. |

Perkiraan h memakai jarak Manhattan, yaitu jumlah selisih baris dan kolom, serta jumlah korban yang belum ditangani. Aturan rintangan dan energi tetap diperiksa saat mencari rencana yang dapat dijalankan.

## 7. Perubahan rute ketika ada rintangan baru

Respons aplikasi bergantung pada lokasi rintangan:

| Lokasi rintangan baru | Respons aplikasi |
|---|---|
| Di luar sisa rute aktif | Rencana yang ada tetap dipakai; tidak memicu pencarian ulang. |
| Memotong sisa rute aktif | A* mencari rencana baru dari kondisi robot saat ini. |
| Memotong rute dan tidak ada alternatif yang memenuhi aturan | Misi berhenti dan rintangan tetap terpasang. Gunakan Reset atau pilih peta lain untuk mencoba lagi. |

Saat mencari ulang, **posisi robot, sisa energi, korban yang sudah ditangani, dan biaya yang sudah terpakai tetap dipertahankan**. Robot melanjutkan dari keadaan terakhir setelah rencana baru ditemukan.

Perkiraan total biaya diperbarui menjadi **biaya yang sudah terpakai + biaya sisa rencana baru**. Jumlah pencarian ulang juga bertambah.

## 8. Energi dan biaya aksi

Energi menunjukkan kemampuan robot melakukan aksi berikutnya. Biaya menunjukkan jumlah aksi sah yang telah dilakukan selama misi.

| Aksi | Syarat utama | Pengaruh pada energi | Tambahan biaya |
|---|---|---|---:|
| Gerak satu petak | Energi minimal 1; tujuan di dalam peta dan bukan rintangan. | Berkurang 1. | 1 |
| Tangani korban | Berada di korban yang belum ditangani; energi minimal 1. | Berkurang 1. | 1 |
| Isi energi | Berada di stasiun dan energi belum penuh. | Kembali menjadi 10. | 1 |
| Aksi yang ditolak | Misalnya menabrak rintangan atau mengisi di luar stasiun. | Tetap. | 0 |

**Contoh perhitungan:** 10 aksi gerak + 1 aksi tangani + 2 aksi isi menghasilkan biaya **13**. Ini hanya contoh menghitung biaya, bukan urutan rute tertentu.

Robot yang energinya 0 masih dapat mengisi jika sudah berada di stasiun. Pos berfungsi sebagai titik awal dan tujuan pulang; pengisian dilakukan di stasiun **C**.

## 9. Informasi dan visualisasi selama simulasi

### Panel informasi

| Informasi | Yang ditampilkan |
|---|---|
| **Status Misi** | Siap, Berjalan, Dijeda, Misi selesai, atau Misi berhenti. |
| **Energi Robot** | Angka energi saat ini dari maksimum 10 dan batang indikator. Warna indikator berubah saat energi tersisa 3 atau kurang. |
| **Posisi** | Koordinat robot saat ini dalam format (baris, kolom). |
| **Biaya terpakai** | Total biaya aksi yang sudah dilakukan. |
| **Rencana** | Perkiraan total biaya hingga misi selesai menurut rencana aktif. Tanda `-` muncul jika belum ada rencana atau tidak ada rencana yang layak. |
| **Pencarian ulang** | Jumlah pencarian ulang akibat rintangan yang memotong rute. |
| **Korban** | Status masing-masing korban: Menunggu atau Ditangani. |
| **Aksi Terakhir** | Pesan aksi, hasil perubahan peta, atau alasan suatu tindakan ditolak. |

### Garis dan penanda pada peta

- **Garis hijau:** sisa rute aktif yang akan dijalankan robot.
- **Garis kuning/oranye putus-putus:** sisa rute lama sebelum pencarian ulang terakhir.
- **Garis abu-abu kebiruan:** jejak pergerakan yang sudah ditempuh robot.
- **Petak korban berwarna hijau:** korban tersebut sudah ditangani.
- **Rintangan baru berwarna berbeda:** membedakan rintangan tambahan dari rintangan bawaan.
- **Sorotan putus-putus saat memilih rintangan:** muncul pada petak gerak berikutnya jika petak itu kosong, sebagai contoh lokasi yang dapat memotong rute.

Garis rute menggambarkan perpindahan robot. Aksi tangani dan isi berlangsung pada petak yang sama sehingga tidak menambahkan ruas garis.

## 10. Mode lain melalui terminal

Selain jendela aplikasi, proyek menyediakan mode berikut. Jalankan setiap perintah secara terpisah.

| Mode | Perintah | Kegunaan |
|---|---|---|
| Demo bawaan | `python main.py` | Menjalankan urutan aksi tetap pada peta 6×6, termasuk contoh aksi menabrak rintangan yang ditolak. |
| A* otomatis | `python main.py --astar --peta 6x6` | Mencari rencana dan menampilkan simulasi langkah demi langkah di terminal. |
| A* pada peta 8×8 | `python main.py --astar --peta 8x8` | Menjalankan misi dengan tiga korban dan tiga stasiun. |
| A* pada peta 10×10 | `python main.py --astar --peta 10x10` | Menjalankan misi pada peta terbesar yang tersedia. |
| Demo rintangan dinamis | `python main.py --dinamis` | Memakai peta 8×8; menambahkan rintangan di (2, 5) setelah korban pertama ditangani. |
| Dinamis dengan pilihan peta dan koordinat | `python main.py --dinamis --peta 10x10 --rintangan 2 5` | Memilih peta dan lokasi rintangan untuk demo perubahan rute. |
| Kendali manual | `python main.py --manual --peta 6x6` | Memilih sendiri setiap aksi robot melalui masukan keyboard di terminal. |
| Bantuan perintah | `python main.py --help` | Menampilkan pilihan mode dan argumen program. |

Ukuran dapat dipilih melalui `--peta 6x6`, `--peta 8x8`, atau `--peta 10x10`. Jika tidak ditentukan, **GUI dan dinamis memakai 8×8**, sedangkan **manual, A*, dan demo bawaan memakai 6×6**.

Pilih satu mode dalam satu perintah: `--gui`, `--astar`, `--manual`, atau `--dinamis`. Opsi `--rintangan BARIS KOLOM` hanya berlaku bersama `--dinamis`. Untuk demo dinamis pada peta 6×6, koordinat rintangan wajib ditentukan.

Pada mode dinamis, rintangan dimasukkan setelah aksi tangani korban pertama. Pencarian ulang hanya terjadi jika rintangan memotong sisa rute; koordinat lain dapat membuat rencana tetap berlaku atau membuat misi tidak dapat diselesaikan.

### Tombol pada mode manual

Ketik salah satu perintah berikut, lalu tekan **Enter**:

| Masukan | Aksi |
|---|---|
| `w` | Bergerak ke atas. |
| `s` | Bergerak ke bawah. |
| `a` | Bergerak ke kiri. |
| `d` | Bergerak ke kanan. |
| `h` | Menangani korban di posisi robot. |
| `c` | Mengisi energi di stasiun. |
| `q` | Keluar dari mode manual. |

Aturan energi, rintangan, dan syarat selesai tetap berlaku pada mode manual. Kendali keyboard ini digunakan di terminal.

### Informasi pada keluaran A* di terminal

Mode A* menampilkan jumlah kondisi yang diperiksa saat pencarian awal, biaya rencana, dan tabel berisi nomor aksi, nama aksi, posisi, energi, status korban, g, h, serta f. Jumlah kondisi yang diperiksa menunjukkan proses pencarian dan dapat lebih besar daripada jumlah aksi robot.

Nilai pada tabel ditampilkan **setelah setiap aksi**. Kolom g di tabel adalah biaya terpakai sejak awal misi, sedangkan saat pencarian ulang, perhitungan internal A* dimulai dari 0 untuk merencanakan sisa misi.

## 11. Contoh urutan mencoba fitur

1. Jalankan `python main.py --gui --peta 8x8`.
2. Tekan **Langkah** beberapa kali untuk melihat perubahan posisi, energi, dan biaya per aksi.
3. Tekan **Lanjut** agar robot bergerak otomatis, lalu **Jeda** untuk mengamati kondisinya.
4. Tekan **Tambah Rintangan**, kemudian pilih petak kosong pada **sisa rute hijau** yang tidak ditempati robot.
5. Perhatikan rute lama, hasil pencarian rute baru, dan angka **Pencarian ulang**. Jika tidak ada alternatif, coba kembali dengan **Reset**.
6. Jika rute baru tersedia, tekan **Lanjut** sampai seluruh korban ditangani dan robot kembali ke pos.
7. Tekan **Reset** untuk mengulang pada susunan dasar yang sama.
8. Tekan **Acak Peta** untuk mencoba susunan baru yang sudah diuji kelayakannya.
9. Ganti **Ukuran** menjadi `6x6` atau `10x10` untuk membandingkan misi.
10. Tekan **Peta Contoh** jika ingin memakai kembali susunan bawaan untuk ukuran terpilih.

Untuk penjelasan fungsi dan lokasi kode, buka [Panduan Kode](PANDUAN_KODE.md). Seluruh implementasi aplikasi berada di [main.py](main.py).
