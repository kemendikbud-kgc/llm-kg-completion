# BAB III
# METODOLOGI PENELITIAN

## 3.1 Desain Penelitian

Penelitian ini menggunakan pendekatan **Design Science Research (DSR)** dengan fokus pada pengembangan purwarupa sistem *Knowledge Graph Completion* berbasis *Large Language Model* (LLM). DSR dipilih karena penelitian ini bertujuan untuk menghasilkan artefak berupa kerangka kerja komputasional yang dapat memecahkan masalah fragmentasi kurikulum sains dalam Kurikulum Merdeka.

Menurut Hevner et al. (2004), DSR merupakan paradigma penelitian yang berfokus pada pengembangan artefak inovatif untuk menjawab masalah-masalah yang teridentifikasi dalam domain organisasi. Artefak yang dikembangkan dalam penelitian ini meliputi:

1. **Purwarupa sistem** — Aplikasi web berbasis Streamlit untuk mengekstrak, menyimpan, dan memvisualisasikan *knowledge graph* kurikulum sains
2. **Algoritma ekstraksi** — Metode ekstraksi terstruktur menggunakan LLM dengan output berbasis Pydantic schema
3. **Pipeline KGC** — Tahapan *completion* menggunakan *embedding similarity* dan klasifikasi LLM

Penelitian ini dikategorikan sebagai **penelitian terapan** (*applied research*) dengan karakteristik:

| Karakteristik | Deskripsi |
|---------------|-----------|
| Jenis Penelitian | Terapan (*Applied Research*) |
| Pendekatan | Design Science Research (DSR) |
| Metode | Eksperimental dengan validasi kualitatif |
| Output | Purwarupa sistem (*prototype*) |
| Paradigma | Pragmatisme |

Adopsi DSR dalam penelitian ini mengikuti kerangka kerja yang diusulkan oleh Peffers et al. (2007), meliputi enam tahapan:

1. **Identifikasi Masalah** — Fragmentasi kurikulum sains lintas disiplin (Fisika, Kimia, Biologi) menyebabkan siswa kesulitan melihat keterhubungan konsep
2. **Definisi Tujuan** — Mengembangkan sistem yang dapat menemukan relasi implisit antar-konsep lintas mata pelajaran
3. **Desain dan Pengembangan** — Membangun pipeline ekstraksi-konstruksi-kompletion *knowledge graph*
4. **Demonstrasi** — Implementasi purwarupa dengan data buku teks Kemendikbudristek
5. **Evaluasi** — Pengukuran metrik struktural (ADC, Modularity) dan validasi pakar
6. **Komunikasi** — Dokumentasi dalam bentuk skripsi dan publikasi ilmiah

---

## 3.2 Lokasi dan Waktu Penelitian

### 3.2.1 Lokasi Penelitian

Penelitian ini dilaksanakan secara *online* tanpa melibatkan studi lapangan. Data primer diperoleh dari repositori buku teks elektronik Kementerian Pendidikan, Kebudayaan, Riset, dan Teknologi (Kemendikbudristek) yang dapat diakses melalui portal resmi:

**Sumber Data:** https://buku.kemdikbud.go.id

### 3.2.2 Waktu Penelitian

Penelitian direncanakan berlangsung selama **6 (enam) bulan**, dimulai dari Januari 2026 hingga Juni 2026. Rincian tahapan waktu penelitian disajikan pada Tabel 3.1.

**Tabel 3.1 Jadwal Pelaksanaan Penelitian**

| Fase | Kegiatan | Periode |
|------|----------|---------|
| 1 | Studi literatur dan desain sistem | Januari - Februari 2026 |
| 2 | Implementasi pipeline ekstraksi | Februari - Maret 2026 |
| 3 | Konstruksi *Knowledge Graph* | Maret - April 2026 |
| 4 | *Knowledge Graph Completion* | April 2026 |
| 5 | Evaluasi dan validasi pakar | Mei 2026 |
| 6 | Analisis hasil dan penulisan | Mei - Juni 2026 |

---

## 3.3 Populasi dan Sampel

### 3.3.1 Populasi

Populasi dalam penelitian ini adalah seluruh buku teks elektronik mata pelajaran sains untuk jenjang SMA Fase F (Kelas XI dan XII) dalam Kurikulum Merdeka yang diterbitkan oleh Kemendikbudristek. Kriteria populasi meliputi:

- Buku teks elektronik resmi dari Kemendikbudristek
- Mata pelajaran: Fisika, Kimia, dan Biologi
- Tingkat: Kelas XI dan XII (Fase F)
- Format: PDF (*Portable Document Format*)

### 3.3.2 Sampel

Sampel penelitian dipilih menggunakan teknik **purposive sampling** dengan kriteria:

1. Buku resmi dari repository Kemendikbudristek
2. Kelas XI dan XII (Fase F) sesuai ruang lingkup penelitian
3. Tersedia dalam format PDF yang dapat diproses secara komputasional

Sampel yang digunakan dalam penelitian ini disajikan pada Tabel 3.2.

**Tabel 3.2 Sampel Buku Teks yang Digunakan**

| No | Kode | Judul Buku | Mata Pelajaran | Kelas |
|----|------|------------|----------------|-------|
| 1 | FIS-XI | Buku Siswa Fisika untuk SMA/MA Kelas XI | Fisika | XI |
| 2 | FIS-XII | Buku Siswa Fisika untuk SMA/MA Kelas XII | Fisika | XII |
| 3 | KIM-XI | Buku Siswa Kimia untuk SMA/MA Kelas XI | Kimia | XI |
| 4 | KIM-XII | Buku Siswa Kimia untuk SMA/MA Kelas XII | Kimia | XII |
| 5 | BIO-XI | Buku Siswa Biologi untuk SMA/MA Kelas XI | Biologi | XI |
| 6 | BIO-XII | Buku Siswa Biologi untuk SMA/MA Kelas XII | Biologi | XII |

Total sampel: **6 (enam) buku teks elektronik**

---

## 3.4 Variabel Penelitian dan Definisi Operasional

### 3.4.1 Variabel Penelitian

#### Variabel Independen

Variabel independen dalam penelitian ini meliputi:

| Variabel | Deskripsi | Nilai/Level |
|----------|-----------|-------------|
| Model LLM Ekstraksi | Model bahasa besar yang digunakan untuk ekstraksi konsep | Gemini 2.5 Flash, GPT-4o Mini, Claude 3.5 Haiku, GLM-4.5 Flash |
| Strategi *Prompt Engineering* | Variasi instruksi sistem untuk ekstraksi | default (v3-bloom), minimal, strict, cot (*chain-of-thought*) |
| Model *Embedding* | Model representasi vektor untuk perhitungan similaritas | Gemini Embedding, text-embedding-3-small, multilingual-e5-small |
| Threshold Similaritas | Nilai ambang batas cosine similarity untuk KGC | 0.7 - 0.9 (default: 0.8) |

#### Variabel Dependen

Variabel dependen dalam penelitian ini meliputi:

| Variabel | Deskripsi | Satuan |
|----------|-----------|--------|
| Jumlah Konsep Terekstrak | Total konsep yang berhasil diekstrak per dokumen | Jumlah node |
| Jumlah Relasi Terprediksi | Total relasi implisit yang ditemukan melalui KGC | Jumlah edge |
| *Average Degree Centrality* (ADC) | Rata-rata degree centrality node dalam graf | Nilai 0-1 |
| *Modularity* | Ukuran struktur komunitas dalam graf | Nilai -0.5 hingga 1 |
| Tingkat Validitas Pakar | Persentase relasi yang divalidasi benar oleh pakar | Persentase (%) |

### 3.4.2 Definisi Operasional

**Tabel 3.3 Definisi Operasional Istilah Penelitian**

| Istilah | Definisi Operasional |
|---------|---------------------|
| *Knowledge Graph* | Struktur data graf dalam Neo4j yang terdiri dari node dengan label MataPelajaran, Document, Bab, SubBab, SubSubBab, Konsep, SubKonsep dan edge berupa relasi struktural (hasBab, hasKonsep, dll.) maupun semantik (SIMILAR_TO, isPrerequisiteOf, supports, analogousTo) |
| Konsep | Entitas pengetahuan fisika/kimia/biologi yang memiliki nama, deskripsi, dan tingkat kognitif Bloom (remember, understand, apply, analyze, evaluate, create) |
| SubKonsep | Konten terperinci yang menjelaskan atau mengelaborasi sebuah Konsep, memiliki atribut nama, deskripsi, dan Bloom level |
| Relasi Struktural | Hubungan hierarkis dalam graf: MataPelajaran → Document → Bab → SubBab → SubSubBab → Konsep → SubKonsep |
| Relasi Implisit | Hubungan antar-konsep yang tidak tertulis eksplisit dalam teks buku tetapi dapat diinferensikan melalui analisis semantik LLM |
| KGC (*Knowledge Graph Completion*) | Proses prediksi tripel (head, relation, tail) yang hilang menggunakan embedding similarity dan klasifikasi LLM untuk menghasilkan relasi isPrerequisiteOf, supports, atau analogousTo |
| *Embedding* | Representasi vektor numerik dari deskripsi konsep yang dihasilkan oleh model embedding (dimensi bervariasi tergantung model) |
| *Cosine Similarity* | Ukuran kemiripan antara dua vektor embedding, dihitung sebagai dot product dibagi produktus norma kedua vektor |

---

## 3.5 Kerangka Konsep

Kerangka konsep penelitian ini menggambarkan alur pemrosesan data dari input dokumen kurikulum hingga output knowledge graph terintegrasi. Sistem dibangun dengan arsitektur pipeline 5 tahap yang saling terintegrasi.

### 3.5.1 Diagram Alur Penelitian

```
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT: Kurikulum Merdeka                     │
│         Buku Teks Sains (Fisika, Kimia, Biologi) Kelas XI-XII   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TAHAP 1: INGESTION                              │
│  • Ekstraksi teks dari PDF (pymupdf)                            │
│  • Parsing struktur dokumen (Daftar Isi, Glosarium)             │
│  • Klasifikasi halaman: text vs vision                          │
│  • Filtering konten non-akademik                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TAHAP 2: EXTRACTION                             │
│  • Text chunking (SentenceSplitter, 2048 tokens)                │
│  • LLM-based extraction (LlamaIndex + Pydantic)                 │
│  • Structured output: KonsepExtraction schema                   │
│  • Validasi Bloom's taxonomy                                    │
│  • Disk caching (SHA-256 hash key)                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TAHAP 3: GRAPH CONSTRUCTION                     │
│  • Pembuatan node di Neo4j                                      │
│    - MataPelajaran {name, phase}                                │
│    - Document {name, kelas, uploaded_at}                        │
│    - Bab, SubBab, SubSubBab {name}                              │
│    - Konsep {name, description, bloom_level}                    │
│    - SubKonsep {name, description, bloom_level}                 │
│  • Pembentukan relasi struktural                                │
│    - hasDocument, hasBab, hasSubBab, hasSubSubBab               │
│    - hasKonsep, hasSubKonsep                                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TAHAP 4: GRAPH COMPLETION                       │
│  • Embedding node descriptions (LiteLLM / HuggingFace)          │
│  • Cosine similarity matching (threshold: 0.8)                  │
│  • LLM classification relasi:                                   │
│    - isPrerequisiteOf (ketergantungan urutan)                   │
│    - supports (ketergantungan fungsional)                       │
│    - analogousTo (hubungan struktural lintas disiplin)          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TAHAP 5: EVALUATION                             │
│  • Evaluasi Struktural (Kuantitatif)                            │
│    - Average Degree Centrality (ADC)                            │
│    - Modularity (Newman-Girvan)                                 │
│    - Graph Density                                              │
│  • Validasi Pakar (Kualitatif)                                  │
│    - Human-in-the-loop verification                             │
│    - Likert scale 1-5                                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              OUTPUT: Knowledge Graph Terintegrasi               │
│        Pemetaan Interkoneksi Sains Lintas Disiplin              │
│        (Fisika ↔ Kimia ↔ Biologi)                               │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5.2 Penjelasan Tahapan

**Tahap 1 — Ingestion**
Tahap ini bertanggung jawab untuk mengekstrak konten dari file PDF buku teks. Proses meliputi:
- Ekstraksi teks menggunakan pustaka pymupdf
- Parsing struktur dokumen dari Daftar Isi (Table of Contents) untuk mendapatkan hierarki Bab, SubBab, dan SubSubBab
- Klasifikasi halaman berdasarkan kepadatan teks dan jumlah gambar untuk menentukan metode ekstraksi (text-based atau vision-based)
- Ekstraksi glosarium untuk konteks terminologi

**Tahap 2 — Extraction**
Tahap ini menggunakan LLM untuk mengekstrak konsep dan sub-konsep dari teks yang telah di-*chunk*:
- *Text chunking* menggunakan SentenceSplitter dengan ukuran 2048 token dan overlap 128 token
- Ekstraksi terstruktur menggunakan LlamaIndex LLMTextCompletionProgram dengan validasi schema Pydantic
- Setiap konsep dan sub-konsep dilengkapi dengan tingkat kognitif Bloom
- Hasil ekstraksi di-*cache* ke disk untuk menghindari pemanggilan API berulang

**Tahap 3 — Graph Construction**
Tahap ini membangun struktur graf dalam Neo4j:
- Pembuatan node dengan label dan properti yang sesuai
- Pembentukan relasi struktural berdasarkan hierarki dokumen
- Node Konsep bersifat *shared* (MERGE berdasarkan nama) untuk memungkinkan penghubungan lintas dokumen

**Tahap 4 — Graph Completion**
Tahap ini menemukan relasi implisit antar-konsep:
- Embedding deskripsi konsep menggunakan model embedding
- Pencarian pasangan serupa berdasarkan cosine similarity di atas threshold
- Klasifikasi relasi oleh LLM ke dalam tiga tipe:
  - `isPrerequisiteOf`: Konsep A harus dipelajari sebelum B
  - `supports`: Konsep A mendukung pemahaman B
  - `analogousTo`: Konsep A dan B memiliki pola/prinsip serupa (lintas disiplin)

**Tahap 5 — Evaluation**
Tahap ini mengukur kualitas knowledge graph yang dihasilkan:
- Evaluasi struktural menggunakan metrik graf (ADC, Modularity, Density)
- Validasi kualitatif oleh pakar menggunakan skala Likert

---

## 3.6 Teknik Pengumpulan Data

### 3.6.1 Studi Literatur

Pengumpulan data sekunder dilakukan melalui studi literatur dari berbagai sumber:

| Sumber | Deskripsi |
|--------|-----------|
| Jurnal Ilmiah | IEEE, ACM, dan jurnal terindeks Scopus terkait Knowledge Graph, LLM, dan pendidikan |
| Prosiding Konferensi | AAAI, IJCAI, KDD, dan konferensi terkait NLP serta educational technology |
| Dokumen Resmi | Dokumen Capaian Pembelajaran Kurikulum Merdeka dari Kemendikbudristek |
| Repositori Kode | GitHub untuk referensi implementasi dan best practices |

### 3.6.2 Dokumentasi Sekunder

Data primer penelitian berupa buku teks elektronik diperoleh dari:
- Portal buku elektronik Kemendikbudristek (https://buku.kemdikbud.go.id)
- Format: PDF dengan lisensi CC BY-NC-SA 4.0 untuk keperluan pendidikan

### 3.6.3 Eksperimen Komputasional

Data eksperimental dikumpulkan melalui:
1. **Ekstraksi otomatis** — Menjalankan pipeline ekstraksi pada setiap dokumen sampel
2. **Pembangunan graf iteratif** — Konstruksi knowledge graph secara bertahap
3. **Eksperimen parameter** — Pengujian berbagai kombinasi model LLM, strategi prompt, dan threshold similaritas
4. **Pencatatan metrik** — Logging otomatis jumlah node, edge, dan metrik evaluasi

---

## 3.7 Alat dan Bahan

### 3.7.1 Perangkat Keras

Eksperimen komputasional dilakukan menggunakan komputer dengan spesifikasi:

| Komponen | Spesifikasi |
|----------|-------------|
| Prosesor | [Diisi sesuai perangkat aktual] |
| Memori RAM | [Diisi sesuai perangkat aktual] |
| Penyimpanan | SSD dengan kapasitas minimal 256 GB |
| Koneksi Internet | Stabil untuk akses API LLM |

### 3.7.2 Perangkat Lunak

**Tabel 3.4 Daftar Perangkat Lunak yang Digunakan**

| Komponen | Teknologi | Versi | Fungsi |
|----------|-----------|-------|--------|
| LLM Backend | litellm | ≥1.0 | Multi-provider LLM access (Gemini, OpenAI, Anthropic, z.ai) |
| Framework | LlamaIndex | ≥0.10 | Orkestrasi ekstraksi terstruktur dengan LLM |
| Graph Database | Neo4j (Aura) | 5.x | Penyimpanan dan kueri knowledge graph |
| Embedding | HuggingFace / Gemini | - | Representasi vektor deskripsi konsep |
| PDF Processing | pymupdf | ≥1.24 | Ekstraksi teks dan rendering halaman |
| Backend | Python | 3.11+ | Implementasi inti sistem |
| Frontend | Streamlit | ≥1.30 | Antarmuka pengguna dan visualisasi |
| Graph Analysis | NetworkX | ≥3.0 | Perhitungan metrik graf (ADC, Modularity) |
| Data Validation | Pydantic | ≥2.0 | Schema validation untuk output LLM |
| Environment | uv | - | Manajemen dependensi Python |
| Version Control | Git | - | Pengelolaan kode sumber |

### 3.7.3 Model yang Digunakan

**Tabel 3.5 Model LLM untuk Ekstraksi**

| Model | Provider | Kegunaan |
|-------|----------|----------|
| Gemini 2.5 Flash | Google AI | Ekstraksi default (utama) |
| GPT-4o Mini | OpenAI | Alternatif ekstraksi |
| Claude 3.5 Haiku | Anthropic | Alternatif ekstraksi |
| GLM-4.5 Flash | z.ai | Opsi gratis |

**Tabel 3.6 Model untuk Embedding**

| Model | Provider | Dimensi |
|-------|----------|---------|
| Gemini Embedding | Google AI | 768 |
| text-embedding-3-small | OpenAI | 1536 |
| multilingual-e5-small | HuggingFace | 384 |
| Qwen3-Embedding-8B | HuggingFace | 1024 |

### 3.7.4 Strategi Prompt Engineering

Penelitian ini menguji empat strategi prompt untuk ekstraksi konsep:

| Strategi | Versi | Deskripsi |
|----------|-------|-----------|
| default | v3-bloom | Prompt lengkap dengan ontologi Indonesia dan Bloom's taxonomy |
| minimal | v2-minimal | Prompt dasar sebagai baseline perbandingan |
| strict | v2-strict | Enforce hierarki ketat (setiap Konsep wajib punya SubKonsep) |
| cot | v2-cot | Chain-of-thought untuk ekstraksi sistematis bertahap |

---

## 3.8 Teknik Analisis Data

### 3.8.1 Evaluasi Struktural (Kuantitatif)

Evaluasi struktural dilakukan untuk mengukur kualitas topologi knowledge graph yang dihasilkan. Metrik yang digunakan meliputi:

#### Average Degree Centrality (ADC)

*Average Degree Centrality* mengukur rata-rata jumlah koneksi per node dalam graf, menunjukkan tingkat interkoneksi konsep.

**Rumus:**

$$ADC = \frac{1}{N} \sum_{i=1}^{N} \frac{d_i}{N-1}$$

**Keterangan:**
- $N$ = jumlah node dalam graf
- $d_i$ = degree (jumlah edge) dari node ke-$i$

**Interpretasi:**
- Nilai ADC tinggi menunjukkan graf yang padat dengan banyak interkoneksi
- Nilai ADC rendah menunjukkan graf yang sparse

#### Modularity (Newman-Girvan)

*Modularity* mengukur seberapa baik graf terbagi menjadi komunitas-komunitas yang terpisah. Metrik ini penting untuk mengukur tingkat keterpisahan antar-disiplin ilmu.

**Rumus:**

$$Q = \frac{1}{2m} \sum_{ij} \left[ A_{ij} - \frac{k_i k_j}{2m} \right] \delta(c_i, c_j)$$

**Keterangan:**
- $A_{ij}$ = elemen matriks adjacensi (1 jika ada edge, 0 jika tidak)
- $k_i, k_j$ = degree dari node $i$ dan $j$
- $m$ = jumlah total edge
- $\delta(c_i, c_j)$ = 1 jika node $i$ dan $j$ dalam komunitas yang sama, 0 jika tidak

**Interpretasi:**
- $Q \approx 0$ → Struktur komunitas tidak jelas (graf terintegrasi)
- $Q > 0.3$ → Struktur komunitas moderat
- $Q > 0.7$ → Komunitas terpisah dengan jelas (silo)

#### Graph Density

*Density* mengukur rasio jumlah edge aktual terhadap jumlah edge maksimum yang mungkin.

**Rumus:**

$$D = \frac{2|E|}{|V|(|V|-1)}$$

**Keterangan:**
- $|E|$ = jumlah edge
- $|V|$ = jumlah node

### 3.8.2 Validasi Pakar (Kualitatif)

Validasi kualitatif dilakukan menggunakan pendekatan **human-in-the-loop** dengan melibatkan ahli materi (guru atau dosen) untuk menilai validitas relasi yang diprediksi oleh sistem.

#### Prosedur Validasi

1. **Sampel relasi** — Dipilih secara acak dari relasi yang diprediksi oleh KGC
2. **Presentasi** — Relasi ditampilkan dengan konteks: konsep A, konsep B, tipe relasi, dan deskripsi
3. **Penilaian** — Validator menilai menggunakan skala Likert 1-5

**Skala Likert Validitas Relasi:**

| Skor | Kategori | Deskripsi |
|------|----------|-----------|
| 1 | Sangat Tidak Valid | Relasi salah atau tidak relevan |
| 2 | Tidak Valid | Relasi kurang tepat |
| 3 | Netral | Relasi dapat diterima dengan keberatan |
| 4 | Valid | Relasi tepat |
| 5 | Sangat Valid | Relasi sangat tepat dan bermakna |

#### Metrik Validasi

- **Precision@k** — Proporsi relasi dengan skor ≥ 4 dari total k relasi yang divalidasi
- **Inter-rater Reliability** — Koefisien Cohen's Kappa jika lebih dari satu validator

### 3.8.3 Analisis Perbandingan

Analisis perbandingan dilakukan untuk mengevaluasi efektivitas KGC:

1. **Before/After KGC** — Perbandingan metrik graf sebelum dan sesudah completion
2. **Cross-subject discovery rate** — Persentase relasi yang menghubungkan konsep dari mata pelajaran berbeda
3. **Ablation study** — Pengujian kontribusi setiap komponen (embedding, threshold, LLM classification)

---

## 3.9 Alur Penelitian

Alur penelitian secara keseluruhan dapat dirangkum sebagai berikut:

1. **Persiapan**
   - Pengumpulan dan unduh buku teks elektronik dari portal Kemendikbudristek
   - Konfigurasi lingkungan pengembangan dan API keys

2. **Implementasi Sistem**
   - Pengembangan modul ingestion dengan pymupdf
   - Implementasi pipeline ekstraksi dengan LlamaIndex dan Pydantic
   - Konstruksi graph database dengan Neo4j
   - Implementasi algoritma KGC dengan embedding similarity dan LLM classification

3. **Eksperimen**
   - Eksekusi ekstraksi pada 6 dokumen sampel
   - Konstruksi knowledge graph
   - Pelaksanaan KGC dengan variasi parameter
   - Pencatatan hasil dan metrik

4. **Evaluasi**
   - Perhitungan metrik struktural (ADC, Modularity, Density)
   - Validasi relasi oleh pakar
   - Analisis temuan relasi lintas disiplin

5. **Pelaporan**
   - Dokumentasi hasil dalam bentuk skripsi
   - Penyusunan rekomendasi untuk penelitian lanjutan

---

*Referensi bab ini:*

- Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design science in information systems research. *MIS Quarterly*, 28(1), 75-105.
- Peffers, K., Tuunanen, T., Rothenberger, M. A., & Chatterjee, S. (2007). A design science research methodology for information systems research. *Journal of Management Information Systems*, 24(3), 45-77.
