"""Drill into the textRun-level indices of the 'Fisika' cells."""
from __future__ import annotations
import json
from pathlib import Path

DOC = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-fresh.json").read_text(encoding="utf-8"))
content = DOC["body"]["content"]


def dump_cell(table_idx, row_idx, cell_idx, label):
    el = content[table_idx]
    cell = el["table"]["tableRows"][row_idx]["tableCells"][cell_idx]
    print(f"\n=== {label} ===")
    print(f"  cell.startIndex={cell['startIndex']} cell.endIndex={cell['endIndex']}")
    for pi, sub in enumerate(cell.get("content", [])):
        if "paragraph" in sub:
            p = sub["paragraph"]
            print(f"  paragraph {pi}: startIndex={sub['startIndex']} endIndex={sub['endIndex']}")
            for ei, pe in enumerate(p.get("elements", [])):
                tr = pe.get("textRun")
                if tr:
                    print(f"    element {ei}: startIndex={pe['startIndex']} endIndex={pe['endIndex']} content={tr.get('content', '')!r}")
                else:
                    print(f"    element {ei}: startIndex={pe['startIndex']} endIndex={pe['endIndex']} keys={list(pe.keys())}")
        else:
            print(f"  sub {pi}: {list(sub.keys())}")


# Tabel 4.1 is content[516], expert-fisika-2 is row 3, "Fisika" cell is index 1
dump_cell(516, 3, 1, "Tabel 4.1 row 3 cell 1 (Fisika)")
# Tabel 4.3 is content[527], expert-fisika-2 is row 3, "Fisika" cell is index 1
dump_cell(527, 3, 1, "Tabel 4.3 row 3 cell 1 (Fisika)")
