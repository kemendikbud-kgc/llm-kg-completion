# Bab 4 — Perbaikan P0 (sebelum presentasi)

Sumber angka: `lintas_buku_edges.t070_k20.json` (konfigurasi final: threshold 0,70 / top_k 20 / chat_model gemini-2.5-flash). **Hapus seluruh catatan dalam blok `>` sebelum submit.**

---

## FIX #1 — Satukan jumlah edge lintas-buku ke SATU konfigurasi final

> Masalah: §4.2.3.1 & "Dampak KGC" memakai **0,80/k10 → 44 edge**; metode (idx 580) menyebut threshold **0,75**; tetapi validasi pakar & Neo4j memakai run **0,70/k20 → 125 edge**. Pakai run yang **benar-benar divalidasi pakar dan tersimpan di Neo4j**: **0,70 / k20 / 125 edge**.

**Ganti paragraf pembuka §4.2.3.1 (idx 647) dengan:**

Pada konfigurasi final (threshold = 0,70; top_k = 20; scope lintas-mapel), pipeline menemukan **125 relasi lintas-buku**. Distribusi tipe relasi didominasi **PRASYARAT_UNTUK (57 edge, 45,6%)**, diikuti **MEMPERDALAM (31 edge, 24,8%)**, **BERKAITAN_DENGAN (21 edge, 16,8%)**, **APLIKASI_DARI (15 edge, 12,0%)**, dan **SAMA_DENGAN (1 edge, 0,8%)**. Dominasi PRASYARAT_UNTUK mengindikasikan bahwa jembatan lintas-disiplin pada kurikulum sains kelas XII lebih banyak bersifat prasyarat pengetahuan daripada aplikasi atau analogi. Dari 125 relasi, **8 edge berkonfidens < 0,5** (seluruhnya BERKAITAN_DENGAN) dikeluarkan dari survei validasi utama, menyisakan **117 relasi** yang dinilai pakar.

**Ganti kalimat statistik confidence (idx 649) dengan:**

Dari 125 edge, **20 edge (16%)** memiliki skor confidence = 1,0, menunjukkan keyakinan tinggi LLM. Contoh relasi dengan confidence tertinggi meliputi: *(pertahankan 4 contoh DNA→Gen, Potensial Elektrode→Potensial Listrik, Enzim→Protein, Fosforilasi Oksidatif→Oksidasi — masih valid).*

**Ganti pembuka §4.2.3.2 (idx 659) dengan:**

Sebanyak **9 edge memiliki confidence < 0,7** (8 di antaranya < 0,5), yang mengindikasikan potensi false positive. *(pertahankan 3 contoh Gerbang Logika, Semikonduktor, Efek Fotolistrik).*

**Ganti "Dampak KGC" (idx 686) dengan:**

Pipeline KGC berhasil menambahkan **125 jembatan lintas-buku** yang sebelumnya tidak ada antar-mata pelajaran. Secara kualitatif, mayoritas relasi ini bermakna pedagogis dan dapat dipertanggungjawabkan secara ilmiah; keberadaan sejumlah kecil false positive pada confidence rendah menggarisbawahi pentingnya pemilihan threshold dan validasi pakar sebagai filter akhir.

> Juga perbaiki di tempat lain agar konsisten:
> - **Metode idx 580:** ubah threshold lintas-buku **0,75 → 0,70** (dan jelaskan 0,80 hanya untuk intra-buku, atau hapus jika tak relevan).
> - **Overview Tahapan (idx 448), baris Completion:** model classifier = **Gemini 2.5 Flash** (bukan Flash Lite — Flash Lite dipakai di Extraction).
> - Jangan lagi memakai angka **44** atau **65.703** di mana pun (65.703 = C(363,2) = SEMUA pasangan, bukan ruang lintas-mapel; bila ingin ruang kandidat lintas-mapel sebut ~39.800 pasangan untuk 350 konsep).

---

## FIX #2 — Perbaiki definisi tipe relasi yang terduplikasi (idx 595–601)

> Masalah: dua baris tertulis `LINTAS_BUKU_PRASYARAT_UNTUK`; baris kedua sebenarnya MEMPERDALAM.

**Ganti daftar 5 label menjadi:**

- **LINTAS_BUKU_SAMA_DENGAN**: A dan B merujuk pada entitas semantik yang sama lintas buku (simetris).
- **LINTAS_BUKU_APLIKASI_DARI**: A adalah aplikasi/manifestasi konsep B di disiplin berbeda (asimetris).
- **LINTAS_BUKU_PRASYARAT_UNTUK**: A pada satu mapel menjadi prasyarat untuk memahami B di mapel lain (asimetris).
- **LINTAS_BUKU_MEMPERDALAM**: A memperdalam/memperluas pemahaman B di buku lain (asimetris).
- **LINTAS_BUKU_BERKAITAN_DENGAN**: A dan B berkaitan secara umum lintas buku tanpa struktur ketat (simetris, fallback).
- **none**: kemiripan semantik hanya superfisial; tidak ada relasi kurikuler bermakna.

---

## FIX #3 — Placeholder & subbab kosong

### 3a. Isi hasil validasi Fase 2 (yang SUDAH ada datanya)
Sisipkan blok dari `bab4_4231_validasi_pakar_draft.md` ke §4.2.3.1 (validitas 99% / tipe 98% / arah 74% + temuan bias arah). Ini mengisi satu-satunya hasil kuantitatif Fase 2 yang saat ini kosong.

### 3b. Bracket yang BELUM punya angka — JANGAN dipresentasikan dengan `[ ]` terlihat
Angka berikut harus dihitung dari data nyata (jangan dikarang). Bila belum sempat: hapus kalimatnya atau ganti dengan "sedang dihitung", **bukan** dibiarkan berkurung:

| Lokasi | Placeholder | Sumber angka |
|---|---|---|
| idx 631 | ADC Pre/Post-KGC | kueri Cypher metrik (Neo4j) |
| idx 632 | Modularity Pre-KGC | kueri Cypher |
| idx 633 | Description Completeness %, TRR % | metrik ekstraksi |
| idx 639 | Precision Fase 1 / Fase 2 %, Selisih % | hasil review pakar (Fase 1) |
| idx 640 | AC1 | hanya bila Fase 1 punya ≥2 penilai pada triple yang sama |

> Catatan AC1/κ: untuk **Fase 2 (completion)** baru ada **satu penilai** → kesepakatan antar-pakar belum dapat dihitung. Nyatakan ini eksplisit; jangan tampilkan AC1 Fase 2.

### 3c. §4.2.4 "Analisis Komparatif Antar-Domain Sains" (idx 688) KOSONG
Untuk presentasi: **hapus/ sembunyikan heading kosong ini** agar tidak terlihat belum selesai — atau isi dari data presisi per-mapel hasil review (tersedia: Biologi ~0,95; Fisika 0,86–0,99; Kimia 0,82–0,84). Drafting paragraf ini = P1 (beri tahu bila mau).

---

> **Caveat verifikasi:** audit ini memakai cache dokumen tertanggal 1 Juni; bila ada edit setelahnya, nomor idx bisa bergeser tetapi isu tetap sama. Verifikasi 3 hal di doc langsung: (1) tidak ada lagi angka "44 edge", (2) tidak ada `[ ]` terlihat di §4.2, (3) §4.2.4 tidak tampil kosong.
