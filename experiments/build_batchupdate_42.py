"""Draft §4.2 Pembahasan Kualitatif into the 'Subbab' stub.

Operations:
  1. Delete Lorem ipsum body at [78099, 78544)        (445 chars)
  2. Insert §4.2 body text at 78099                   (new content)
  3. updateParagraphStyle: inserted range → NORMAL_TEXT
     (insertion inherits HEADING_2 from §4.x "Analisis Satu" at position 78099 after delete)
  4. Delete heading text "Subbab" at [78092, 78098)   (6 chars, preserve trailing \n)
  5. Insert "Pembahasan Kualitatif" at 78092          (inherits HEADING_2 — desired)
"""
from __future__ import annotations
import json
from pathlib import Path

DOC_FRESH = Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json")
OUT_REQUEST = Path(r"D:\codebases\llm-kg-completion\.thesis-batchupdate-42.json")

REVISION_ID = json.loads(DOC_FRESH.read_text(encoding="utf-8"))["revisionId"]

# §4.2 body — 4 sub-sections with inline labels (no HEADING_3 styling, KISS).
# User can manually promote labels to HEADING_3 if desired.
BODY_42 = "\n".join([
    "Hasil kuantitatif pada §4.1 menunjukkan presisi rata-rata 0,910 dan recall 0,713 untuk dataset Kimia. Namun, angka agregat tersebut tidak mengungkap pola error sistematis yang ditemukan pakar. Subbab ini menganalisis komentar terbuka pakar (n = 30, mayoritas dari expert-kimia-6) dan missing triple yang diusulkan (n = 29) untuk mengidentifikasi sumber error sistematis serta area domain yang membutuhkan perbaikan prompt ekstraksi.",
    "",
    "4.2.1 Sumber Error Konseptual",
    "Mayoritas koreksi pakar berakar pada penyederhanaan berlebihan oleh sistem terhadap konsep yang sebenarnya bergantung pada konteks fisis tertentu. Tiga contoh menonjol dari expert-kimia-6 mengilustrasikan pola ini.",
    "Pertama, definisi pH (triple 4). Sistem mendefinisikan pH berdasarkan konsentrasi ion hidrogen, namun pakar mengoreksi bahwa secara konvensi, pH didefinisikan berdasarkan aktivitas ion hidrogen (aH+); penggunaan konsentrasi akan menghasilkan galat matematis dalam larutan nyata di laboratorium ketika koefisien aktivitas (gamma) menyimpang dari 1. Kesalahan ini menunjukkan keterbatasan LLM ketika menghadapi konsep yang sederhana pada level teks tetapi memerlukan asumsi laboratorium tersembunyi.",
    "Kedua, pemurnian tembaga (triple 74). Sistem menyebut proses pemurnian tembaga sebagai electroplating, tetapi pakar mengoreksi bahwa pemurnian tembaga sebenarnya dilakukan melalui elektrorefining, bukan teknik pelapisan. Kesalahan terminologis ini bersifat domain-specific dan tidak dapat dideteksi melalui validasi sintaksis karena kedua istilah secara linguistik plausibel pada konteks elektrokimia.",
    "Ketiga, daur ulang polimer termoset (triple 139). Sistem menyatakan termoset dapat didaur ulang melalui pelelehan ulang, namun pakar mengoreksi bahwa termoset tidak dapat dilelehkan ulang karena jaringan silang permanen — termoset tidak dapat didaur ulang secara termal, meskipun masih dapat didaur ulang melalui metode lain. Koreksi ini menyoroti kecenderungan LLM menggeneralisasi properti makro tanpa membedakan mekanisme spesifik di balik properti tersebut.",
    "",
    "4.2.2 Pola \"Kurang Konteks\"",
    "Sebanyak 19 dari 166 triple Kimia (11,4 persen) dinilai sebagai Kurang Konteks oleh expert-kimia-6 — angka tertinggi di antara seluruh reviewer pada Fase 1. Penelusuran komentar pada triple-triple tersebut menunjukkan bahwa kategori ini umumnya muncul ketika sistem menghasilkan pernyataan yang benar pada level ideal-tertutup tetapi tidak menyatakan asumsi pendukungnya secara eksplisit. Sebagai contoh, pada triple 20 mengenai kesetimbangan elektrolit, pakar mencatat bahwa pernyataan tersebut hanya berlaku dengan mengasumsikan nilai gamma (koefisien aktivitas) sama dengan satu. Pola serupa muncul pada triple 22, 25, 27, 28, dan 29, yang seluruhnya menyangkut perbedaan perilaku larutan ideal dan larutan elektrolit nyata. Pola ini mengindikasikan bahwa prompt ekstraksi pada Fase 1 belum cukup menstimulasi LLM untuk mendokumentasikan ruang lingkup keberlakuan konsep (scope of validity), suatu aspek yang krusial dalam sains eksakta tingkat lanjut.",
    "",
    "4.2.3 Kekosongan Cakupan dari Analisis Missing Triple",
    "Sebanyak 29 missing triple yang diusulkan oleh expert-kimia-6 terdistribusi secara tidak merata di empat Bab Kimia, dengan klasterisasi sebagai berikut: Elektrokimia (9 triple, 31,0 persen), Makromolekul Organik (7 triple, 24,1 persen), Gugus Fungsi dalam Senyawa Karbon (7 triple, 24,1 persen), dan Larutan dan Koloid (6 triple, 20,8 persen). Konsentrasi missing triple pada Elektrokimia — meliputi konsep Persamaan Nernst, Hukum Faraday, Deret Elektrokimia, dan Sel Elektrokimia — menunjukkan bahwa sistem secara sistematis mengabaikan rantai kausal kuantitatif yang menjadi inti pembelajaran Bab tersebut. Pola serupa muncul pada Makromolekul Organik: pakar mengusulkan triple untuk hubungan struktural Polimer-Monomer, Vulkanisasi-Ikatan-silang, dan Termoset-Ikatan-silang-permanen, yang merupakan inti pedagogis pengantar kimia polimer namun terlewat oleh sistem ekstraksi.",
    "",
    "4.2.4 Implikasi untuk Perbaikan Prompt Ekstraksi",
    "Tiga pola sistematis di atas — penyederhanaan konseptual, ketidakeksplisitan asumsi keberlakuan, dan kekosongan rantai kausal kuantitatif — menyarankan perbaikan prompt ekstraksi pada tiga arah. Pertama, prompt perlu memuat instruksi eksplisit agar LLM membedakan definisi konvensional dari penyederhanaan pedagogis (misalnya: untuk setiap definisi, sebutkan asumsi laboratorium yang melekat). Kedua, prompt perlu mendorong ekstraksi rantai sebab-akibat kuantitatif, terutama pada Bab dengan hukum-hukum matematis seperti Faraday, Nernst, dan Le Chatelier. Ketiga, prompt perlu memuat daftar terminologi domain-specific yang sering tertukar (electroplating vs. elektrorefining, termoset vs. termoplastik) sebagai disambiguasi a priori, agar kesalahan terminologis dapat dicegah pada tahap ekstraksi.",
    "",
])

# Indices (pre-edit, from .thesis-verify.json after §4.1.5 update):
LOREM_START = 78099
LOREM_END = 78544       # 445 chars
HEADING_START = 78092
HEADING_END = 78098     # 6 chars "Subbab" (preserve trailing \n at 78098)
NEW_HEADING_TEXT = "Pembahasan Kualitatif"

L_body = len(BODY_42)

requests = [
    # 1. Largest-index op first: delete Lorem ipsum.
    {"deleteContentRange": {"range": {"startIndex": LOREM_START, "endIndex": LOREM_END}}},
    # 2. Insert §4.2 body at the same index.
    {"insertText": {"location": {"index": LOREM_START}, "text": BODY_42}},
    # 3. Force inserted paragraphs to NORMAL_TEXT (they inherit HEADING_2 from next paragraph).
    {
        "updateParagraphStyle": {
            "range": {"startIndex": LOREM_START, "endIndex": LOREM_START + L_body},
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            "fields": "namedStyleType",
        }
    },
    # 4. Rename heading: delete "Subbab".
    {"deleteContentRange": {"range": {"startIndex": HEADING_START, "endIndex": HEADING_END}}},
    # 5. Insert new heading text (inherits HEADING_2 — what we want).
    {"insertText": {"location": {"index": HEADING_START}, "text": NEW_HEADING_TEXT}},
]

payload = {
    "requests": requests,
    "writeControl": {"requiredRevisionId": REVISION_ID},
}

OUT_REQUEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"§4.2 body: {L_body} chars (~{len(BODY_42.split())} words)")
print(f"Delete Lorem ipsum: {LOREM_END - LOREM_START} chars")
print(f"Delete 'Subbab': {HEADING_END - HEADING_START} chars")
print(f"Insert 'Pembahasan Kualitatif': {len(NEW_HEADING_TEXT)} chars")
print(f"Net delta in doc: {L_body - (LOREM_END - LOREM_START) - (HEADING_END - HEADING_START) + len(NEW_HEADING_TEXT):+d} chars")
print(f"Wrote: {OUT_REQUEST}")
