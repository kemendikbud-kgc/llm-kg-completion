# BAB 4 Hasil dan Pembahasan

## 4.X Metrik Struktural Knowledge Graph

Berdasarkan hasil ekstraksi dan penyelesaian graf terhadap tiga buku teks kurikulum merdeka (Fisika, Kimia, Biologi kelas XI), diperoleh statistik struktural sebagai berikut:

### Tabel 4.X.1 Statistik Dasar Knowledge Graph

| Metrik                  | Fisika | Kimia | Biologi | Rata-rata |
|-------------------------|--------|-------|---------|-----------|
| Jumlah Konsep           | -      | -     | -       | -         |
| Jumlah SubKonsep        | -      | -     | -       | -         |
| Jumlah Bab              | -      | -     | -       | -         |
| Jumlah Edge (total)     | -      | -     | -       | -         |
| Jumlah SIMILAR_TO       | -      | -     | -       | -         |
| Jumlah Typed Relations  | -      | -     | -       | -         |

### Tabel 4.X.2 Metrik Kualitas Struktural

| Metrik                        | Fisika | Kimia | Biologi | Target  |
|-------------------------------|--------|-------|---------|---------|
| Average Degree Centrality (ADC)| -     | -     | -       | -       |
| Modularity                    | -      | -     | -       | > 0.3   |
| Density                       | -      | -     | -       | -       |
| Orphan Konsep Rate            | -      | -     | -       | < 0.05  |

### Tabel 4.X.3 Metrik Ekstraksi

| Metrik                        | Fisika | Kimia | Biologi | Target    |
|-------------------------------|--------|-------|---------|-----------|
| Description Completeness      | -      | -     | -       | ≥ 90%     |
| Avg SubKonsep per Konsep      | -      | -     | -       | 2-4       |
| Empty SubKonsep Rate          | -      | -     | -       | < 20%     |

### Tabel 4.X.4 Metrik Hubungan

| Metrik                        | Fisika | Kimia | Biologi | Target    |
|-------------------------------|--------|-------|---------|-----------|
| Typed Relation Ratio          | -      | -     | -       | ≥ 70%     |
| isPrerequisiteOf count        | -      | -     | -       | -         |
| supports count                | -      | -     | -       | -         |
| analogousTo count             | -      | -     | -       | -         |
| Max Prerequisite Chain Length | -      | -     | -       | -         |

### Tabel 4.X.5 Composite Quality Score

| Komponen                 | Bobot | Skor Fisika | Skor Kimia | Skor Biologi |
|--------------------------|-------|-------------|------------|--------------|
| Extraction Score ($S_1$) | 0.30  | -           | -          | -            |
| Structure Score ($S_2$)  | 0.25  | -           | -          | -            |
| Relationship Score ($S_3$)| 0.25  | -           | -          | -            |
| Curriculum Score ($S_4$) | 0.20  | -           | -          | -            |
| **Composite Score**      | 1.00  | -           | -          | -            |

---

## 4.X Hasil Validasi Guru

Validasi dilakukan oleh 3 guru SMA (masing-masing 1 guru per mata pelajaran: Fisika, Kimia, Biologi) menggunakan kuesioner Google Forms dengan skala Likert 1-5.

### Tabel 4.X.7 Profil Responden Validasi

| Responden | Mata Pelajaran | Pengalaman Mengajar | Kelas yang Diajar |
|-----------|----------------|---------------------|-------------------|
| Guru 1    | Fisika         | - tahun             | -                 |
| Guru 2    | Kimia          | - tahun             | -                 |
| Guru 3    | Biologi        | - tahun             | -                 |

### Tabel 4.X.8 Hasil Validasi Konsep

| Metrik                        | Mean | Std Dev | 95% CI        | Target |
|-------------------------------|------|---------|---------------|--------|
| Kecocokan Nama Konsep         | -    | -       | [-, -]        | ≥ 4.0  |
| Kelengkapan Deskripsi         | -    | -       | [-, -]        | ≥ 4.0  |
| **Rata-rata Validasi Konsep** | -    | -       | [-, -]        | ≥ 4.0  |

### Tabel 4.X.9 Hasil Validasi Relasi

| Metrik                        | Mean | Std Dev | 95% CI        | Target |
|-------------------------------|------|---------|---------------|--------|
| Validitas Relasi              | -    | -       | [-, -]        | ≥ 3.5  |
| Kesesuaian Pengalaman Mengajar| -    | -       | [-, -]        | ≥ 3.5  |
| **Rata-rata Validasi Relasi** | -    | -       | [-, -]        | ≥ 3.5  |

### Tabel 4.X.10 Penilaian Keseluruhan

| Metrik                              | Mean | Std Dev | 95% CI        |
|-------------------------------------|------|---------|---------------|
| Kualitas Keseluruhan KG             | -    | -       | [-, -]        |
| Kesesuaian Kurikulum Merdeka        | -    | -       | [-, -]        |
| Kegunaan untuk Analisis Kurikulum   | -    | -       | [-, -]        |
| **Tingkat Kesediaan Menggunakan**   | -    | -       | -             |

### Tabel 4.X.11 Ringkasan Metrik Validasi

| Metrik                        | Nilai | Interpretasi        |
|-------------------------------|-------|---------------------|
| Concept Valid Rate (rating ≥ 4)| -%   | -                   |
| Relation Valid Rate (rating ≥ 4)| -%  | -                   |
| Would Use Rate                | -%    | -                   |
| Cohen's Kappa (Inter-rater)   | -     | -                   |

---

## 4.X Pembahasan

*(Isi pembahasan hasil analisis dan interpretasi data di atas)*

### Temuan Utama

1. **Kualitas Ekstraksi**: -
2. **Struktur Graf**: -
3. **Penemuan Hubungan**: -
4. **Validasi Pakar**: -

### Keterbatasan

1. Jumlah validator terbatas (3 guru)
2. Cakupan hanya 3 mata pelajaran IPA
3. Tidak ada gold standard KG untuk perbandingan
