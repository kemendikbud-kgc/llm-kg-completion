# Plan — Issue #21: Bab 2 substantive revisions (Siti Aminah)

Doc `1NUFWP1JHmpH...`. Re-fetch revisionId immediately before editing (indices drift).
All targets are **unique substrings** → use `replaceAllText` (no index math needed). One `batchUpdate` with `writeControl.requiredRevisionId`.

Status after re-reading the CURRENT text (§2.1 ~L249–250, §2.x ~L304–306):

| Sub-item | Verdict | Action |
|---|---|---|
| #23 long sentence | Real, present | **Edit E2** |
| #25 long sentence + "dimana" | Real, present (+ typo "tersebut") | **Edit E3** |
| #48 translation-ese run-on | Real, present (grammar broken; ICL already defined) | **Edit E4** |
| #36 "kelangkaan data" framing | Real, present | **Edit E5** |
| #21 ANN transition + "dup sentence" | **Largely addressed** — no literal dup remains; L306 already argues impractical→O(n²)+token limit→ANN | **E1 optional** |
| #49 encoder/generator abrupt | **Addressed** — both defined inline at L250 | italics only → folds into #4 |

---

## E2 — #23 split long sentence (§2.x)
`replaceAllText`:
- **Find:** `pemahaman semantik, model diminta menjawab`
- **Replace:** `pemahaman semantik. Model diminta menjawab`

## E3 — #25 split + remove "dimana" + fix typo (§2.x)
- **Find:**
  `Distribusi topik dalam kurikulum sains SMA bersifat asimetris, dimana konsep-konsep lintas disiplin yang menghubungkan fisika, kimia, dan biologi, misalnya relasi antara termodinamika dengan metabolisme sel, atau antara ikatan kimia dengan sifat mekanik material, cenderung jarang tersebut secara eksplisit dalam satu sumber teks tunggal, sehingga secara struktural masuk ke dalam kategori long-tail dalam graf pengetahuan.`
- **Replace:**
  `Distribusi topik dalam kurikulum sains SMA bersifat asimetris. Konsep-konsep lintas disiplin yang menghubungkan fisika, kimia, dan biologi — misalnya relasi antara termodinamika dengan metabolisme sel, atau antara ikatan kimia dengan sifat mekanik material — cenderung jarang tersurat secara eksplisit dalam satu sumber teks tunggal. Akibatnya, relasi-relasi tersebut secara struktural masuk ke dalam kategori long-tail dalam graf pengetahuan.`

## E4 — #48 fix broken run-on, paraphrase (ICL def retained) (§2.1)
- **Find:**
  `Lebih dari itu, untuk mengatasi kelangkaan informasi pada entitas long-tail, Wei et al. (2023) membuktikan bahwa integrasi LLM melalui strategi In-Context Learning (ICL), yaitu dengan memberikan beberapa contoh triple yang telah benar di dalam prompt sebagai panduan sehingga LLM mampu mempelajari pola dari contoh tersebut dan memprediksi relasi baru tanpa perlu fine-tuning, yang pada akhirnya memungkinkan aktivasi pengetahuan implisit yang telah tertanam dalam model untuk menginferensikan relasi yang tidak mampu ditangkap oleh metode konvensional.`
- **Replace:**
  `Lebih dari itu, Wei et al. (2023) menunjukkan bahwa strategi In-Context Learning (ICL) efektif mengatasi kelangkaan informasi pada entitas long-tail. Dalam strategi ini, beberapa contoh triple yang benar disertakan langsung di dalam prompt sebagai panduan, sehingga LLM dapat mempelajari polanya dan memprediksi relasi baru tanpa proses fine-tuning. Mekanisme tersebut mengaktifkan pengetahuan implisit yang telah tertanam dalam model untuk menginferensikan relasi yang luput dari metode konvensional.`

## E5 — #36 reframe "kelangkaan data" (§2.1)
- **Find:** `yaitu kelangkaan data dan keterbatasan pemetaan relasi.`
- **Replace:** `yaitu kelangkaan relasi eksplisit antar-konsep — bukan kelangkaan materi sumber, yang justru melimpah — serta keterbatasan pemetaan relasi.`

## E1 — #21 (optional) strengthen transition into ANN
Current L306 already builds the argument. If desired, tighten the opener:
- **Find:** `Namun, dalam implementasi komputasionalnya, penerapan LLM secara langsung`
- **Replace:** `Kapasitas semantik tersebut, di sisi lain, menghadirkan tantangan komputasional: penerapan LLM secara langsung`

→ Your call: apply E1, or resolve #21 as already-addressed.

---

## Execution
1. Re-fetch doc → fresh `revisionId`.
2. One `batchUpdate`: `replaceAllText` × {E2, E3, E4, E5 (+E1 if approved)}.
3. Re-fetch → verify each landed; check italic/bold didn't bleed.
4. Reply-resolve comments #23, #25, #48, #36 (+#21, #49).

## Caveat (Drive API)
The Drive comments API can reply but cannot reliably set `resolved`. Resolving may need a manual click in the browser, OR I reply "Done — <change>" and you tick resolve. Confirm preference.
