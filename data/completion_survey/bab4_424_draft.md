### 4.2.4 Analisis Komparatif Antar-Domain Sains

Bagian ini membandingkan ketiga domain sains dari dua sisi: **pola interkoneksi** antar-mata pelajaran (berapa banyak jembatan lintas-buku yang terbentuk antar pasangan disiplin) dan **kualitas ekstraksi** per domain.

**Gambar 4.x** — *Inter-domain bridge graph*. Setiap simpul adalah satu mata pelajaran; ketebalan dan label sisi menyatakan jumlah relasi lintas-buku (LINTAS_BUKU) yang ditemukan antar pasangan disiplin (dari 117 relasi tersurvei).

[SISIPKAN GAMBAR: interdomain_bridges.png]

Distribusi jembatan lintas-disiplin sangat **tidak merata**. Pasangan **Biologi–Kimia mendominasi (91 relasi, 78%)**, diikuti **Fisika–Kimia (21 relasi, 18%)**, sedangkan **Biologi–Fisika nyaris tidak terhubung (5 relasi, 4%)**. Pola ini menempatkan **Kimia sebagai poros (hub)** yang menjembatani kedua disiplin lain. Temuan ini konsisten secara pedagogis: tumpang-tindih molekuler dan biokimiawi (DNA, protein, enzim, reaksi redoks) membuat Biologi dan Kimia berbagi banyak konsep dasar, sementara keterkaitan Fisika sebagian besar terbatas pada elektrokimia (arus dan potensial listrik ↔ sel elektrokimia). Sifat Fisika yang lebih abstrak-matematis menjadikannya domain paling terisolasi dalam jaringan konsep kurikulum kelas XII.

Dari sisi kualitas ekstraksi (validasi Fase 1), terdapat perbedaan antar-domain:

| Domain | Presisi ekstraksi (Fase 1) | Catatan |
|---|--:|---|
| Biologi | ~0,95–0,97 | paling konsisten; konsep deskriptif-naratif |
| Fisika | ~0,86–0,99 | rentang lebar; lemah pada relasi kuantitatif/rumus |
| Kimia | ~0,82–0,92 | kesalahan terbanyak pada terminologi proses (mis. elektrorefining) |

Perbedaan ini selaras dengan analisis kesalahan (§4.2.3): kelemahan utama pada Fisika adalah **under-extraction rumus** (67% missing triples Fisika berupa formula), sedangkan Kimia rentan pada **pencampuran konsep teknis**. Biologi—yang materinya lebih bersifat deskriptif—paling sesuai dengan kekuatan LLM dalam mengekstrak struktur konseptual.

---

> **CATATAN (hapus sebelum submit):**
> - Sisipkan `data/completion_survey/interdomain_bridges.png` sebagai Gambar 4.x.
> - Angka jembatan (91/21/5) = dari 117 relasi tersurvei (run 0,70/k20).
> - Angka presisi Fase 1 adalah rentang antar-penilai dari KG Review App; bersifat indikatif (sebagian mapel hanya 1–2 penilai, ada duplikasi akun fisika-2/kimia-2). Ganti dengan nilai agregat final bila sudah dihitung resmi. Jangan presentasikan sebagai angka tunggal pasti.
