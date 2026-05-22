# Parameter Sistem — revised based on Yhoga's notebooks

> Source notebooks: `experiments/yhoga/TA_KG/`
> - `TA_KG.ipynb` — base per-chapter extraction
> - `TA_KG_INTERKONEKSI-v1.ipynb` — cross-book-aware extraction (`other_books_concepts` injected)
> - `TA_KG_COMPLETION-v2.ipynb` — orphan-completion (post-extraction KG completion)
>
> Conventions: parameters not set in code use the Google GenAI API defaults (Gemini docs).
> Where a default is in effect we mark it explicitly so a reader can reproduce.

---

## A. Pipeline Tahap Ekstraksi (per-Bab)

| Parameter | Nilai | Sumber |
|---|---|---|
| LLM API | Google GenAI SDK (`google.genai.Client`) | `TA_KG.ipynb` cell 28 |
| Model LLM | `gemini-2.5-flash` (varian base) atau `gemini-2.5-flash-lite` (varian cross-book aware) | `TA_KG.ipynb` cell 28 / `TA_KG_INTERKONEKSI-v1.ipynb` cell 12 |
| `temperature` | **Default API (1.0)** — tidak diset di kode | — |
| `top_p` | **Default API (0.95)** — tidak diset | — |
| `top_k` | **Default API (64)** — tidak diset | — |
| `max_output_tokens` | **Default API (~8192)** — tidak diset | — |
| `response_mime_type` | Tidak diset — output JSON dikembalikan di dalam fenced code block, di-parse via `text.replace("```json","").replace("```","").strip()` | `TA_KG.ipynb` cell 28 |
| `response_schema` | **Tidak diset** — tidak ada penegakan skema; struktur output hanya didorong via instruksi prompt | — |
| Granularitas pemanggilan | **Per-Bab** (semua chunk dalam satu Bab digabung sebagai `chapter_text`, satu pemanggilan LLM per Bab) | `TA_KG.ipynb` cell 31 |
| Konteks yang disuntikkan ke prompt | (i) glosarium buku siswa, (ii) materi pokok buku guru, (iii) daftar subchapter dari TOC, (iv) nama Bab sebelumnya & berikutnya, (v) (varian INTERKONEKSI) ringkasan konsep dari dua buku lain | cell 28 |
| Cache | Tidak ada — setiap pemanggilan menembak API | — |

## B. Pemotongan Dokumen (chunking)

| Parameter | Nilai | Sumber |
|---|---|---|
| Library | LlamaIndex `SentenceSplitter` | `TA_KG.ipynb` cells 6, 7 |
| `chunk_size` | 800 token | cell 6 |
| `chunk_overlap` | 200 token | cell 6 |
| Catatan | Chunk hanya dipakai sebagai unit baca; pemanggilan LLM tetap di tingkat Bab (chunk se-Bab di-concat) | cell 31 |

## C. Kosakata Relasi yang Diizinkan (intra-buku)

Vokabulari relasi disebutkan di **prompt instruksi** saja — tidak dipenegakan oleh skema:

```
MENDEFINISIKAN, MENYEBABKAN, MEMUNGKINKAN, MENGATUR, BAGIAN_DARI,
TERDIRI_DARI, BERGANTUNG_PADA, BERINTERAKSI_DENGAN, BEREAKSI_DENGAN,
MENGHASILKAN, MEMPENGARUHI, TERLETAK_DI, DIFORMULASIKAN_SEBAGAI,
DIKATALISIS_OLEH, MEMILIKI_SIFAT
```

15 tipe relasi *yang dianjurkan*, namun karena `response_schema` tidak diset,
LLM bebas menghasilkan tipe lain. Empiris di output `.json` boosted:
38 tipe relasi unik di Biologi, 33 di Fisika — termasuk kasus tipo
(`Disebabkan_oleh`, `Dihasilkan_dari`) — konsisten dengan tidak adanya
penegakan skema.

## D. Pipeline Tahap Completion (orphan completion, post-ekstraksi)

| Parameter | Nilai | Sumber |
|---|---|---|
| Model embedding | `paraphrase-multilingual-mpnet-base-v2` (Sentence-Transformers) | `TA_KG_COMPLETION-v2.ipynb` cell 2 |
| Dimensi embedding | 768 | default model |
| Normalisasi | `normalize_embeddings=True` (unit-norm) | cell 9 |
| `batch_size` (embed) | 32 | cell 9 |
| Indeks kemiripan | Dot product NumPy atas embedding ter-normalisasi (bukan Neo4j vector index) | cell 11/13 |
| `COS_THRESHOLD` | 0.75 | cell 2 |
| `TOP_K` | 5 kandidat per orphan | cell 2 |
| `CONF_THRESHOLD` | 0.7 (min confidence LLM agar relasi diterima) | cell 2 |
| `MIN_DEGREE_FOR_SKIP` | 1 (skip konsep yang sudah punya ≥1 relasi nyata) | cell 2 |
| Model LLM classifier | `gemini-2.5-flash-lite` | cell 2 |
| `temperature` (classifier) | **0.2** | cell 15 |
| `system_instruction` | Diset (definisi 6 tipe relasi + aturan direction/symmetric/NONE) | cell 15 |
| `response_mime_type` (classifier) | `application/json` | cell 15 |
| `response_schema` (classifier) | **Diset** — JSON Schema dengan `enum` untuk `relation_type` dan `direction`; `required` untuk semua 5 field | cell 15 |
| Kosakata relasi (closed) | 6 tipe + `NONE`: `BAGIAN_DARI`, `MENYEBABKAN`, `MEMUNGKINKAN`, `PRASYARAT_UNTUK`, `APLIKASI_DARI`, `ANALOGI_DENGAN` | cell 2 |
| Struktur direction | `A_TO_B` / `B_TO_A` / `SYMMETRIC` | cell 15 |
| Tipe asimetris | `BAGIAN_DARI`, `MENYEBABKAN`, `MEMUNGKINKAN`, `PRASYARAT_UNTUK`, `APLIKASI_DARI` | cell 2 |
| Tipe hierarkis (cycle-checked) | `BAGIAN_DARI`, `PRASYARAT_UNTUK` | cell 2 |

## E. Sumber Data

| Parameter | Nilai |
|---|---|
| Korpus utama | Biologi Kelas XII, Fisika Kelas XII, Kimia Kelas XII (buku siswa Kurikulum Merdeka) |
| Korpus pendukung | Buku Guru per-mata-pelajaran (untuk `materi_pokok_map`) |
| Format input | PDF → teks (LlamaIndex SimpleDirectoryReader) |
| Pra-pemrosesan | Pembagian per-Bab via TOC, ekstraksi glosarium & materi pokok dari Buku Guru |

---

## Catatan metodologis (untuk ditulis di Bab 3 sebagai narasi singkat)

> Tahap ekstraksi mengandalkan default API Gemini untuk semua parameter generasi
> (`temperature`, `top_p`, `top_k`, `max_output_tokens`) dan **tidak** menggunakan
> penegakan skema (`response_schema`). Struktur output JSON didorong sepenuhnya
> melalui instruksi prompt dan kemudian di-parse setelah menanggalkan fenced code
> block. Akibatnya: (a) hasil ekstraksi memiliki variabilitas run-to-run yang
> mengikuti karakteristik default sampling Gemini, dan (b) kosakata relasi yang
> dihasilkan tidak terbatas pada 15 tipe yang disebutkan di prompt — analisis
> empiris menunjukkan 33–38 tipe unik per buku, termasuk tipo kapitalisasi.
>
> Sebaliknya, tahap completion (`TA_KG_COMPLETION-v2.ipynb`) menggunakan
> `temperature=0.2` dan **`response_schema`** dengan `enum` tertutup pada
> `relation_type` (6 tipe + `NONE`), sehingga hasil completion bersifat
> deterministik-relatif dan tidak memiliki kebocoran kosakata.

## Inkonsistensi yang perlu diselesaikan di Bab 3

1. **Model LLM untuk ekstraksi**: Bab 3 (Formatted Main) saat ini menulis
   `gemini-2.5-flash-lite`. Notebook ekstraksi base (`TA_KG.ipynb`) memakai
   `gemini-2.5-flash`. Varian `flash-lite` hanya dipakai di notebook
   INTERKONEKSI-v1 dan COMPLETION-v2. **Pilih satu** sebagai kanonis untuk
   ekstraksi, dan dokumentasikan varian sebagai ablasi.

2. **Model embedding**: Bab 3 menulis "Gemini Embedding, text-embedding-3-small,
   multilingual-e5-small". Notebook completion-v2 memakai
   `paraphrase-multilingual-mpnet-base-v2`. **Tidak ada satupun** dari tiga
   model yang ditulis di Bab 3 dipakai di notebook. Sesuaikan tabel dengan
   model aktual, atau eksplisit nyatakan bahwa tiga model tsb adalah
   kandidat ablasi yang belum dijalankan.

3. **Threshold similaritas**: Bab 3 menulis "0.7-0.9 (default: 0.8)". Notebook
   completion-v2 memakai `0.75`. Sesuaikan default ke `0.75` atau dokumentasikan
   bahwa `0.8` adalah default thesis-level yang akan diuji terhadap `0.75`
   notebook.

4. **Penegakan skema (structured output)**: Bab 3 menyebut "strict output
   constraints" di kolom "Strategi Prompt Engineering". Faktanya tahap ekstraksi
   **tidak** memakai `response_schema` — hanya tahap completion yang memakai.
   Ubah deskripsi jadi: "Tahap ekstraksi: prompt-driven JSON tanpa schema
   enforcement. Tahap completion: `response_schema` JSON dengan `enum` tertutup."
