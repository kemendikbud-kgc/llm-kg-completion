"""Verify the post-batchUpdate state."""
from __future__ import annotations
import json
from pathlib import Path

DOC = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json").read_text(encoding="utf-8"))
content = DOC["body"]["content"]


def text_of_paragraph(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", []))


def text_of_table_cell(cell):
    parts = []
    for el in cell.get("content", []):
        p = el.get("paragraph")
        if p:
            parts.append(text_of_paragraph(p))
    return "".join(parts)


# 1) Confirm Tabel 4.1 row 3 says "Kimia"
# 2) Confirm Tabel 4.3 row 3 says "Kimia"
# 3) Confirm 4.1.4 has content

print("=== Tables with expert-fisika-2 ===")
for i, el in enumerate(content):
    tbl = el.get("table")
    if not tbl:
        continue
    rows = tbl.get("tableRows", [])
    for ri, row in enumerate(rows):
        cells = row.get("tableCells", [])
        row_text = " | ".join(text_of_table_cell(c).strip() for c in cells)
        if "expert-fisika-2" in row_text:
            print(f"  content[{i}] row {ri}: '{row_text}'")

print("\n=== Headings 4.1.x area (Hasil/Keterbatasan/Implikasi) ===")
for i, el in enumerate(content):
    p = el.get("paragraph")
    if not p:
        continue
    ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
    if not ns.startswith("HEADING"):
        continue
    txt = text_of_paragraph(p).strip()
    if any(t in txt for t in ["Hasil Validasi", "Keterbatasan", "Implikasi"]):
        print(f"  content[{i}] {ns}: '{txt}'")

print("\n=== Body between Keterbatasan and Implikasi ===")
# Find both heading positions in content list
ket_idx = None
imp_idx = None
for i, el in enumerate(content):
    p = el.get("paragraph")
    if not p:
        continue
    txt = text_of_paragraph(p).strip()
    if "Keterbatasan" in txt and p.get("paragraphStyle", {}).get("namedStyleType", "").startswith("HEADING"):
        ket_idx = i
    elif "Implikasi" in txt and p.get("paragraphStyle", {}).get("namedStyleType", "").startswith("HEADING") and ket_idx is not None and i > ket_idx:
        imp_idx = i
        break

if ket_idx is not None and imp_idx is not None:
    print(f"  §4.1.4 heading at content[{ket_idx}]")
    print(f"  §4.1.5 heading at content[{imp_idx}]")
    word_total = 0
    for j in range(ket_idx + 1, imp_idx):
        el = content[j]
        p = el.get("paragraph")
        if p:
            ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
            txt = text_of_paragraph(p)
            words = len(txt.split())
            word_total += words
            preview = txt[:100].replace("\n", "\\n")
            print(f"    [{j}] {ns:14} ({words:>3}w) {preview!r}")
    print(f"  Total words in §4.1.4 body: {word_total}")
