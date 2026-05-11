"""Audit Bab 3 and Bab 4 sections: word counts to find gaps."""
from __future__ import annotations
import json
from pathlib import Path

DOC = json.loads(Path(r"D:\codebases\llm-kg-completion\.thesis-verify.json").read_text(encoding="utf-8"))
content = DOC["body"]["content"]


def text_of_paragraph(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", []))


# Build a flat list of all headings with their index positions
headings = []
for i, el in enumerate(content):
    p = el.get("paragraph")
    if not p:
        continue
    ns = p.get("paragraphStyle", {}).get("namedStyleType", "")
    if not ns.startswith("HEADING"):
        continue
    txt = text_of_paragraph(p).strip()
    if txt:
        headings.append((i, el.get("startIndex"), el.get("endIndex"), ns, txt))

# Compute word counts between each pair of consecutive headings (the body of section i)
print(f"{'idx':>4} {'startIdx':>8} {'endIdx':>8} {'style':12} {'words':>5}  text")
print("-" * 110)
for h_idx in range(len(headings)):
    i, s, e, ns, txt = headings[h_idx]
    next_i = headings[h_idx + 1][0] if h_idx + 1 < len(headings) else len(content)
    body_words = 0
    body_tables = 0
    for j in range(i + 1, next_i):
        el = content[j]
        p = el.get("paragraph")
        if p:
            body_words += len(text_of_paragraph(p).split())
        elif el.get("table"):
            body_tables += 1
    marker = ""
    if body_words == 0 and body_tables == 0:
        marker = "  *** EMPTY ***"
    elif body_words < 30 and body_tables == 0:
        marker = "  ** sparse **"
    tbl_marker = f" +{body_tables}tbl" if body_tables else ""
    print(f"{i:>4} {s:>8} {e:>8} {ns:12} {body_words:>5}{tbl_marker:5}  {txt[:70]}{marker}")
