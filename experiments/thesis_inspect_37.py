"""Inspect §3.7 Teknik Pengumpulan Data and §3.2 Lokasi/Waktu."""
from __future__ import annotations
import json
from pathlib import Path

DOC = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json").read_text(encoding="utf-8"))
content = DOC["body"]["content"]


def text_of_paragraph(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", []))


def dump(start, end, label):
    print(f"\n=== {label} ===")
    for j in range(start, end):
        el = content[j]
        s, e = el.get("startIndex"), el.get("endIndex")
        p = el.get("paragraph")
        tbl = el.get("table")
        if p:
            ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
            txt = text_of_paragraph(p)
            marker = "HEADING" if ns.startswith("HEADING") else "para"
            print(f"  [{j:>4}] {marker:8} {ns:14} s={s:>6} e={e:>6}  {txt[:90]!r}")
        elif tbl:
            rows = len(tbl.get("tableRows", []))
            print(f"  [{j:>4}] {'TABLE':8} {'':14} s={s:>6} e={e:>6}  rows={rows}")
        else:
            print(f"  [{j:>4}] {'?':8} {'':14} s={s:>6} e={e:>6}  keys={list(el.keys())}")


# §3.7 Teknik Pengumpulan Data: heading [424], next HEADING_2 at [462] Pengolahan Data
dump(424, 462, "§3.7 Teknik Pengumpulan Data (heading[424] to heading[462])")
# §3.2 Lokasi/Waktu: heading [327], next HEADING_2 at [333] Sumber Data
dump(327, 333, "§3.2 Lokasi dan Waktu Penelitian (heading[327] to heading[333])")
# §4.1 (main heading): [512] Hasil Validasi (HEADING_2), goes until §4.2 or end of HASIL chapter
# The next HEADING_1 is at [557] KESIMPULAN
print(f"\n=== §4.1 subsection state ===")
for j in range(512, 557):
    el = content[j]
    s, e = el.get("startIndex"), el.get("endIndex")
    p = el.get("paragraph")
    tbl = el.get("table")
    if p:
        ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
        txt = text_of_paragraph(p)
        if ns.startswith("HEADING"):
            print(f"  [{j:>4}] {ns:12} s={s:>6} e={e:>6}  {txt[:80]!r}")
