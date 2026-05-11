"""Verify §4.2 'Pembahasan Kualitatif' is in place with real body."""
from __future__ import annotations
import json
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")

content = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json").read_text(encoding="utf-8"))["body"]["content"]


def text_of_paragraph(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", []))


# Find "Pembahasan Kualitatif" heading
pem_idx = None
for i, el in enumerate(content):
    p = el.get("paragraph")
    if not p:
        continue
    txt = text_of_paragraph(p).strip()
    if "Pembahasan Kualitatif" in txt and p.get("paragraphStyle", {}).get("namedStyleType", "").startswith("HEADING"):
        pem_idx = i
        break

if pem_idx is None:
    print("ERROR: Pembahasan Kualitatif heading not found")
    sys.exit(1)

# Find next HEADING_2 (will be next §4.x section)
next_h = None
for j in range(pem_idx + 1, len(content)):
    p = content[j].get("paragraph")
    if p and p.get("paragraphStyle", {}).get("namedStyleType", "") == "HEADING_2":
        next_h = j
        break

print(f"§4.2 'Pembahasan Kualitatif' heading at content[{pem_idx}]")
print(f"Next HEADING_2 at content[{next_h}]: {text_of_paragraph(content[next_h].get('paragraph', {})).strip()!r}")
print()

word_total = 0
has_lorem = False
for j in range(pem_idx + 1, next_h):
    el = content[j]
    p = el.get("paragraph")
    if not p:
        continue
    ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
    txt = text_of_paragraph(p)
    if "Lorem ipsum" in txt:
        has_lorem = True
    words = len(txt.split())
    word_total += words
    preview = txt[:90].replace("\n", "\\n")
    print(f"  [{j}] {ns:12} ({words:>3}w) {preview!r}")

print(f"\nTotal words in §4.2: {word_total}")
print(f"Lorem ipsum still present: {has_lorem}")
