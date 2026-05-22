"""Judge the KG quality from the extracted JSONs (Yhoga peer)."""
import json, os
from collections import Counter, defaultdict

D = os.path.dirname(__file__)
def L(n): return json.load(open(os.path.join(D, n), 'r', encoding='utf-8'))

files = {
    'Biologi': L('biologi_base.json'),
    'Fisika':  L('fisika_base.json'),
    'Kimia':   L('kimia_base.json'),
}

# 1. Top-level schema
print('=== SCHEMA (top keys + sample chapter keys + sample concept keys) ===')
for subj, d in files.items():
    ch0 = d['chapters'][0]
    st0 = ch0['subtopics'][0]
    c0  = st0['concepts'][0]
    print(f'{subj}: top={sorted(d.keys())}')
    print(f'  chapter keys={sorted(ch0.keys())}')
    print(f'  subtopic keys={sorted(st0.keys())}')
    print(f'  concept keys ={sorted(c0.keys())}')

# 2. Concept granularity per chapter / subtopic
print('\n=== GRANULARITY (chapters / subtopics / concepts per book) ===')
for subj, d in files.items():
    chs = d['chapters']
    sts = [st for ch in chs for st in ch.get('subtopics',[])]
    cps = [c for st in sts for c in st.get('concepts',[])]
    avg_c_per_st = len(cps) / max(len(sts), 1)
    print(f'{subj}: chapters={len(chs)}  subtopics={len(sts)}  concepts={len(cps)}  '
          f'avg concepts/subtopic={avg_c_per_st:.1f}')

# 3. Intra-book relation types and frequency
print('\n=== INTRA-BOOK RELATION TYPES (base only — pre-boost) ===')
for subj, d in files.items():
    types = Counter()
    for ch in d['chapters']:
        for st in ch.get('subtopics',[]):
            for c in st.get('concepts',[]):
                for r in c.get('relations',[]):
                    types[r.get('type','?')] += 1
    total = sum(types.values())
    print(f'{subj} ({total} edges): {dict(types.most_common())}')

# 4. Cross-book relation types
print('\n=== CROSS-BOOK RELATION TYPES ===')
for subj, d in files.items():
    types = Counter(); targets = Counter()
    for ch in d['chapters']:
        for st in ch.get('subtopics',[]):
            for c in st.get('concepts',[]):
                for r in c.get('cross_book_links',[]):
                    types[r.get('relation_type','?')] += 1
                    targets[r.get('target_book','?')] += 1
    total = sum(types.values())
    print(f'{subj} ({total} edges): types={dict(types.most_common())}  targets={dict(targets)}')

# 5. Chapter-level relations
print('\n=== CHAPTER-LEVEL RELATIONS ===')
for subj, d in files.items():
    rels = []
    for ch in d['chapters']:
        for r in ch.get('chapter_relations',[]):
            rels.append((ch['chapter'], r.get('type'), r.get('target_chapter'),
                        len(r.get('concept_links',[]))))
    print(f'{subj}: {len(rels)} chapter relations')
    for src,t,tgt,nl in rels:
        print(f'  ({src!r}) --[{t}]--> ({tgt!r})  with {nl} concept_links')

# 6. Orphans (concepts with no edges)
print('\n=== ORPHAN CONCEPTS (no intra-book and no cross-book edges) ===')
for subj, d in files.items():
    total = 0; orphans = []
    for ch in d['chapters']:
        for st in ch.get('subtopics',[]):
            for c in st.get('concepts',[]):
                total += 1
                if not c.get('relations') and not c.get('cross_book_links'):
                    orphans.append(c['name'])
    print(f'{subj}: {len(orphans)}/{total} orphans ({len(orphans)/max(total,1):.0%})')
    for n in orphans[:8]: print(f'    - {n}')
    if len(orphans) > 8: print(f'    ... +{len(orphans)-8} more')

# 7. Description quality (length distribution)
print('\n=== DESCRIPTION LENGTH (concept.description) ===')
for subj, d in files.items():
    lens = []
    empty = 0
    for ch in d['chapters']:
        for st in ch.get('subtopics',[]):
            for c in st.get('concepts',[]):
                desc = c.get('description','') or ''
                if not desc.strip(): empty += 1
                lens.append(len(desc))
    if lens:
        lens.sort()
        med = lens[len(lens)//2]
        print(f'{subj}: n={len(lens)} empty={empty} min={lens[0]} med={med} max={lens[-1]}')

# 8. glossary_validated coverage
print('\n=== glossary_validated COVERAGE ===')
for subj, d in files.items():
    total = 0; gv_true = 0; gv_false = 0; missing = 0
    for ch in d['chapters']:
        for st in ch.get('subtopics',[]):
            for c in st.get('concepts',[]):
                total += 1
                if 'glossary_validated' not in c: missing += 1
                elif c['glossary_validated']: gv_true += 1
                else: gv_false += 1
    print(f'{subj}: total={total} validated=True:{gv_true} False:{gv_false} missing:{missing}')

# 9. Dangling targets (target referenced by edge but not a concept in the book)
print('\n=== DANGLING INTRA-BOOK TARGETS (edge target not in concept set) ===')
for subj, d in files.items():
    names = set()
    for ch in d['chapters']:
        for st in ch.get('subtopics',[]):
            for c in st.get('concepts',[]): names.add(c['name'])
    dangling = Counter()
    for ch in d['chapters']:
        for st in ch.get('subtopics',[]):
            for c in st.get('concepts',[]):
                for r in c.get('relations',[]):
                    tgt = r.get('target')
                    if tgt and tgt not in names:
                        dangling[tgt] += 1
    print(f'{subj}: {len(dangling)} distinct dangling targets, {sum(dangling.values())} edges affected')
    for tgt, n in dangling.most_common(5):
        print(f'    [{n}x] -> {tgt!r}')

# 10. Symmetric / duplicate edges (A->B same type as B->A)
print('\n=== SYMMETRIC INTRA-BOOK EDGES (base only) ===')
for subj, d in files.items():
    seen = set(); sym = 0; dup = 0
    for ch in d['chapters']:
        for st in ch.get('subtopics',[]):
            for c in st.get('concepts',[]):
                for r in c.get('relations',[]):
                    key = (c['name'], r.get('target'), r.get('type'))
                    if key in seen: dup += 1
                    seen.add(key)
    for (a,b,t) in seen:
        if (b,a,t) in seen and a < b: sym += 1
    print(f'{subj}: symmetric pairs={sym}  duplicate edges={dup}')
