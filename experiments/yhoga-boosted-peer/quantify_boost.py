"""Quantify what the _expert_boosted suffix actually adds vs the base."""
import json, os, random
from collections import Counter

D = os.path.dirname(__file__)
def load(n): return json.load(open(os.path.join(D, n), 'r', encoding='utf-8'))

pairs = [
    ('Biologi', 'biologi_base.json', 'biologi_boosted.json'),
    ('Fisika',  'fisika_base.json',  'fisika_boosted.json'),
    ('Kimia',   'kimia_base.json',   'kimia_boosted.json'),
]

def iter_concepts(doc):
    for ch in doc['chapters']:
        for st in ch.get('subtopics', []):
            for c in st.get('concepts', []):
                yield ch['chapter'], st.get('subtopic') or st.get('name','?'), c

def rel_key(r):
    # Stable identity of an intra-book relation
    return (r.get('target'), r.get('type'))

def cross_key(r):
    return (r.get('target_book'), r.get('target_concept'), r.get('relation_type'))

totals = []

for subj, b, x in pairs:
    base = load(b); boost = load(x)
    # Index by concept name
    bmap = {c['name']: c for _,_,c in iter_concepts(base)}
    xmap = {c['name']: c for _,_,c in iter_concepts(boost)}

    intra_added = 0; intra_explanation = Counter(); intra_added_examples = []
    cross_added = 0; cross_added_examples = []
    typed_intra = Counter(); typed_cross = Counter()

    for name, bx in xmap.items():
        bb = bmap.get(name, {})
        bb_rels  = bb.get('relations', []) or []
        xx_rels  = bx.get('relations', []) or []
        bb_cross = bb.get('cross_book_links', []) or []
        xx_cross = bx.get('cross_book_links', []) or []
        # Adds in intra-book relations
        bb_keys = {rel_key(r) for r in bb_rels}
        for r in xx_rels:
            if rel_key(r) not in bb_keys:
                intra_added += 1
                typed_intra[r.get('type','?')] += 1
                desc = r.get('description','')
                intra_explanation[desc] += 1
                if len(intra_added_examples) < 5:
                    intra_added_examples.append((name, r))
        # Adds in cross-book
        bb_ck = {cross_key(r) for r in bb_cross}
        for r in xx_cross:
            if cross_key(r) not in bb_ck:
                cross_added += 1
                typed_cross[r.get('relation_type','?')] += 1
                if len(cross_added_examples) < 5:
                    cross_added_examples.append((name, r))

    total_intra_base  = sum(len(c.get('relations',[])) for _,_,c in iter_concepts(base))
    total_intra_boost = sum(len(c.get('relations',[])) for _,_,c in iter_concepts(boost))
    total_cross_base  = sum(len(c.get('cross_book_links',[])) for _,_,c in iter_concepts(base))
    total_cross_boost = sum(len(c.get('cross_book_links',[])) for _,_,c in iter_concepts(boost))

    flagged = sum(1 for _,_,c in iter_concepts(boost)
                  for r in c.get('relations',[]) if r.get('expert_validation_added'))
    flagged_no_match = sum(1 for _,_,c in iter_concepts(boost)
                           for r in c.get('relations',[])
                           if r.get('expert_validation_added') and not r.get('description'))
    print(f'\n========== {subj} ==========')
    print(f'intra-book relations:  base={total_intra_base}  boost={total_intra_boost}  '
          f'added={intra_added}  ({intra_added/max(total_intra_base,1):.0%} of base)')
    print(f'cross-book links:      base={total_cross_base}  boost={total_cross_boost}  added={cross_added}')
    print(f'relations flagged expert_validation_added=true in boost: {flagged}')
    print(f'  by type: {dict(typed_intra)}')
    print(f'  added cross-book by type: {dict(typed_cross)}')
    print(f'  unique explanation strings on added relations: {len(intra_explanation)}')
    for desc, n in intra_explanation.most_common(3):
        print(f'    [{n}x] {desc!r}')
    print('  sample added intra-book relations:')
    for name, r in intra_added_examples:
        print(f'    {name!r} --[{r.get("type")}]--> {r.get("target")!r}'
              f'  (expert_validation_added={r.get("expert_validation_added")}, '
              f'desc={r.get("description","")[:80]!r})')
    if cross_added_examples:
        print('  sample added cross-book links:')
        for name, r in cross_added_examples:
            print(f'    {name!r} --[{r.get("relation_type")}]--> '
                  f'{r.get("target_concept")!r} in {r.get("target_book")!r}')
    totals.append((subj, intra_added, cross_added, total_intra_base, total_cross_base))

print('\n========== SUMMARY ==========')
print(f'{"subject":10} {"intra-add":>10} {"intra-base":>11} {"%inc":>6} '
      f'{"cross-add":>10} {"cross-base":>11}')
for subj, ia, ca, ib, cb in totals:
    print(f'{subj:10} {ia:>10d} {ib:>11d} {ia/max(ib,1):>5.0%} {ca:>10d} {cb:>11d}')
