"""Identify content[540] in §4.1.5 region."""
from __future__ import annotations
import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8")

content = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json").read_text(encoding="utf-8"))["body"]["content"]
for j in range(535, 542):
    el = content[j]
    s, e = el.get("startIndex"), el.get("endIndex")
    keys = [k for k in el if k not in ("startIndex", "endIndex")]
    print(f"  [{j}] s={s} e={e} keys={keys}")
    tbl = el.get("table")
    if tbl:
        print(f"    table rows={len(tbl.get('tableRows', []))} columns={tbl.get('columns')}")
        # First row content
        rows = tbl.get("tableRows", [])
        for ri, row in enumerate(rows[:2]):
            cells = row.get("tableCells", [])
            cell_texts = []
            for c in cells:
                parts = []
                for sub in c.get("content", []):
                    p = sub.get("paragraph")
                    if p:
                        for pe in p.get("elements", []):
                            tr = pe.get("textRun")
                            if tr:
                                parts.append(tr.get("content", ""))
                cell_texts.append("".join(parts).strip())
            print(f"    row {ri}: {' | '.join(cell_texts)}")
