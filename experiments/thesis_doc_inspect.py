"""Inspect thesis Google Doc structure to find indices for surgical edits.

Goals:
  1. Find Tabel 4.1 cell for `expert-fisika-2` row to fix Fisika → Kimia.
  2. Find §4.1.4 heading and its boundary with §4.1.5, to know where to insert.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DOC_PATH = Path(r"D:\codebases\llm-kg-completion\.thesis-fresh.json")


def walk_elements(content):
    for el in content:
        yield el


def text_of_paragraph(p):
    parts = []
    for pe in p.get("elements", []):
        tr = pe.get("textRun")
        if tr:
            parts.append(tr.get("content", ""))
    return "".join(parts)


def text_of_table_cell(cell):
    parts = []
    for el in cell.get("content", []):
        p = el.get("paragraph")
        if p:
            parts.append(text_of_paragraph(p))
    return "".join(parts)


def main():
    data = json.loads(DOC_PATH.read_text(encoding="utf-8"))
    content = data["body"]["content"]
    rev_id = data.get("revisionId", "")
    print(f"revisionId: {rev_id}")
    print(f"top-level elements: {len(content)}")

    # 1) Find headings containing 4.1.x
    print("\n=== Headings 4.1.x ===")
    headings = []
    for i, el in enumerate(content):
        p = el.get("paragraph")
        if not p:
            continue
        style = p.get("paragraphStyle", {})
        named_style = style.get("namedStyleType", "")
        if not named_style.startswith("HEADING"):
            continue
        txt = text_of_paragraph(p).strip()
        if "4.1" in txt or "Hasil Validasi" in txt or "Keterbatasan" in txt:
            headings.append({
                "index_in_content": i,
                "startIndex": el.get("startIndex"),
                "endIndex": el.get("endIndex"),
                "namedStyle": named_style,
                "text": txt,
            })
    for h in headings:
        print(f"  [{h['index_in_content']:>4}] {h['namedStyle']:12} "
              f"start={h['startIndex']:>6} end={h['endIndex']:>6}  {h['text']!r}")

    # 2) Find content between 4.1.4 and 4.1.5 (or next heading)
    h414 = next((h for h in headings if "4.1.4" in h["text"]), None)
    h415 = next((h for h in headings if "4.1.5" in h["text"]), None)
    if h414:
        # Find what's between 4.1.4 heading and the next heading
        idx_in = h414["index_in_content"]
        next_heading_idx = None
        for j in range(idx_in + 1, len(content)):
            p = content[j].get("paragraph")
            if p and p.get("paragraphStyle", {}).get("namedStyleType", "").startswith("HEADING"):
                next_heading_idx = j
                break
        print(f"\n=== Content between §4.1.4 heading and next heading ===")
        print(f"  §4.1.4 heading at content[{idx_in}], endIndex={h414['endIndex']}")
        if next_heading_idx is not None:
            print(f"  next heading at content[{next_heading_idx}], "
                  f"startIndex={content[next_heading_idx].get('startIndex')}, "
                  f"text={text_of_paragraph(content[next_heading_idx].get('paragraph', {})).strip()!r}")
            # Show paragraphs in between
            for j in range(idx_in + 1, next_heading_idx):
                el = content[j]
                p = el.get("paragraph")
                if p:
                    txt = text_of_paragraph(p)
                    if txt.strip():
                        print(f"    content[{j}] start={el.get('startIndex')} end={el.get('endIndex')}: {txt[:120]!r}")
                    else:
                        print(f"    content[{j}] start={el.get('startIndex')} end={el.get('endIndex')}: <empty paragraph>")
                else:
                    keys = list(el.keys())
                    print(f"    content[{j}] start={el.get('startIndex')} end={el.get('endIndex')}: {keys}")

    # 3) Find Tabel 4.1 row for expert-fisika-2
    print("\n=== Tables containing 'expert-fisika-2' ===")
    for i, el in enumerate(content):
        tbl = el.get("table")
        if not tbl:
            continue
        rows = tbl.get("tableRows", [])
        for ri, row in enumerate(rows):
            cells = row.get("tableCells", [])
            row_text = " | ".join(text_of_table_cell(c).strip() for c in cells)
            if "expert-fisika-2" in row_text:
                print(f"  Table at content[{i}] start={el.get('startIndex')} end={el.get('endIndex')}")
                print(f"  Row {ri}: {row_text!r}")
                for ci, cell in enumerate(cells):
                    cell_text = text_of_table_cell(cell)
                    s = cell.get("startIndex")
                    e = cell.get("endIndex")
                    print(f"    Cell {ci}: start={s} end={e}  text={cell_text!r}")
                # Also show header row for column reference
                if rows:
                    header_cells = rows[0].get("tableCells", [])
                    header_text = " | ".join(text_of_table_cell(c).strip() for c in header_cells)
                    print(f"  (Header row 0): {header_text!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
