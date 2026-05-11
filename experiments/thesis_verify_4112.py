"""Check §4.1.1, §4.1.2, §4.1.3 body content."""
from __future__ import annotations
import json
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")

content = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json").read_text(encoding="utf-8"))["body"]["content"]


def text_of_paragraph(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", []))


# Find sub-section heading indices
labels = {
    "Cakupan Pengumpulan Data": "§4.1.1",
    "Distribusi Penilaian per Reviewer": "§4.1.2",
    "Presisi Validasi per Reviewer": "§4.1.3",
    "Keterbatasan Data Fase 1": "§4.1.4",
    "Implikasi untuk Fase 2": "§4.1.5",
}

heading_positions = []
for i, el in enumerate(content):
    p = el.get("paragraph")
    if not p:
        continue
    ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
    if ns != "HEADING_3":
        continue
    txt = text_of_paragraph(p).strip()
    for key, label in labels.items():
        if key in txt:
            heading_positions.append((i, label, txt))

print("=== §4.1.x subsections ===\n")
for k, (i, label, txt) in enumerate(heading_positions):
    next_i = heading_positions[k + 1][0] if k + 1 < len(heading_positions) else None
    if next_i is None:
        # find next any heading
        for j in range(i + 1, len(content)):
            p = content[j].get("paragraph")
            if p and p.get("paragraphStyle", {}).get("namedStyleType", "").startswith("HEADING"):
                next_i = j
                break
    words = 0
    tables = 0
    for j in range(i + 1, next_i):
        el = content[j]
        p = el.get("paragraph")
        if p:
            words += len(text_of_paragraph(p).split())
        elif el.get("table"):
            tables += 1
    body_text = ""
    for j in range(i + 1, next_i):
        el = content[j]
        p = el.get("paragraph")
        if p:
            body_text += text_of_paragraph(p)
    # Print first 200 chars of body
    preview = body_text[:200].replace("\n", " ").strip()
    print(f"{label:>8}  content[{i}]  body: {words}w +{tables}tbl")
    print(f"        preview: {preview!r}")
    print()
