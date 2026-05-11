"""Find current state of 'Subbab' / 'Analisis' stubs to plan §4.2 insertion."""
from __future__ import annotations
import json
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")

content = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json").read_text(encoding="utf-8"))["body"]["content"]


def text_of_paragraph(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", []))


# Find all relevant headings
targets = ["Implikasi untuk Fase 2", "Subbab", "Analisis Satu", "Analisis Dua", "Analisis tiga", "KESIMPULAN"]
for i, el in enumerate(content):
    p = el.get("paragraph")
    if not p:
        continue
    ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
    if not ns.startswith("HEADING"):
        continue
    txt = text_of_paragraph(p).strip()
    if any(t in txt for t in targets):
        print(f"  [{i}] {ns:12} s={el['startIndex']} e={el['endIndex']}: {txt!r}")

# Walk content[541] onwards (Subbab area) to see what's currently there
print("\n=== Body after Implikasi heading and 'Subbab' stub ===")
# Find Subbab index
sub_idx = None
for i, el in enumerate(content):
    p = el.get("paragraph")
    if not p:
        continue
    if text_of_paragraph(p).strip() == "Subbab" and p.get("paragraphStyle", {}).get("namedStyleType", "").startswith("HEADING"):
        sub_idx = i
        break

if sub_idx is not None:
    print(f"Subbab heading at content[{sub_idx}]")
    # Walk forward 12 elements
    for j in range(sub_idx, min(sub_idx + 12, len(content))):
        el = content[j]
        s, e = el.get("startIndex"), el.get("endIndex")
        p = el.get("paragraph")
        tbl = el.get("table")
        if p:
            ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
            txt = text_of_paragraph(p)
            preview = txt[:90].replace("\n", "\\n")
            marker = "HEADING" if ns.startswith("HEADING") else "para"
            print(f"  [{j}] {marker:8} {ns:14} s={s} e={e}: {preview!r}")
        elif tbl:
            rows = len(tbl.get("tableRows", []))
            print(f"  [{j}] TABLE s={s} e={e} rows={rows}")
