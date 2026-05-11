"""Find what's between §4.1.4 heading and the next heading."""
from __future__ import annotations
import json
from pathlib import Path

DOC = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-fresh.json").read_text(encoding="utf-8"))
content = DOC["body"]["content"]


def text_of_paragraph(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", []))


start_idx = 530  # the §4.1.4 heading
# Walk forward until next heading
for j in range(start_idx, min(len(content), start_idx + 30)):
    el = content[j]
    s, e = el.get("startIndex"), el.get("endIndex")
    p = el.get("paragraph")
    tbl = el.get("table")
    sect = el.get("sectionBreak")
    if p:
        ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
        txt = text_of_paragraph(p)
        marker = "HEADING" if ns.startswith("HEADING") else "para"
        print(f"  [{j:>4}] {marker:10} {ns:14} start={s:>6} end={e:>6}  {txt[:120]!r}")
    elif tbl:
        rows = len(tbl.get("tableRows", []))
        print(f"  [{j:>4}] {'TABLE':10} {'':14} start={s:>6} end={e:>6}  rows={rows}")
    elif sect:
        print(f"  [{j:>4}] {'SECTION':10} {'':14} start={s:>6} end={e:>6}")
    else:
        print(f"  [{j:>4}] {'?':10} {'':14} start={s:>6} end={e:>6}  keys={list(el.keys())}")
