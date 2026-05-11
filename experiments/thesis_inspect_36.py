"""Inspect body between §3.6 (content[405]) and §3.7 (content[424])."""
from __future__ import annotations
import json
from pathlib import Path

DOC = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json").read_text(encoding="utf-8"))
content = DOC["body"]["content"]


def text_of_paragraph(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", []))


for j in range(405, 425):
    el = content[j]
    s, e = el.get("startIndex"), el.get("endIndex")
    p = el.get("paragraph")
    tbl = el.get("table")
    if p:
        ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
        txt = text_of_paragraph(p)
        marker = "HEADING" if ns.startswith("HEADING") else "para"
        print(f"  [{j:>4}] {marker:8} {ns:14} start={s:>6} end={e:>6}  {txt[:80]!r}")
    elif tbl:
        rows = len(tbl.get("tableRows", []))
        print(f"  [{j:>4}] {'TABLE':8} {'':14} start={s:>6} end={e:>6}  rows={rows}")
    else:
        print(f"  [{j:>4}] {'?':8} {'':14} start={s:>6} end={e:>6}  keys={list(el.keys())}")
