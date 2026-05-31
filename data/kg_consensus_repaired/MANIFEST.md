# kg_consensus_repaired

Repaired consensus KG JSONs — descriptions restored after the positional-join
scramble bug in `final-kg/final-consensus/KG_CONSENSUS.ipynb` (see PR
Kemendickbud/final-kg#1).

## How produced
`python experiments/scripts/repair_consensus_descriptions.py`

- **Source of descriptions:** `final-kg/final-consensus/kg/{Subject} Kelas XII.json`
  (the pre-consensus base — its descriptions were never scrambled; verified to
  match `final-kg/extracted/` exactly).
- **Method:** structural pass-through (each triple keeps its OWN base
  description) + `expert_review` rebuilt from `validations/expert-{slug}-4/-6.json`
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
- Counts: {"Biologi": {"total": 151, "agreed": 141, "single_reviewer": 0, "unrated": 0, "scramble_after": 0, "needs_rejudge": 10}, "Fisika": {"total": 240, "agreed": 185, "single_reviewer": 0, "unrated": 0, "scramble_after": 0, "needs_rejudge": 55}, "Kimia": {"total": 166, "agreed": 108, "single_reviewer": 0, "unrated": 0, "scramble_after": 0, "needs_rejudge": 58}}
