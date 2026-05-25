"""
Add missing KG concepts identified by ToC-vs-KG gap analysis.

Reads extraction-v2-reviewed JSONs, adds new concepts with
provenance="toc-gap-completion", writes back.

Gaps identified:
  Fisika: 5 concepts (Inframerah, Gerak Relatif Newton, Dilatasi Waktu,
          Penambahan Kecepatan, Pengerutan Panjang)
  Kimia:  3 concepts (Stoikiometri Larutan, Perbandingan Sel Volta dan
          Sel Elektrolisis, Mobil Listrik)
  Biologi: 0 (ToC matches KG at chapter/subtopic level)
"""

import json
from pathlib import Path
from datetime import date

BASE = Path(__file__).resolve().parent.parent / "knowledge_graph_states" / "extraction-v2-reviewed"

REVIEW_STUB = {
    "status": "proposed",
    "consensus": "proposed",
    "n_reviewers": 0,
    "ratings": {},
    "comments": {}
}

def make_rel(rel_type, target, description):
    return {
        "type": rel_type,
        "target": target,
        "description": description,
        "provenance": "toc-gap-completion",
        "expert_review": {**REVIEW_STUB}
    }

def make_concept(name, description, materi_pokok_ref, relations):
    return {
        "name": name,
        "description": description,
        "glossary_validated": False,
        "materi_pokok_ref": materi_pokok_ref,
        "provenance": "toc-gap-completion",
        "relations": relations
    }

# ── Fisika gap concepts ──────────────────────────────────────────────

FISIKA_GAPS = [
    # (chapter_name, subtopic_name, concept)
    (
        "GELOMBANG ELEKTROMAGNETIK",
        "D. Pemanfaatan Gelombang Elektromagnetik",
        make_concept(
            "Pemanfaatan Inframerah",
            "Sinar inframerah dimanfaatkan pada remote control dan alat pendeteksi suhu "
            "(termometer inframerah) tanpa harus menyentuh objek yang diukur. Prinsip kerjanya "
            "memanfaatkan fakta bahwa setiap benda di atas 0K memancarkan radiasi inframerah; "
            "radiasi ini dikumpulkan oleh lensa menuju sensor thermofile, kemudian diolah menjadi "
            "data digital dan ditampilkan pada layar sebagai suhu yang terbaca.",
            "Spektrum GEM",
            [
                make_rel(
                    "BAGIAN_DARI",
                    "Spektrum Elektromagnetik",
                    "Inframerah merupakan bagian dari spektrum elektromagnetik dengan panjang "
                    "gelombang antara cahaya tampak dan gelombang mikro."
                ),
                make_rel(
                    "MEMUNGKINKAN",
                    "Pengukuran Suhu Non-Kontak",
                    "Radiasi inframerah yang dipancarkan benda memungkinkan pengukuran suhu "
                    "secara non-kontak menggunakan termometer inframerah."
                ),
            ]
        )
    ),
    (
        "RELATIVITAS",
        "A. Postulat Pertama dan Kedua Einstein",
        make_concept(
            "Gerak Relatif Newton",
            "Teori relativitas Newton mempelajari bagaimana pengukuran besaran fisika "
            "bergantung pada kerangka acuan pengamat. Menurut Newton, suatu benda dikatakan "
            "bergerak apabila kedudukannya berubah terhadap kerangka acuannya. Kerangka acuan "
            "Newton disebut kerangka inersia, yaitu kerangka acuan tempat benda tersebut bergerak, "
            "dan relativitas Newton menyatakan bahwa hukum-hukum mekanika berlaku sama "
            "pada semua kerangka acuan inersial.",
            "Percobaan Michelson Morley",
            [
                make_rel(
                    "MEMPERSIAPKAN",
                    "Postulat Relativitas Khusus Einstein",
                    "Konsep gerak relatif Newton menjadi landasan yang kemudian diperluas oleh "
                    "Einstein melalui postulat relativitas khusus, yang menambahkan keinvarianan "
                    "kecepatan cahaya."
                ),
            ]
        )
    ),
    (
        "RELATIVITAS",
        "B. Dampak Relativitas Einstein",
        make_concept(
            "Dilatasi Waktu",
            "Fenomena relativistik di mana selang waktu yang diamati pada kerangka acuan "
            "yang bergerak relatif terhadap pengamat akan lebih panjang daripada selang waktu "
            "pada kerangka acuan diam (waktu proper). Pemuluran waktu ini dirumuskan sebagai "
            "t = t₀/√(1 − v²/c²), dengan t₀ adalah waktu proper dan v adalah kecepatan relatif "
            "antara dua kerangka acuan.",
            "Transformasi Lorentz",
            [
                make_rel(
                    "BERGANTUNG_PADA",
                    "Faktor Lorentz (γ)",
                    "Besarnya dilatasi waktu ditentukan oleh faktor Lorentz γ = 1/√(1 − v²/c²), "
                    "sehingga efeknya hanya signifikan pada kecepatan mendekati kecepatan cahaya."
                ),
                make_rel(
                    "DIFORMULASIKAN_SEBAGAI",
                    "t = t₀/√(1 − v²/c²)",
                    "Persamaan dilatasi waktu menyatakan hubungan antara selang waktu pada "
                    "kerangka diam (t₀) dan kerangka bergerak (t) dengan kecepatan relatif v."
                ),
            ]
        )
    ),
    (
        "RELATIVITAS",
        "B. Dampak Relativitas Einstein",
        make_concept(
            "Penambahan Kecepatan Relativistik",
            "Aturan penambahan kecepatan yang berlaku pada kecepatan mendekati kecepatan cahaya, "
            "menggantikan penjumlahan kecepatan klasik V = v₁ + v₂ dengan persamaan "
            "V = (v₁ + v₂)/(1 + v₁v₂/c²). Persamaan ini menjamin bahwa kecepatan hasil tidak "
            "pernah melebihi kecepatan cahaya, sesuai postulat kedua Einstein.",
            "Transformasi Lorentz",
            [
                make_rel(
                    "BERGANTUNG_PADA",
                    "Transformasi Lorentz",
                    "Persamaan penambahan kecepatan relativistik diturunkan dari transformasi Lorentz."
                ),
                make_rel(
                    "DIFORMULASIKAN_SEBAGAI",
                    "V = (v₁ + v₂)/(1 + v₁v₂/c²)",
                    "Persamaan kecepatan relativistik yang menggantikan penjumlahan sederhana "
                    "V = v₁ + v₂ pada kecepatan tinggi."
                ),
            ]
        )
    ),
    (
        "RELATIVITAS",
        "B. Dampak Relativitas Einstein",
        make_concept(
            "Pengerutan Panjang",
            "Fenomena relativistik di mana panjang objek yang bergerak dengan kecepatan "
            "mendekati kecepatan cahaya akan terukur lebih pendek dalam arah geraknya oleh "
            "pengamat yang diam. Pertama kali diajukan oleh George F. FitzGerald (1851–1901) "
            "dan Hendrik A. Lorentz (1853–1928), dirumuskan sebagai L = L₀√(1 − v²/c²), "
            "dengan L₀ adalah panjang proper objek saat diam.",
            "Transformasi Lorentz",
            [
                make_rel(
                    "BERGANTUNG_PADA",
                    "Faktor Lorentz (γ)",
                    "Besarnya pengerutan panjang ditentukan oleh faktor Lorentz γ, analog dengan "
                    "dilatasi waktu."
                ),
                make_rel(
                    "DIFORMULASIKAN_SEBAGAI",
                    "L = L₀√(1 − v²/c²)",
                    "Persamaan pengerutan panjang menyatakan bahwa panjang terukur L berkurang "
                    "dari panjang proper L₀ sesuai faktor Lorentz."
                ),
            ]
        )
    ),
]

# ── Kimia gap concepts ───────────────────────────────────────────────

KIMIA_GAPS = [
    (
        "Larutan dan Koloid",
        "C. Kesetimbangan dalam Larutan",
        make_concept(
            "Stoikiometri Larutan",
            "Perhitungan kuantitatif berdasarkan konsep mol dan persamaan reaksi yang terjadi "
            "di dalam larutan. Mencakup tiga jenis reaksi utama: reaksi pengendapan (menghasilkan "
            "endapan seperti CaCO₃ dan BaCO₃), reaksi pembentukan gas (seperti reaksi logam "
            "dengan asam menghasilkan H₂), dan reaksi netralisasi asam basa (menghasilkan garam "
            "dan air). Tahapan perhitungannya meliputi menuliskan persamaan reaksi setara, mengubah "
            "besaran ke mol, menggunakan perbandingan koefisien, dan mengubah mol ke besaran "
            "yang diinginkan.",
            "C. Kesetimbangan dalam Larutan",
            [
                make_rel(
                    "MENGHASILKAN",
                    "Reaksi Pengendapan",
                    "Stoikiometri larutan diterapkan pada reaksi pengendapan untuk menghitung "
                    "massa endapan yang terbentuk berdasarkan konsentrasi dan volume reaktan."
                ),
                make_rel(
                    "BERGANTUNG_PADA",
                    "Titrasi Asam Basa",
                    "Titrasi asam basa merupakan salah satu aplikasi stoikiometri larutan di mana "
                    "perhitungan mol digunakan untuk menentukan konsentrasi larutan yang tidak diketahui."
                ),
            ]
        )
    ),
    (
        "Elektrokimia",
        "C. Sel elektrokimia",
        make_concept(
            "Perbandingan Sel Volta dan Sel Elektrolisis",
            "Perbandingan karakteristik antara sel volta dan sel elektrolisis meliputi: logam "
            "elektrode (dua logam berbeda potensial reaksi vs logam yang sama sebagai katode dan "
            "anode), muatan anode (negatif vs positif), muatan katode (positif vs negatif), "
            "larutan elektrolit (dalam wadah terpisah dihubungkan jembatan garam vs katode dan "
            "anode dalam elektrolit yang sama), perubahan energi (energi potensial kimia → energi "
            "listrik vs aliran sumber listrik eksternal → reaksi kimia berlangsung), dan aplikasi "
            "(baterai kering, aki mobil vs elektrolisis air, pemisahan komponen menjadi senyawanya).",
            "C. Sel elektrokimia",
            [
                make_rel(
                    "TERDIRI_DARI",
                    "Sel Volta",
                    "Sel volta merupakan salah satu tipe sel elektrokimia yang mengubah energi "
                    "kimia menjadi energi listrik secara spontan."
                ),
                make_rel(
                    "TERDIRI_DARI",
                    "Sel Elektrolisis",
                    "Sel elektrolisis merupakan tipe sel elektrokimia yang memerlukan sumber "
                    "listrik eksternal untuk menyebabkan reaksi kimia berlangsung (reaksi non-spontan)."
                ),
            ]
        )
    ),
    (
        "Elektrokimia",
        "E. Aplikasi elektrokimia",
        make_concept(
            "Mobil Listrik",
            "Kendaraan yang menggunakan baterai sebagai sumber energi utama, mengadopsi sel "
            "elektrokimia yang dapat mengkonversi energi kimia menjadi energi listrik dan "
            "sebaliknya. Baterai mobil listrik harus mampu bekerja dalam jangka waktu cukup lama, "
            "memiliki kapasitas daya besar, dan ringan. Jenis baterai yang umum digunakan meliputi "
            "litium-ion, polimer litium, nikel-kadmium, timbal-asam, dan nikel-hidrida logam. "
            "Mobil listrik ramah lingkungan karena tanpa emisi buangan karbon dan memiliki "
            "efisiensi energi yang tinggi.",
            "E. Aplikasi elektrokimia",
            [
                make_rel(
                    "MENGGUNAKAN",
                    "Baterai Litium-ion",
                    "Baterai litium-ion merupakan jenis baterai yang paling banyak digunakan "
                    "pada mobil listrik modern karena densitas energi besar dan waktu operasional panjang."
                ),
                make_rel(
                    "BAGIAN_DARI",
                    "Reaksi Elektrokimia",
                    "Mobil listrik merupakan aplikasi nyata dari prinsip reaksi elektrokimia, "
                    "di mana konversi energi kimia ke listrik digunakan untuk menggerakkan motor."
                ),
            ]
        )
    ),
]


def find_subtopic(data, chapter_name, subtopic_name):
    for ch in data["chapters"]:
        if chapter_name.lower() in ch["chapter"].lower():
            for st in ch["subtopics"]:
                if subtopic_name.lower() in st["name"].lower():
                    return st
    return None


def concept_exists(data, concept_name):
    for ch in data["chapters"]:
        for st in ch["subtopics"]:
            for c in st["concepts"]:
                if c["name"].lower() == concept_name.lower():
                    return True
    return False


def process_file(filename, gaps):
    path = BASE / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    added = 0
    skipped = 0

    for chapter_name, subtopic_name, concept in gaps:
        if concept_exists(data, concept["name"]):
            print(f"  SKIP (already exists): {concept['name']}")
            skipped += 1
            continue

        st = find_subtopic(data, chapter_name, subtopic_name)
        if st is None:
            print(f"  ERROR: subtopic not found: {chapter_name} / {subtopic_name}")
            continue

        st["concepts"].append(concept)
        print(f"  ADDED: {concept['name']} -> {st['name']}")
        added += 1

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    return added, skipped


def update_manifest(fisika_added, kimia_added):
    path = BASE / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))

    manifest["per_grade"]["Fisika Kelas XII"]["added"] = (
        manifest["per_grade"]["Fisika Kelas XII"].get("added", 0) + fisika_added
    )
    manifest["per_grade"]["Kimia Kelas XII"]["added"] = (
        manifest["per_grade"]["Kimia Kelas XII"].get("added", 0) + kimia_added
    )
    manifest["totals"]["operations"]["add"] = (
        manifest["totals"]["operations"].get("add", 0) + fisika_added + kimia_added
    )
    manifest["toc_gap_completion"] = {
        "date": str(date.today()),
        "fisika_added": fisika_added,
        "kimia_added": kimia_added,
        "biologi_added": 0,
        "method": "ToC-vs-KG gap analysis; descriptions sourced from book PDF pages"
    }

    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n  Manifest updated: +{fisika_added} Fisika, +{kimia_added} Kimia")


if __name__ == "__main__":
    print("=== Adding ToC-gap concepts ===\n")

    print("Fisika Kelas XII:")
    f_added, f_skipped = process_file("Fisika Kelas XII.json", FISIKA_GAPS)

    print("\nKimia Kelas XII:")
    k_added, k_skipped = process_file("Kimia Kelas XII.json", KIMIA_GAPS)

    update_manifest(f_added, k_added)

    print(f"\n=== Done: {f_added + k_added} concepts added, {f_skipped + k_skipped} skipped ===")
