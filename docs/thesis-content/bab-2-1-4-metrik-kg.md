# BAB 2.1.4 Metrik Evaluasi Knowledge Graph

Evaluasi kualitas Knowledge Graph (KG) merupakan aspek krusial dalam mengukur keberhasilan sistem ekstraksi dan penyelesaian graf yang dibangun. Metrik evaluasi KG dapat dikategorikan menjadi tiga kelompok utama: metrik struktural, metrik ekstraksi, dan metrik hubungan antar-entitas.

## 2.1.4.1 Metrik Struktural

Metrik struktural mengukur karakteristik topologi graf berdasarkan teori graf dan analisis jaringan. Metrik ini bersifat objektif dan dapat dihitung secara otomatis dari struktur graf.

### A. Average Degree Centrality (ADC)

**Average Degree Centrality** mengukur rata-rata jumlah koneksi (derajat) per node dalam graf. Semakin tinggi nilai ADC, semakin terhubung graf tersebut. ADC didefinisikan sebagai:

$$ADC = \frac{1}{|V|} \sum_{v \in V} \frac{deg(v)}{|V| - 1}$$

Di mana $V$ adalah himpunan simpul (node) dan $deg(v)$ adalah jumlah edge yang terhubung ke simpul $v$.

### B. Modularity

**Modularity** ($Q$) mengukur seberapa baik graf terbagi menjadi komunitas-komunitas yang terpisah. Nilai modularity berkisar antara $-0.5$ hingga $1.0$, di mana nilai yang lebih tinggi menunjukkan pembagian komunitas yang lebih baik. Modularity didefinisikan sebagai:

$$Q = \frac{1}{2m}\sum_{ij}\left[A_{ij} - \frac{k_i k_j}{2m}\right]\delta(c_i, c_j)$$

Di mana:
- $A_{ij}$ = matriks adjacensi
- $k_i$ = derajat simpul $i$
- $m$ = total jumlah edge
- $\delta(c_i, c_j) = 1$ jika simpul $i$ dan $j$ berada dalam komunitas yang sama

### C. Graph Density

**Graph Density** mengukur rasio antara jumlah edge yang ada dengan jumlah maksimum edge yang mungkin dalam graf:

$$\rho = \frac{|E|}{|V|(|V| - 1)}$$

Di mana $|E|$ adalah jumlah edge dan $|V|$ adalah jumlah simpul. Density bernilai antara 0 dan 1.

## 2.1.4.2 Metrik Ekstraksi

Metrik ekstraksi mengevaluasi kualitas proses ekstraksi entitas dan atribut dari dokumen sumber.

### A. Description Completeness

**Description Completeness** mengukur persentase entitas yang memiliki deskripsi non-kosong:

$$DC = \frac{|\{e \in E : desc(e) \neq \emptyset\}|}{|E|}$$

Target minimal untuk metrik ini adalah $\geq 0.90$ (90%).

### B. Empty SubKonsep Rate

**Empty SubKonsep Rate** mengukur persentase konsep yang tidak memiliki sub-konsep:

$$ESR = \frac{|\{k \in K : |SK(k)| = 0\}|}{|K|}$$

Nilai yang lebih rendah menunjukkan dekomposisi konsep yang lebih baik.

## 2.1.4.3 Metrik Hubungan

Metrik hubungan mengevaluasi kualitas dan keberagaman relasi antar-entitas dalam KG.

### A. Typed Relation Ratio

**Typed Relation Ratio** mengukur persentase pasangan serupa yang telah diklasifikasikan ke dalam tipe relasi spesifik:

$$TRR = \frac{|T_{typed}|}{|T_{SIMILAR\_TO}|}$$

Target minimal: $\geq 0.70$ (70%).

### B. Prerequisite Chain Length

**Prerequisite Chain Length** mengukur panjang rantai prasyarat maksimum dalam graf, yang menunjukkan kedalaman ketergantungan konseptual:

$$PCL = \max_{path} \{length(p) : p \text{ adalah rantai } isPrerequisiteOf\}$$

## 2.1.4.4 Composite Quality Score

Untuk keperluan evaluasi keseluruhan, metrik-metrik di atas digabungkan menjadi **Composite Quality Score** dengan pembobotan:

$$Q_{composite} = \sum_{i=1}^{4} w_i \cdot S_i$$

Di mana:
- $S_1$ = Skor ekstraksi (description completeness), $w_1 = 0.35$
- $S_2$ = Skor struktur (low orphan rate + good connectivity), $w_2 = 0.30$
- $S_3$ = Skor hubungan (typed ratio + cross-domain), $w_3 = 0.35$
- $S_4$ = Skor kesesuaian kurikulum (pyramid compliance), $w_4 = 0.00$ (dinormalisasi)

Target keseluruhan: $Q_{composite} \geq 0.75$.

## 2.1.4.5 Validasi Manusia (Human Evaluation)

Selain metrik otomatis, validasi oleh pakar domain diperlukan untuk menilai kebenaran semantik dan validitas pedagogis KG. Validasi manusia menggunakan skala Likert 5 poin dan dianalisis menggunakan statistik deskriptif serta **Cohen's Kappa** untuk mengukur kesepakatan antar-penilai:

$$\kappa = \frac{p_o - p_e}{1 - p_e}$$

Di mana $p_o$ adalah proporsi kesepakatan yang diamati dan $p_e$ adalah proporsi kesepakatan yang diharapkan secara kebetulan.

**Interpretasi nilai Kappa:**

| Nilai $\kappa$ | Tingkat Kesepakatan |
|----------------|---------------------|
| < 0.20         | Poor (Sangat Rendah)|
| 0.21 - 0.40    | Fair (Rendah)       |
| 0.41 - 0.60    | Moderate (Sedang)   |
| 0.61 - 0.80    | Good (Baik)         |
| > 0.80         | Excellent (Sangat Baik) |

Tabel 2.X Interpretasi Nilai Cohen's Kappa (Cohen, 1960)
