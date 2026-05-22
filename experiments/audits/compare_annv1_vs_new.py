"""Compare ann-v1 cross-book edges vs new/*_expert_boosted cross_book_links."""
import json, os, sys
from collections import Counter

ROOT = os.path.dirname(__file__)
ANN  = os.path.join(ROOT, 'yhoga-ann-v1')
NEW  = os.path.join(ROOT, 'yhoga-boosted-peer')

# ----- ann-v1 (canonical t075_k15) -----
ann = json.load(open(os.path.join(ANN, 'lintas_buku_edges.t075_k15.json'), encoding='utf-8'))
ann_edges = ann['edges']
def ann_norm(e):
    a, b = e['source_name'].strip().lower(), e['target_name'].strip().lower()
    ga, gb = e['source_grade'], e['target_grade']
    # undirected key for type-agnostic overlap; keep directed too
    return (frozenset([(a,ga),(b,gb)]), e['properties']['relation_type'])

ann_undir = set()
ann_undir_typed = Counter()
ann_dir = set()
ann_typed = Counter()
ann_concepts = set()
ann_confidence = []
for e in ann_edges:
    a, b = e['source_name'].strip().lower(), e['target_name'].strip().lower()
    ga, gb = e['source_grade'], e['target_grade']
    rt = e['properties']['relation_type']  # SAMA_DENGAN, APLIKASI_DARI, etc (already stripped LINTAS_BUKU_ prefix)
    ann_undir.add(frozenset([(a,ga),(b,gb)]))
    ann_undir_typed[rt] += 1
    ann_dir.add(((a,ga),(b,gb),rt))
    ann_typed[rt] += 1
    ann_concepts.add((a,ga)); ann_concepts.add((b,gb))
    ann_confidence.append(e['properties'].get('confidence', None))

# ----- new/*_expert_boosted cross-book links -----
new_books = {
    'Biologi Kelas XII': json.load(open(os.path.join(NEW,'biologi_boosted.json'), encoding='utf-8')),
    'Fisika Kelas XII':  json.load(open(os.path.join(NEW,'fisika_boosted.json'),  encoding='utf-8')),
    'Kimia Kelas XII':   json.load(open(os.path.join(NEW,'kimia_boosted.json'),   encoding='utf-8')),
}
# Also load base for comparison
new_base = {
    'Biologi Kelas XII': json.load(open(os.path.join(NEW,'biologi_base.json'), encoding='utf-8')),
    'Fisika Kelas XII':  json.load(open(os.path.join(NEW,'fisika_base.json'),  encoding='utf-8')),
    'Kimia Kelas XII':   json.load(open(os.path.join(NEW,'kimia_base.json'),   encoding='utf-8')),
}

LB_TYPES = {'SAMA_DENGAN','APLIKASI_DARI','PRASYARAT_UNTUK','MEMPERDALAM','BERKAITAN_DENGAN'}

new_dir = set()
new_undir = set()
new_undir_typed = Counter()
new_typed = Counter()
new_concepts = set()
new_leaks = Counter()
new_raw_count = 0
for src_grade, doc in new_books.items():
    for ch in doc['chapters']:
        for st in ch.get('subtopics', []):
            for c in st.get('concepts', []):
                src_name = c['name'].strip().lower()
                for ln in c.get('cross_book_links', []) or []:
                    tgt_book  = ln.get('target_book')
                    tgt_name  = (ln.get('target_concept') or '').strip().lower()
                    rt        = ln.get('relation_type')
                    if not tgt_book or not tgt_name or not rt: continue
                    new_raw_count += 1
                    if rt not in LB_TYPES:
                        new_leaks[rt] += 1
                    new_undir.add(frozenset([(src_name,src_grade),(tgt_name,tgt_book)]))
                    new_dir.add(((src_name,src_grade),(tgt_name,tgt_book),rt))
                    new_typed[rt] += 1
                    new_concepts.add((src_name,src_grade)); new_concepts.add((tgt_name,tgt_book))

# count undirected typed
for k in new_dir:
    a, b, t = k
    new_undir_typed[t] += 1
# This double-counts symmetric mirror edges if both ends are stored. Let's dedupe properly:
seen_undir = set()
new_undir_dedup_typed = Counter()
for (a,b,t) in new_dir:
    key = (frozenset([a,b]), t)
    if key in seen_undir: continue
    seen_undir.add(key)
    new_undir_dedup_typed[t] += 1

# Pair-level overlap (undirected, type-agnostic)
overlap_undir = ann_undir & new_undir
overlap_undir_typed_match = 0
for (a,b,t) in ann_dir:
    if (frozenset([a,b]), t) in {(frozenset([x,y]),tt) for (x,y,tt) in new_dir}:
        overlap_undir_typed_match += 1

# Total concepts in each KG
ann_total_concepts = 342  # per derivation.md
new_total_concepts = sum(
    len(st.get('concepts',[]))
    for d in new_books.values()
    for ch in d['chapters']
    for st in ch.get('subtopics',[])
)

# ----- Print -----
def pct(n, d): return f'{100*n/max(d,1):.1f}%'

print('=' * 80)
print('ann-v1 (canonical: lintas_buku_edges.t075_k15.json)  vs  new/*_expert_boosted')
print('=' * 80)

print('\n--- TOTALS ---')
print(f'{"":<48} {"ann-v1":>12} {"new (boosted)":>18}')
print(f'{"Raw cross-book edges (as stored)":<48} {len(ann_dir):>12} {new_raw_count:>18}')
print(f'{"Unique undirected cross-book pairs":<48} {len(ann_undir):>12} {len(new_undir):>18}')
print(f'{"Unique concepts touched":<48} {len(ann_concepts):>12} {len(new_concepts):>18}')
print(f'{"... as % of total concepts in graph":<48} '
      f'{pct(len(ann_concepts), ann_total_concepts):>12} {pct(len(new_concepts), new_total_concepts):>18}'
      f'   (denominators: {ann_total_concepts} / {new_total_concepts})')

print('\n--- TYPE BREAKDOWN (on each side, % of total) ---')
all_types = sorted(set(ann_typed) | set(new_typed))
header = f'{"type":<30}{"ann-v1 n":>10}{"ann-v1 %":>10}{"new n":>10}{"new %":>10}'
print(header); print('-'*len(header))
for t in all_types:
    a = ann_typed.get(t,0); n = new_typed.get(t,0)
    flag = '  ← OPEN-VOCAB LEAK' if t not in LB_TYPES else ''
    print(f'{t:<30}{a:>10}{pct(a,len(ann_dir)):>10}{n:>10}{pct(n,new_raw_count):>10}{flag}')

print('\n--- OPEN-VOCAB LEAKS in new (types outside closed LINTAS_BUKU_* vocab) ---')
if new_leaks:
    for t,c in new_leaks.most_common():
        print(f'  {t}: {c}')
else:
    print('  none')

print('\n--- DOMAIN COVERAGE (cross-grade pair counts by subject pair) ---')
def pair_counts(undir_set):
    cnt = Counter()
    for fs in undir_set:
        grades = sorted([g for (_,g) in fs])
        cnt[' ↔ '.join(g.replace(' Kelas XII','') for g in grades)] += 1
    return cnt
print('  ann-v1:', dict(pair_counts(ann_undir).most_common()))
print('  new:   ', dict(pair_counts(new_undir).most_common()))

print('\n--- BASE vs BOOSTED cross_book_links delta (new) ---')
# Just to confirm: the boost adds NO cross-book edges
def count_cross(books):
    total = 0; types = Counter()
    for d in books.values():
        for ch in d['chapters']:
            for st in ch.get('subtopics', []):
                for c in st.get('concepts', []):
                    for ln in c.get('cross_book_links', []) or []:
                        total += 1
                        types[ln.get('relation_type','?')] += 1
    return total, types
n_base, t_base = count_cross(new_base)
n_boost, t_boost = count_cross(new_books)
print(f'  base   cross-book edges: {n_base}')
print(f'  boosted cross-book edges: {n_boost}  (delta = {n_boost-n_base:+d})')

print('\n--- PAIR-LEVEL OVERLAP (undirected, type-agnostic) ---')
print(f'  Overlapping undirected pairs (any type): {len(overlap_undir)} '
      f'/ {len(ann_undir)} ann-v1 / {len(new_undir)} new')
print(f'  Overlapping pairs with same type:       {overlap_undir_typed_match}')
if overlap_undir:
    print('  Examples:')
    for fs in list(overlap_undir)[:8]:
        print(f'    {sorted(fs)}')

print('\n--- CONFIDENCE / PROVENANCE ---')
conf = [c for c in ann_confidence if c is not None]
print(f'  ann-v1: confidence on every edge (n={len(conf)}, '
      f'min={min(conf):.2f}, avg={sum(conf)/len(conf):.2f}, max={max(conf):.2f})')
# Check new for confidence field
new_has_conf = 0
for d in new_books.values():
    for ch in d['chapters']:
        for st in ch.get('subtopics', []):
            for c in st.get('concepts', []):
                for ln in c.get('cross_book_links', []) or []:
                    if 'confidence' in ln or 'score' in ln: new_has_conf += 1
print(f'  new: cross-book edges with confidence/score: {new_has_conf} / {new_raw_count}')
