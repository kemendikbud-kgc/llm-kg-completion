"""Compare base vs expert_boosted JSONs from Yhoga's peer (fadrian.yhoga@ui.ac.id)."""
import json, os, sys
from collections import Counter

D = os.path.dirname(__file__)

def load(name):
    with open(os.path.join(D, name), 'r', encoding='utf-8') as f:
        return json.load(f)

def walk_concepts(doc):
    out = []
    for ch in doc.get('chapters', []):
        for st in ch.get('subtopics', []):
            for c in st.get('concepts', []):
                out.append((ch.get('chapter'), st.get('subtopic') or st.get('name') or '?', c))
    return out

def concept_keys(doc):
    keys = set()
    for ch in doc.get('chapters', []):
        for st in ch.get('subtopics', []):
            for c in st.get('concepts', []):
                k = c.get('name') or c.get('concept') or c.get('id')
                if k: keys.add(k)
    return keys

def relation_summary(doc):
    counts = Counter()
    examples = {}
    for ch in doc.get('chapters', []):
        for ch_rel in ch.get('chapter_relations', []):
            t = ch_rel.get('type', 'CHAPTER_REL?')
            counts[f'chapter:{t}'] += len(ch_rel.get('concept_links', []) or [1])
        for st in ch.get('subtopics', []):
            for c in st.get('concepts', []):
                for link_field in ('cross_book_links', 'related_concepts', 'concept_relations',
                                   'prerequisites', 'supports', 'analogies'):
                    lst = c.get(link_field, []) or []
                    if not isinstance(lst, list): continue
                    for ln in lst:
                        if isinstance(ln, dict):
                            rt = ln.get('relation_type') or ln.get('type') or link_field
                            counts[f'concept:{link_field}:{rt}'] += 1
                            examples.setdefault(f'concept:{link_field}:{rt}', ln)
                        else:
                            counts[f'concept:{link_field}:<str>'] += 1
    return counts, examples

def detect_expert_markers(doc):
    """Look for any field that hints at expert validation."""
    text = json.dumps(doc, ensure_ascii=False).lower()
    markers = ['expert', 'validated', 'validasi', 'pakar', 'approved',
               'reviewer', 'confidence', 'score', 'verdict', 'feedback', 'reviewed']
    hits = {m: text.count(m) for m in markers if m in text}
    return hits

pairs = [
    ('Biologi', 'biologi_base.json', 'biologi_boosted.json'),
    ('Fisika',  'fisika_base.json',  'fisika_boosted.json'),
    ('Kimia',   'kimia_base.json',   'kimia_boosted.json'),
]

for subj, base_fn, boost_fn in pairs:
    base = load(base_fn); boost = load(boost_fn)
    print(f'\n========== {subj} ==========')
    print(f'grade: base={base.get("grade")!r}  boost={boost.get("grade")!r}')
    print(f'chapters: base={len(base["chapters"])}  boost={len(boost["chapters"])}')
    nb_concepts_base  = sum(len(st.get("concepts",[])) for ch in base["chapters"]  for st in ch.get("subtopics",[]))
    nb_concepts_boost = sum(len(st.get("concepts",[])) for ch in boost["chapters"] for st in ch.get("subtopics",[]))
    print(f'concepts:  base={nb_concepts_base}  boost={nb_concepts_boost}  (delta={nb_concepts_boost-nb_concepts_base:+d})')

    ck_base = concept_keys(base); ck_boost = concept_keys(boost)
    only_in_boost = ck_boost - ck_base
    only_in_base = ck_base - ck_boost
    print(f'distinct concept names: base={len(ck_base)} boost={len(ck_boost)} '
          f'(added={len(only_in_boost)}, removed={len(only_in_base)})')

    rc_base,  ex_base  = relation_summary(base)
    rc_boost, ex_boost = relation_summary(boost)
    all_types = sorted(set(rc_base) | set(rc_boost))
    print('--- relation counts (base -> boost) ---')
    for t in all_types:
        b = rc_base.get(t,0); o = rc_boost.get(t,0)
        if b == o == 0: continue
        marker = '  +' if o>b else ('  -' if o<b else '   ')
        print(f'{marker} {t:55s} {b:>5d} -> {o:>5d}  (delta={o-b:+d})')

    em_base = detect_expert_markers(base); em_boost = detect_expert_markers(boost)
    if em_base or em_boost:
        print(f'expert-validation markers: base={em_base}  boost={em_boost}')
