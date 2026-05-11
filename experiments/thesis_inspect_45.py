"""Read §4.1.5 body + §2.1 Landasan Teori state."""
from __future__ import annotations
import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8")

DOC = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json").read_text(encoding="utf-8"))
content = DOC["body"]["content"]


def text_of_paragraph(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", []))


# §4.1.5 = heading[535], next heading at [541] ("Subbab")
print("=== §4.1.5 Implikasi untuk Fase 2 body ===")
for j in range(535, 542):
    el = content[j]
    s, e = el.get("startIndex"), el.get("endIndex")
    p = el.get("paragraph")
    if p:
        ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
        txt = text_of_paragraph(p)
        marker = "HEADING" if ns.startswith("HEADING") else "para"
        print(f"  [{j}] {marker} s={s} e={e}: {txt!r}")

# §2.1 Landasan Teori = heading[216], next HEADING_2 at [238] "2.2 Metrik Evaluasi"
print("\n=== §2.1 Landasan Teori body ===")
for j in range(216, 238):
    el = content[j]
    s, e = el.get("startIndex"), el.get("endIndex")
    p = el.get("paragraph")
    tbl = el.get("table")
    if p:
        ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
        txt = text_of_paragraph(p)
        marker = "HEADING" if ns.startswith("HEADING") else "para"
        preview = txt[:90].replace("\n", "\\n")
        print(f"  [{j}] {marker} {ns} s={s} e={e}: {preview!r}")
    elif tbl:
        rows = len(tbl.get("tableRows", []))
        print(f"  [{j}] TABLE s={s} e={e} rows={rows}")
