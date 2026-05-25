"""
Add expert-fisika-4's proposed missing triples to extraction-v4-validated-byCC.

15 proposed triples from expert-fisika-4.json:
  - 4 already covered by CC additions (Inframerah x2, Dilatasi, Penambahan Kecepatan) → skip concept creation, add extra relations where new info exists
  - 5 new concepts to create
  - 6 new relations to add to existing concepts
"""

import json
from pathlib import Path
from datetime import date

BASE = Path(__file__).resolve().parent.parent / "knowledge_graph_states" / "extraction-v4-validated-byCC"

REVIEW_STUB = {
    "status": "proposed",
    "consensus": "proposed",
    "n_reviewers": 1,
    "ratings": {"expert-fisika-4": "proposed"},
    "comments": {}
}

def make_rel(rel_type, target, description):
    return {
        "type": rel_type,
        "target": target,
        "description": description,
        "provenance": "expert-proposed-fisika-4",
        "expert_review": {**REVIEW_STUB}
    }

def make_concept(name, description, materi_pokok_ref, relations):
    return {
        "name": name,
        "description": description,
        "glossary_validated": False,
        "materi_pokok_ref": materi_pokok_ref,
        "provenance": "expert-proposed-fisika-4",
        "relations": relations
    }

# ── New concepts (5) ─────────────────────────────────────────────────

NEW_CONCEPTS = [
    (
        "LISTRIK STATIS",
        "C. Kapasitor Keping Sejajar",
        make_concept(
            "Muatan Kapasitor dan Beda Potensial Pelat Paralel",
            "Muatan listrik (Q) yang tersimpan di dalam kapasitor keping sejajar berbanding "
            "lurus dengan nilai kapasitansi (C) dan beda potensial atau tegangan (V) yang "
            "diberikan, dirumuskan sebagai Q = C . V. Beda potensial (V) antara dua pelat "
            "paralel yang sejajar berjarak d di dalam medan listrik homogen E dihitung dengan "
            "rumus V = E . d.",
            "Kapasitor Keping Sejajar",
            [
                make_rel("DIFORMULASIKAN_SEBAGAI", "Q = C . V",
                         "Muatan tersimpan kapasitor berbanding lurus dengan kapasitansi dan tegangan."),
                make_rel("DIFORMULASIKAN_SEBAGAI", "V = E . d",
                         "Beda potensial pelat paralel sama dengan medan listrik dikali jarak antar pelat."),
            ]
        )
    ),
    (
        "LISTRIK ARUS SEARAH",
        "D. Rangkaian Listrik",
        make_concept(
            "Alat Ukur Listrik",
            "Amperemeter digunakan untuk mengukur kuat arus listrik dan harus dipasang "
            "secara seri dalam rangkaian, sedangkan voltmeter digunakan untuk mengukur beda "
            "potensial (tegangan) dan harus dipasang secara paralel.",
            "Rangkaian Listrik",
            [
                make_rel("TERDIRI_DARI", "Amperemeter",
                         "Amperemeter mengukur kuat arus listrik, dipasang seri dalam rangkaian."),
                make_rel("TERDIRI_DARI", "Voltmeter",
                         "Voltmeter mengukur beda potensial (tegangan), dipasang paralel dalam rangkaian."),
            ]
        )
    ),
    (
        "KEMAGNETAN",
        "G. Induktansi dan Transformator",
        make_concept(
            "Efisiensi Transformator",
            "Efisiensi transformator (eta) dihitung dengan membandingkan daya keluar sekunder "
            "(Ps) dengan daya masuk primer (Pp) dikali seratus persen, dirumuskan sebagai "
            "eta = (Vs . Is) / (Vp . Ip) x 100%.",
            "Induktansi dan Transformator",
            [
                make_rel("DIFORMULASIKAN_SEBAGAI", "eta = (Vs . Is) / (Vp . Ip) x 100%",
                         "Efisiensi trafo adalah perbandingan daya output sekunder terhadap daya input primer."),
                make_rel("BERGANTUNG_PADA", "Prinsip Kerja Transformator",
                         "Efisiensi transformator bergantung pada prinsip kerja induksi elektromagnetik "
                         "antara kumparan primer dan sekunder."),
            ]
        )
    ),
    (
        "ARUS BOLAK-BALIK",
        "A. Persamaan Arus Bolak Balik",
        make_concept(
            "Nilai Efektif Arus dan Tegangan AC",
            "Nilai efektif dari arus dan tegangan bolak-balik dihitung dengan membagi nilai "
            "maksimumnya dengan akar dua, dirumuskan sebagai Ief = Imaks / akar(2) dan "
            "Vef = Vmaks / akar(2).",
            "Persamaan Arus Bolak Balik",
            [
                make_rel("DIFORMULASIKAN_SEBAGAI", "Ief = Imaks / akar(2)",
                         "Arus efektif AC dihitung dari amplitudo arus dibagi akar dua."),
                make_rel("DIFORMULASIKAN_SEBAGAI", "Vef = Vmaks / akar(2)",
                         "Tegangan efektif AC dihitung dari amplitudo tegangan dibagi akar dua."),
            ]
        )
    ),
    (
        "GEJALA KUANTUM",
        "B. Efek Fotolistrik",
        make_concept(
            "Dualisme Gelombang-Partikel",
            "Fenomena efek fotolistrik dan efek Compton secara empiris membuktikan bahwa "
            "gelombang elektromagnetik atau cahaya memiliki sifat dualisme, yaitu dapat "
            "berperilaku sebagai partikel (foton) yang membawa momentum.",
            "Konsep Foton",
            [
                make_rel("DIBUKTIKAN_OLEH", "Efek Fotolistrik",
                         "Efek fotolistrik membuktikan sifat partikel cahaya melalui pelepasan "
                         "elektron oleh foton."),
                make_rel("DIBUKTIKAN_OLEH", "Efek Compton",
                         "Efek Compton membuktikan sifat partikel cahaya melalui hamburan foton "
                         "dan transfer momentum."),
            ]
        )
    ),
]

# ── New relations on existing concepts (6) ───────────────────────────

EXTRA_RELATIONS = [
    # (concept_name, new_relation)
    ("Gerbang Logika Dasar",
     make_rel("TERDIRI_DARI", "Gerbang XOR",
              "Gerbang XOR (Exclusive OR) menghasilkan sinyal keluaran berlogika tinggi (1) "
              "hanya jika kedua masukannya memiliki nilai biner yang berbeda.")),

    ("Gerak Relatif Newton",
     make_rel("MENGGUNAKAN", "Transformasi Galileo",
              "Relativitas klasik Newton menggunakan Transformasi Galileo untuk menghubungkan "
              "koordinat antar kerangka acuan inersial.")),

    ("Pembangkitan Sinar-X",
     make_rel("DIFORMULASIKAN_SEBAGAI", "lambda_min = (h . c) / (e . V)",
              "Panjang gelombang terpendek sinar-X berbanding terbalik dengan tegangan "
              "pemercepat, dirumuskan sebagai lambda_min = hc/eV.")),

    ("Peluruhan (radioaktif)",
     make_rel("DIFORMULASIKAN_SEBAGAI", "Nt = N0 . (1/2)^(t / t1/2)",
              "Jumlah inti radioaktif tersisa setelah waktu t dihitung menggunakan rumus "
              "peluruhan eksponensial.")),

    ("Defek Massa",
     make_rel("DIFORMULASIKAN_SEBAGAI", "Delta_m = (Z.mp + (A-Z).mn) - m_inti",
              "Defek massa dihitung dari selisih massa total nukleon penyusun dengan massa "
              "inti atom yang terbentuk.")),

    ("Pemanfaatan Inframerah",
     make_rel("MEMUNGKINKAN", "Terapi Fisik Medis",
              "Sinar inframerah dimanfaatkan dalam bidang kesehatan untuk terapi fisik "
              "mematangkan jaringan sirkulasi darah melalui efek radiasi panasnya.")),
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


def find_concept(data, concept_name):
    for ch in data["chapters"]:
        for st in ch["subtopics"]:
            for c in st["concepts"]:
                if c["name"].lower() == concept_name.lower():
                    return c
    return None


def main():
    path = BASE / "Fisika Kelas XII.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    added_concepts = 0
    added_relations = 0
    skipped = 0

    # Add new concepts
    print("=== Adding new concepts ===")
    for chapter_name, subtopic_name, concept in NEW_CONCEPTS:
        if concept_exists(data, concept["name"]):
            print(f"  SKIP (exists): {concept['name']}")
            skipped += 1
            continue
        st = find_subtopic(data, chapter_name, subtopic_name)
        if st is None:
            print(f"  ERROR: subtopic not found: {chapter_name} / {subtopic_name}")
            continue
        st["concepts"].append(concept)
        added_concepts += 1
        print(f"  ADDED: {concept['name']} -> {st['name']}")

    # Add extra relations to existing concepts
    print("\n=== Adding relations to existing concepts ===")
    for concept_name, relation in EXTRA_RELATIONS:
        c = find_concept(data, concept_name)
        if c is None:
            print(f"  ERROR: concept not found: {concept_name}")
            continue
        # Check if relation target already exists
        existing_targets = {r["target"] for r in c["relations"]}
        if relation["target"] in existing_targets:
            print(f"  SKIP (rel exists): {concept_name} -> {relation['target']}")
            skipped += 1
            continue
        c["relations"].append(relation)
        added_relations += 1
        print(f"  ADDED REL: {concept_name} -> {relation['target']}")

    # Write back
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Update manifest
    manifest_path = BASE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = "extraction-v4-validated-byCC"
    manifest["source_state"] = "extraction-v3-toc-gap-byCC"
    manifest["built_at"] = str(date.today())
    manifest["built_by"] = "Claude Code (Opus 4.7)"
    manifest["per_grade"]["Fisika Kelas XII"]["added"] = (
        manifest["per_grade"]["Fisika Kelas XII"].get("added", 0) + added_concepts
    )
    manifest["expert_fisika_4_integration"] = {
        "date": str(date.today()),
        "source_file": "expert-fisika-4.json",
        "reviewer_ratings": "239 correct, 1 missing (out of 240)",
        "new_concepts_added": added_concepts,
        "new_relations_added": added_relations,
        "cc_concepts_validated": "3/5 CC additions independently confirmed (Inframerah, Dilatasi Waktu, Penambahan Kecepatan)",
        "bio_review": "expert-biologi-4: 151/151 correct, 0 missing triples, 2 cosmetic comments"
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== Done: {added_concepts} concepts, {added_relations} relations added, {skipped} skipped ===")


if __name__ == "__main__":
    main()
