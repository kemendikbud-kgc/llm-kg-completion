"""Replace §4.1.5 placeholder body with real Implikasi for Fase 2.

State after the previous successful batchUpdate (revision pinned from .thesis-verify.json):
  [535] HEADING_3 'Implikasi untuk Fase 2'             ends at 76502
  [536] '\n'                                            [76502, 76503)
  [537] '\n'                                            [76503, 76504)
  [538] Lorem ipsum (446 chars)                         [76504, 76950)
  [539] 'Tabel 4.1 Tabel Kuisioner\n' placeholder       [76950, 76976)
  [540] empty TABLE 2x5 (admin/template)                [76976, 77059)
  [541] HEADING_2 'Subbab' (next sibling)               starts at 77059

Operation: delete [76502, 77059) — 557 chars of template junk + insert real content.
The inserted text will inherit HEADING_2 style from the §4.x "Subbab" heading at the
post-delete position; force NORMAL_TEXT via updateParagraphStyle.
"""
from __future__ import annotations
import json
from pathlib import Path

DOC_FRESH = Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json")
OUT_REQUEST = Path(r"D:\codebases\llm-kg-completion\.thesis-batchupdate-415.json")

REVISION_ID = json.loads(DOC_FRESH.read_text(encoding="utf-8"))["revisionId"]

BODY_415 = "\n".join([
    "Berdasarkan keterbatasan tersebut, Fase 2 pengumpulan data difokuskan pada tiga prioritas.",
    "Pertama, penyelesaian penilaian oleh reviewer yang masih parsial, yaitu expert-biologi-1, expert-fisika-2, dan sebagian expert-biologi-6, agar metrik presisi mencerminkan estimasi yang representatif terhadap keseluruhan dataset dan bukan snapshot pada subset triple yang telah dinilai.",
    "Kedua, penekanan instruksi penambahan missing triple dalam panduan reviewer. Pada Fase 1, hanya satu reviewer (expert-kimia-6) yang menambahkan missing triple, sehingga metrik recall hanya dapat dihitung untuk dataset Kimia. Pada Fase 2, seluruh reviewer akan diberi instruksi eksplisit untuk menambahkan triple yang dianggap hilang, sehingga recall dapat dilaporkan sebagai indikator kelengkapan terpisah dari presisi pada seluruh mata pelajaran.",
    "Ketiga, pengaktifan reviewer kedua pada dataset Biologi dan Fisika agar inter-rater agreement (Cohen's kappa) dapat dihitung pada seluruh mata pelajaran. Untuk Kimia, expert-fisika-6 telah memulai sesi review pada 8 Mei 2026 sebagai reviewer kedua. Apabila penilaian Kimia oleh expert-fisika-6 diselesaikan dengan cakupan yang seimbang terhadap expert-kimia-6, Cohen's kappa dapat dihitung sebagai indikator reproduktibilitas penilaian pakar pada mata pelajaran Kimia.",
    "Selain itu, data Fase 2 akan dilengkapi dengan kutipan komentar pakar terhadap triple individual (terutama 30 komentar terbuka dari expert-kimia-6 pada dataset Kimia) untuk mendukung analisis kualitatif mengenai sumber error sistematis dan area domain yang memerlukan perbaikan prompt ekstraksi.",
    "",
])

DELETE_START = 76502
DELETE_END = 77059
INSERT_INDEX = 76502  # same as DELETE_START
L = len(BODY_415)

requests = [
    {"deleteContentRange": {"range": {"startIndex": DELETE_START, "endIndex": DELETE_END}}},
    {"insertText": {"location": {"index": INSERT_INDEX}, "text": BODY_415}},
    {
        "updateParagraphStyle": {
            "range": {"startIndex": INSERT_INDEX, "endIndex": INSERT_INDEX + L},
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            "fields": "namedStyleType",
        }
    },
]

payload = {
    "requests": requests,
    "writeControl": {"requiredRevisionId": REVISION_ID},
}

OUT_REQUEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Body length: {L} chars")
print(f"Delete range: [{DELETE_START}, {DELETE_END})  ({DELETE_END - DELETE_START} chars)")
print(f"Net delta: {L - (DELETE_END - DELETE_START):+d} chars")
print(f"revisionId pin: {REVISION_ID[:40]}...")
print(f"Wrote: {OUT_REQUEST}")
