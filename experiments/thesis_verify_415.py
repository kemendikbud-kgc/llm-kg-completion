"""Verify §4.1.5 is now real content."""
from __future__ import annotations
import json
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")

content = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json").read_text(encoding="utf-8"))["body"]["content"]


def text_of_paragraph(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", []))


# Find §4.1.5 heading and walk to next heading
ket_idx = imp_idx = next_h = None
for i, el in enumerate(content):
    p = el.get("paragraph")
    if not p:
        continue
    ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
    if not ns.startswith("HEADING"):
        continue
    txt = text_of_paragraph(p).strip()
    if "Implikasi untuk Fase 2" in txt:
        imp_idx = i
    elif imp_idx is not None and i > imp_idx and ns in ("HEADING_1", "HEADING_2", "HEADING_3"):
        next_h = i
        break

print(f"§4.1.5 heading at content[{imp_idx}]")
print(f"next heading at content[{next_h}]: {text_of_paragraph(content[next_h].get('paragraph', {})).strip()!r}")
print(f"\nBody of §4.1.5:")
word_total = 0
has_lorem = False
has_placeholder_table = False
for j in range(imp_idx + 1, next_h):
    el = content[j]
    p = el.get("paragraph")
    tbl = el.get("table")
    if p:
        ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
        txt = text_of_paragraph(p)
        if "Lorem ipsum" in txt:
            has_lorem = True
        words = len(txt.split())
        word_total += words
        preview = txt[:100].replace("\n", "\\n")
        print(f"  [{j}] {ns:12} ({words:>3}w) {preview!r}")
    elif tbl:
        has_placeholder_table = True
        print(f"  [{j}] TABLE rows={len(tbl.get('tableRows', []))}")

print(f"\nTotal words in §4.1.5: {word_total}")
print(f"Lorem ipsum present: {has_lorem}")
print(f"Placeholder table present: {has_placeholder_table}")
