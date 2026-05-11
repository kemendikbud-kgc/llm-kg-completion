"""Build the batchUpdate request body for §4.1.4 + Tabel 4.1/4.3 corrections.

Index references (verified by thesis_doc_inspect.py against fresh doc fetch):
  - Tabel 4.1 row 3 cell 1 "Fisika\n": [73000, 73008) — replace with "Kimia"
  - Tabel 4.3 row 3 cell 1 "Fisika\n": [74136, 74144) — replace with "Kimia"
  - §4.1.4 heading endIndex 74695 = §4.1.5 heading startIndex (zero body content)
  - Inserting at 74695 pushes §4.1.5 down; must apply NORMAL_TEXT style to inserted range
    because the insertion point inherits HEADING_3 from §4.1.5.

Processing order: largest-index first so lower-index ops keep their original positions.
"""
from __future__ import annotations

import json
from pathlib import Path

DOC_FRESH = Path(r"D:\codebases\llm-kg-completion\.thesis-fresh.json")
OUT_REQUEST = Path(r"D:\codebases\llm-kg-completion\.thesis-batchupdate.json")

REVISION_ID = json.loads(DOC_FRESH.read_text(encoding="utf-8"))["revisionId"]

# Body paragraphs for §4.1.4. Each \n creates a new paragraph in Docs.
BODY_414 = "\n".join([
    "Tiga keterbatasan data Fase 1 perlu dicatat sebelum interpretasi metrik.",
    "Pertama, recall masih terbatas pada satu reviewer. Formula recall yang dirumuskan pada Bab III memerlukan reviewer untuk menambahkan missing triple, yaitu relasi yang menurut pakar seharusnya ada tetapi tidak ditemukan sistem. Pada Fase 1, hanya expert-kimia-6 yang menambahkan missing triple (29 entri), sehingga recall hanya dapat dihitung untuk dataset Kimia: Recall = 0,713 dengan Presisi = 0,837. Selisih 0,124 antara presisi dan recall mengindikasikan adanya celah cakupan sistematis: kurang lebih 13% relasi yang dianggap penting oleh pakar tidak berhasil diekstrak sistem. Reviewer lain belum menambahkan missing triple, sehingga recall belum dapat dihitung untuk dataset Biologi dan Fisika. Recall sebagai metrik agregat baru dapat dilaporkan setelah Fase 2 dengan instruksi eksplisit kepada seluruh reviewer untuk menambahkan triple yang dianggap hilang.",
    "Kedua, inter-rater agreement belum dapat dihitung. Cohen's kappa memerlukan minimal dua reviewer independen yang menilai triple yang sama. Pada Fase 1, Biologi dan Fisika masing-masing memiliki satu reviewer aktif dengan cakupan signifikan, sedangkan Kimia memiliki dua reviewer aktif: expert-kimia-6 dengan cakupan penuh dan expert-fisika-2 dengan cakupan parsial. Perhitungan kappa dijadwalkan untuk Fase 2 setelah cakupan reviewer-pasangan menjadi seimbang pada seluruh mata pelajaran.",
    "Ketiga, cakupan parsial pada tiga reviewer. Tiga dari lima reviewer (expert-biologi-1, expert-fisika-2, dan sebagian expert-biologi-6) belum menyelesaikan seluruh triple yang ditugaskan. Indikator presisi pada reviewer parsial harus diinterpretasikan sebagai snapshot pada subset triple yang telah dinilai, bukan sebagai estimasi presisi keseluruhan dataset.",
    "",  # trailing empty paragraph for breathing space before §4.1.5
])

INSERT_INDEX = 74695
L = len(BODY_414)
print(f"§4.1.4 body length: {L} chars (will push §4.1.5 from index {INSERT_INDEX} to {INSERT_INDEX + L})")

requests = [
    # 1. INSERT §4.1.4 body at largest index first.
    {
        "insertText": {
            "location": {"index": INSERT_INDEX},
            "text": BODY_414,
        }
    },
    # 2. Force NORMAL_TEXT on the just-inserted paragraphs (they inherit HEADING_3 from §4.1.5).
    {
        "updateParagraphStyle": {
            "range": {
                "startIndex": INSERT_INDEX,
                "endIndex": INSERT_INDEX + L,
            },
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            "fields": "namedStyleType",
        }
    },
    # 3. Tabel 4.3 row 3 cell 1: replace "Fisika" with "Kimia" (preserve trailing newline).
    #    Paragraph startIndex = cell.startIndex + 1 (cell.startIndex is a structural marker).
    {"deleteContentRange": {"range": {"startIndex": 74137, "endIndex": 74143}}},
    {"insertText": {"location": {"index": 74137}, "text": "Kimia"}},
    # 4. Tabel 4.1 row 3 cell 1: same correction.
    {"deleteContentRange": {"range": {"startIndex": 73001, "endIndex": 73007}}},
    {"insertText": {"location": {"index": 73001}, "text": "Kimia"}},
]

payload = {
    "requests": requests,
    "writeControl": {"requiredRevisionId": REVISION_ID},
}

OUT_REQUEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nWrote payload to {OUT_REQUEST}")
print(f"Request count: {len(requests)}")
print(f"revisionId pin: {REVISION_ID[:40]}...")
print(f"\nSummary of operations:")
for i, req in enumerate(requests, 1):
    op = list(req.keys())[0]
    body = req[op]
    desc = ""
    if op == "insertText":
        loc = body.get("location", {}).get("index")
        txt_preview = body.get("text", "")[:60].replace("\n", "\\n")
        desc = f"at {loc}: '{txt_preview}{'...' if len(body.get('text','')) > 60 else ''}'"
    elif op == "deleteContentRange":
        r = body.get("range", {})
        desc = f"[{r.get('startIndex')}, {r.get('endIndex')})"
    elif op == "updateParagraphStyle":
        r = body.get("range", {})
        desc = f"[{r.get('startIndex')}, {r.get('endIndex')}) → NORMAL_TEXT"
    print(f"  {i}. {op}: {desc}")
