# Bab 4 — P0 Closeout (find → replace)

Exact replacements against the **live doc** (fetched 4 Juni). Each block: cari teks lama → ganti dengan teks baru. Angka dari `lintas_buku_edges.t070_k20.json` (125 edge, threshold 0,70 / k20).

---

## A. Hapus sisa angka "44 / 5" yang bertabrakan dengan 125

**A1 — idx 675 (di §4.2.3.1, dua baris di bawah "125 relasi"):**

CARI:
> Dari 44 edge, 7 memiliki skor confidence = 1.0 (16%), menunjukkan keyakinan tinggi LLM terhadap relasi tersebut.

GANTI:
> Dari 125 edge, 20 (16%) memiliki skor confidence = 1,0, menunjukkan keyakinan tinggi LLM terhadap relasi tersebut.

**A2 — idx 694 (pembuka §4.2.3.2):**

CARI:
> Sebanyak 5 edge memiliki confidence < 0.7, yang mengindikasikan potensi false positive:

GANTI:
> Sebanyak 9 edge memiliki confidence < 0,7 (8 di antaranya < 0,5), yang mengindikasikan potensi false positive:

**A3 — idx 699 (penutup §4.2.3.2):**

CARI:
> Dari 8 edge bertipe BERKAITAN_DENGAN, mayoritas memiliki confidence lebih rendah dibandingkan tipe lainnya,

GANTI:
> Dari 21 edge bertipe BERKAITAN_DENGAN, mayoritas memiliki confidence lebih rendah dibandingkan tipe lainnya,

**A4 — idx 721 ("Dampak KGC"):**

CARI:
> Pipeline KGC berhasil menambahkan 44 jembatan lintas-buku yang sebelumnya tidak ada.

GANTI:
> Pipeline KGC berhasil menambahkan 125 jembatan lintas-buku antar-mata pelajaran yang sebelumnya tidak ada.

---

## B. Satukan label "0,70" → "konfigurasi final" (hentikan kontradiksi permisif/final/pra-sweep)

**B1 — idx 673 (juga perbaiki kata "konfigurasi" yang dobel):**

CARI:
> Pada konfigurasi konfigurasi final (threshold = 0,70; top_k = 20; scope lintas-mapel), pipeline menemukan 125 relasi lintas-buku.

GANTI:
> Pada konfigurasi final (threshold = 0,70; top_k = 20; scope lintas-mapel), pipeline menemukan 125 relasi lintas-buku.

**B2 — idx 683 (ganti "pra-sweep" → "final"):**

CARI:
> Validasi tahap awal (pilot) ini dilakukan oleh satu pakar atas 100 dari 117 relasi kandidat pada konfigurasi pra-sweep (threshold = 0,70; top_k = 20).

GANTI:
> Validasi tahap awal (pilot) ini dilakukan oleh satu pakar atas 100 dari 117 relasi kandidat pada konfigurasi final (threshold = 0,70; top_k = 20).

**B3 — idx 593 (metode: samakan threshold lintas-buku jadi 0,70):**

CARI:
> threshold = 0.80 untuk pencarian intra-buku; threshold = 0.75 untuk pencarian lintas-buku

GANTI:
> threshold = 0,80 untuk pencarian intra-buku; threshold = 0,70 untuk pencarian lintas-buku (konfigurasi final terpilih dari hasil parameter sweep)

> Catatan: bila di Bab 3 / tempat lain masih tertulis 0,75 untuk lintas-buku, samakan juga ke 0,70.

---

## C. Perbaiki definisi tipe relasi terduplikasi (idx 611–612)

CARI (dua baris):
> LINTAS_BUKU_PRASYARAT_UNTUK: A pada satu mapel menjadi prasyarat untuk B di mapel lain (asimetris).
> LINTAS_BUKU_PRASYARAT_UNTUK: A memperdalam/memperluas pemahaman B di buku lain (asimetris).

GANTI:
> LINTAS_BUKU_PRASYARAT_UNTUK: A pada satu mapel menjadi prasyarat untuk memahami B di mapel lain (asimetris).
> LINTAS_BUKU_MEMPERDALAM: A memperdalam/memperluas pemahaman B di buku lain (asimetris).

---

## D. Placeholder & subbab kosong — TIDAK boleh dikarang (isi nilai nyata atau hapus kalimat)

> Angka berikut harus dari perhitungan nyata. Untuk presentasi: isi, atau hapus kalimatnya. **Jangan biarkan `[ ]` terlihat.**

- idx 647: `[Nilai Pre-KGC]`, `[Nilai Post-KGC]`, `[proceed]` (ADC) → dari kueri Cypher.
- idx 648: `[Nilai Pre-KGC]` (Modularity).
- idx 649: `[Nilai DC]%`, `[Nilai TRR]%`, `[proceed]`.
- idx 655: `[Nilai Presisi Fase 1]%`, `[Nilai Presisi Fase 2]%`, `[misal, …]`, `[Nilai Selisih]%`.
- idx 656: `[Proceed]` (AC1).
- **idx 723 §4.2.4 "Analisis Komparatif Antar-Domain Sains" KOSONG** → untuk presentasi, sembunyikan heading ini, atau minta saya draf dari presisi per-mapel (data nyata tersedia: Biologi ~0,95; Fisika 0,86–0,99; Kimia 0,82–0,84).

> Catatan AC1 (idx 651/656): Fase 2 (completion) baru 1 penilai → AC1/κ belum dapat dihitung untuk Fase 2. Nyatakan eksplisit; jangan tampilkan AC1 Fase 2.

---

## E. Struktur (P1, bila sempat)

- **Caption sebagai Heading** (idx 643, 661, 664, 686): ubah dari gaya *Heading* ke *Normal/Caption* agar tidak masuk Daftar Isi.
- **Penomoran §4.2.3:** beri nomor pada subbagian tak-bernomor — "Validasi Pakar…" (681), "Analisis Pola Kesalahan…" (702), "Dampak KGC" (720) — atau jadikan sub dari 4.2.3.1/.2/.3 yang sesuai.
- **Salah tempat:** idx 702–717 (error ekstraksi: ragi/elektrorefining/rumus + kategori feedback) sebenarnya tentang **ekstraksi**, bukan completion → pertimbangkan pindah ke §4.2.2.
- **Tambah heading `4.1`** sebelum 4.1.1 (intro saat ini langsung ke 4.1.1).

---

## F. Polish (P2)

- idx 673: "MEMPERDALAM  (31 edge" dan "APLIKASI_DARI  (15 edge" — ada **spasi ganda**, rapikan.
- idx 573: "Hal inipenting" → "Hal ini penting".
- idx 495: "Kompleksitas __ untuk __ chunk dan __ bab" → kembalikan simbol `O(...)`.
- idx 583: "nilai default:" → lengkapi daftar nilai default HNSW (mis. M=16, efConstruction=100) atau hapus titik dua.
- idx 588→590: formula cosine similarity hilang → sisipkan persamaannya.
- idx 618: caption "Distribusi tipe relasi … contoh triple per tipe" tanpa tabel → tambahkan tabel atau hapus caption.
- idx 607: classifier completion ditulis "few-shot" → verifikasi (ekstraksi zero-shot); bila prompt hanya berisi definisi label tanpa contoh berlabel, ganti ke "zero-shot dengan definisi label ketat".
