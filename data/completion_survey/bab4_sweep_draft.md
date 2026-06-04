**Parameter Sweep: Pengaruh Threshold dan Top-k**

Pengaruh parameter retrieval terhadap jumlah relasi lintas-buku yang ditemukan dievaluasi pada empat konfigurasi berpasangan, di mana ambang kemiripan (*threshold*) dinaikkan seiring penurunan jumlah tetangga per node (*top-k*). Semakin ketat konfigurasi, semakin sedikit pasangan kandidat yang lolos: dari 101 relasi pada konfigurasi paling permisif (0,70 / k20) menyusut menjadi hanya 14 relasi pada konfigurasi paling ketat (0,85 / k5).

**Tabel 4.x — Jumlah relasi lintas-buku per konfigurasi parameter**

| Konfigurasi (threshold / top-k) | Jumlah relasi |
|---|--:|
| 0,70 / k20 (permisif — konfigurasi final saat ini) | 101 |
| 0,75 / k15 | 72 |
| 0,80 / k10 | 42 |
| 0,85 / k5 (paling ketat) | 14 |

Konfigurasi membentuk himpunan bersarang: setiap konfigurasi yang lebih ketat merupakan himpunan bagian dari yang lebih permisif. Pengetatan parameter dengan demikian berfungsi sebagai kompromi *recall* — menukar cakupan relasi (lebih banyak interkoneksi ditemukan) dengan selektivitas (hanya pasangan berkemiripan tertinggi yang dipertahankan). Sebagaimana dibahas pada Subbab 4.2.3.1, pengetatan ini menurunkan kuantitas relasi tetapi **tidak** memperbaiki ketepatan arah relasi, yang tetap berkisar ~74% di seluruh rentang 0,70–0,80; artinya kesalahan arah tersebar merata pada seluruh rentang kemiripan dan bukan persoalan yang dapat diselesaikan dengan penyetelan *threshold*.

---

> **CATATAN PENEMPATAN (hapus sebelum submit):**
> - **Titik sisip:** gantikan baris placeholder "Parameter sweep: pengaruh threshold dan top-k…" (idx 645), tepat sebelum heading §4.2.3.1.
> - **Caveat angka:** jumlah relasi di atas adalah hasil *re-qualification* dari cache embedding (recompute cosine + rank, tanpa API key), sehingga merupakan estimasi — undercount ~11 relasi yang konsepnya tidak ada di cache. Hitungan eksak per-iterasi memerlukan replay penuh (lihat staged JSON `lintas_buku_edges.tNN_kMM.json`, issue #15).
> - **Konsistensi:** setelah angka ini masuk, perbarui paragraf pembuka §4.2.3.1 yang lama (yang masih menyebut "0,80/k10 → 44 edge") agar selaras dengan tabel ini.
> - **Validitas/tipe:** JANGAN laporkan 100% per-konfigurasi (artefak — 1 relasi invalid + 2 salah-tipe kebetulan ada di himpunan uncomputable). Nilai sebenarnya ~99%/98% (lihat §4.2.3.1).
