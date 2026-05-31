"""Repair the scrambled consensus KG JSONs produced by the positional-join bug.

Rebuilds each `*.consensus.json` from trustworthy sources:
  - base KG  (final-kg/final-consensus/kg/{Subject} Kelas XII.json) -> structure + CORRECT descriptions (canonical order)
  - reviewer files (validations/expert-{slug}-4.json / -6.json)     -> ratings + comments by 0-based id

What it fixes deterministically:
  * descriptions  -> restored to the correct triple (kills the ~75% scramble + the "Auto-agreed" sentinel)
  * expert_review for AGREED triples -> consensus = the agreed label

What it CANNOT fix (flagged, not guessed):
  * DISAGREED triples -> the old LLM verdicts judged the wrong triple (buggy reader),
    so they are marked consensus="needs_rejudge". Re-run the FIXED KG_CONSENSUS notebook
    (only the disagreed subset hits the LLM) to resolve these.

Outputs `{Subject} Kelas XII.consensus.fixed.json` next to the base files, plus a report.
Does NOT overwrite the originals.
"""
import json
import re
from pathlib import Path

KG_DIR = Path("final-kg/final-consensus/kg")
VAL_DIR = Path("final-kg/final-consensus/validations")
OUT_DIR = Path("data/kg_consensus_repaired")
SUBJECTS = [("Biologi", "biologi"), ("Fisika", "fisika"), ("Kimia", "kimia")]

norm = lambda s: re.sub(r"\s+", " ", str(s or "").strip().lower())
ckey = lambda c, t, tg: (norm(c), norm(t), norm(tg))


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def rel_target(r):
    return r.get("target_concept", r.get("target", ""))


def repair(subject, slug):
    base = load(KG_DIR / f"{subject} Kelas XII.json")
    r1 = load(VAL_DIR / f"expert-{slug}-4.json").get("ratings", {})
    r2 = load(VAL_DIR / f"expert-{slug}-6.json").get("ratings", {})
    c1 = load(VAL_DIR / f"expert-{slug}-4.json").get("comments", {})
    c2 = load(VAL_DIR / f"expert-{slug}-6.json").get("comments", {})
    tag1, tag2 = f"expert-{slug}-4", f"expert-{slug}-6"

    report = {"subject": subject, "agreed": 0, "disagreed_needs_rejudge": [],
              "single_reviewer": 0, "unrated": 0, "total": 0}

    idx = 0  # canonical 0-based, concept-relations only -> matches reviewer ids
    for ch in base["chapters"]:
        for st in ch.get("subtopics", []):
            for c in st.get("concepts", []):
                for r in c.get("relations", []):
                    k = str(idx)
                    a, b = r1.get(k), r2.get(k)
                    ratings, comments = {}, {}
                    if a:
                        ratings[tag1] = a
                    if b:
                        ratings[tag2] = b
                    if c1.get(k):
                        comments[tag1] = c1[k]
                    if c2.get(k):
                        comments[tag2] = c2[k]

                    if a and b and a == b:
                        consensus = a
                        report["agreed"] += 1
                    elif a and b and a != b:
                        consensus = "needs_rejudge"
                        report["disagreed_needs_rejudge"].append(
                            {"id": idx, "concept": c["name"], "relation": r.get("type"),
                             "target": rel_target(r), tag1: a, tag2: b})
                    elif a or b:
                        consensus = a or b
                        report["single_reviewer"] += 1
                    else:
                        consensus = "unknown"
                        report["unrated"] += 1

                    review = {"status": consensus, "consensus": consensus,
                              "n_reviewers": len(ratings), "ratings": ratings, "comments": comments}
                    if consensus == "needs_rejudge":
                        review["needs_rejudge"] = True
                    r["expert_review"] = review
                    # description left untouched = the correct base description
                    report["total"] += 1
                    idx += 1

    out = OUT_DIR / f"{subject} Kelas XII.consensus.repaired.json"
    out.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    return out, report


def verify_no_scramble(subject):
    """Every repaired description must equal its base description (by content key)."""
    base = load(KG_DIR / f"{subject} Kelas XII.json")
    fixed = load(OUT_DIR / f"{subject} Kelas XII.consensus.repaired.json")

    def desc_by_key(d):
        m = {}
        for ch in d["chapters"]:
            for st in ch.get("subtopics", []):
                for c in st.get("concepts", []):
                    for r in c.get("relations", []):
                        m[ckey(c["name"], r.get("type"), rel_target(r))] = (r.get("description") or "").strip()
        return m

    bm, fm = desc_by_key(base), desc_by_key(fixed)
    mismatch = sum(1 for k in fm if k in bm and fm[k] != bm[k])
    return mismatch


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{'subject':9} {'total':>5} {'agreed':>7} {'rejudge':>8} {'single':>7} {'unrated':>8}  scramble")
    summary = {}
    for subject, slug in SUBJECTS:
        out, rep = repair(subject, slug)
        scr = verify_no_scramble(subject)
        rep["scramble_after"] = scr
        print(f"{subject:9} {rep['total']:>5} {rep['agreed']:>7} "
              f"{len(rep['disagreed_needs_rejudge']):>8} {rep['single_reviewer']:>7} "
              f"{rep['unrated']:>8}  {scr}")
        (OUT_DIR / f"{subject} Kelas XII.report.json").write_text(
            json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        summary[subject] = {k: rep[k] for k in ("total", "agreed", "single_reviewer", "unrated", "scramble_after")}
        summary[subject]["needs_rejudge"] = len(rep["disagreed_needs_rejudge"])

    manifest = f"""# kg_consensus_repaired

Repaired consensus KG JSONs — descriptions restored after the positional-join
scramble bug in `final-kg/final-consensus/KG_CONSENSUS.ipynb` (see PR
Kemendickbud/final-kg#1).

## How produced
`python experiments/scripts/repair_consensus_descriptions.py`

- **Source of descriptions:** `final-kg/final-consensus/kg/{{Subject}} Kelas XII.json`
  (the pre-consensus base — its descriptions were never scrambled; verified to
  match `final-kg/extracted/` exactly).
- **Method:** structural pass-through (each triple keeps its OWN base
  description) + `expert_review` rebuilt from `validations/expert-{{slug}}-4/-6.json`
  by 0-based reviewer id. **No inference / no LLM.** Content-key match used only
  to self-verify (`scramble_after` must be 0).

## Status of labels
- `agreed` triples: consensus = the agreed reviewer label (final).
- `needs_rejudge` triples: reviewers disagreed; the old LLM verdicts judged the
  WRONG triple (buggy reader) and were discarded. These need the FIXED notebook's
  LLM re-judge before they are final.

## Caveats before uploading to Neo4j
- Base KG is an older snapshot than `extracted/` v4 (Fisika/Kimia have fewer
  triples) — do NOT full-reload; patch `description` by content key only.
- Counts: {json.dumps(summary, ensure_ascii=False)}
"""
    (OUT_DIR / "MANIFEST.md").write_text(manifest, encoding="utf-8")
    print("\nWrote *.consensus.repaired.json + *.report.json + MANIFEST.md to", OUT_DIR)
    print("scramble column must be 0 (descriptions match base).")
