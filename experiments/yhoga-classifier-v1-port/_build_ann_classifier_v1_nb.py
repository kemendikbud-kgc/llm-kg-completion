"""Build ANN_CLASSIFIER_V1.ipynb for Yhoga — mirrors src/completion.py exactly.

Run once: `python _build_ann_classifier_v1_nb.py` to (re)generate the notebook.
The .ipynb is the deliverable; this script is the generator so the JSON stays clean.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
OUT  = HERE / 'ANN_CLASSIFIER_V1.ipynb'

def md(src: str): return {'cell_type':'markdown','metadata':{},'source':src.splitlines(True)}
def code(src: str): return {'cell_type':'code','metadata':{},'source':src.splitlines(True),
                            'execution_count':None,'outputs':[]}

cells = []

# ── Title ───────────────────────────────────────────────────────────
cells.append(md(r"""# ann-classifier-v1 — Cross-Book KGC Pipeline (configurable)

Self-contained notebook that runs ANN-similarity + LLM-classifier cross-book
knowledge graph completion against a Neo4j Aura instance. All hyperparameters
exposed in the cell below — no other edits needed to swap embedding model,
LLM model, threshold, top_k, batch size, or replay target.

## Pipeline overview

```mermaid
flowchart TB
    A[Concepts in Neo4j] --> B[build embed text<br/>name + description<br/>+ materi_pokok_ref + grade]
    B --> C[embed via Gemini<br/>or sentence-transformers]
    C --> D[write Concept.embedding<br/>+ create vector index]
    D --> E[ANN top-k cosine<br/>per Concept]
    E --> F{filters}
    F -->|cross-grade only| G[candidate pairs]
    F -->|skip existing typed edges| G
    G --> H[fetch KONTEKS GRAF<br/>parent Bab + out-edges<br/>+ shared neighbors]
    H --> I[LLM classifier<br/>closed 5-type vocab<br/>+ response_schema]
    I --> J[disk cache<br/>by ctx-fingerprint]
    I --> K[lintas_buku_edges.json]
    K -->|optional REPLAY_TO_NEO4J| L[MERGE LINTAS_BUKU_*<br/>into Neo4j]
```

**Defaults** match the canonical reference run (`lintas_buku_edges.t075_k15.json`):
`threshold=0.75`, `top_k=15`, `embed=gemini-embedding-001`, `chat=gemini-2.5-flash`,
`temperature=0.2`, `batch_size=10`, closed-vocab `response_schema` enforcement.

> **Mermaid rendering**: works natively in JupyterLab 4+, Jupyter Notebook 7+,
> and VS Code. If you open this in Colab, run the `render_mermaid()` helper
> cell below — it embeds Mermaid via CDN so diagrams render there too.
"""))

# Optional Colab-compatible Mermaid renderer (no-op in modern Jupyter/VS Code).
cells.append(code(r"""# Optional: Colab Mermaid renderer (skip if your Jupyter/VS Code already renders mermaid in markdown).
# Usage:
#   render_mermaid('''flowchart LR; A-->B''')

def render_mermaid(diagram: str, height: int = 400):
    from IPython.display import HTML, display
    html = f'''
<div class="mermaid" style="background:white;padding:1em;border:1px solid #ddd;">{diagram}</div>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({{startOnLoad: true, theme: 'default'}});
  mermaid.run();
</script>
'''
    display(HTML(html))
"""))

# ── Hyperparams ─────────────────────────────────────────────────────
cells.append(md("## Hyperparameters"))

cells.append(code(r"""# ===== HYPERPARAMETERS — edit these =====

# --- Neo4j upstream ---
NEO4J_URI      = 'neo4j+ssc://772674a6.databases.neo4j.io'
NEO4J_USER     = '772674a6'
NEO4J_PASSWORD = 'dCFp5Cik9D0JMfo_cL7WenO5K9zDb_w7n3HegK8jeJo'
NEO4J_DATABASE = '772674a6'

# --- Embedding ---
# Backend selector: 'gemini' (default, matches ann-v1) or 'sentence-transformers'
EMBED_BACKEND = 'gemini'
EMBED_MODEL   = 'gemini-embedding-001'   # for ST: 'paraphrase-multilingual-mpnet-base-v2'
EMBED_DIM     = 3072                     # gemini-embedding-001: 3072; mpnet: 768
EMBED_BATCH   = 32

# --- ANN candidate retrieval ---
TOP_K                     = 15           # ann-v1 canonical
COS_THRESHOLD             = 0.75         # ann-v1 canonical
CROSS_GRADE_ONLY          = True         # LINTAS_BUKU enforced — drop same-grade pairs
SKIP_EXISTING_TYPED_EDGES = True         # drop pairs already typed-connected
VECTOR_INDEX_NAME         = 'concept_embedding_idx'

# --- LLM classifier ---
GEMINI_API_KEY    = ''                   # paste your key or read from env
LLM_MODEL         = 'gemini-2.5-flash'
LLM_TEMPERATURE   = 0.2
BATCH_SIZE        = 10                   # 1 = per-pair; >1 = bundle pairs into one prompt
NEIGHBORHOOD_MAX_EDGES = 5               # cap out-edges per concept in KONTEKS GRAF block
CONF_FILTER       = 0.0                  # post-classify confidence floor (0 = keep all)
PROMPT_VERSION    = 'v4-yhoga-nb'        # cache invalidation knob

# --- Closed LINTAS_BUKU vocab (do not change unless ontology changes) ---
LINTAS_BUKU_TYPES = [
    'LINTAS_BUKU_SAMA_DENGAN',
    'LINTAS_BUKU_APLIKASI_DARI',
    'LINTAS_BUKU_PRASYARAT_UNTUK',
    'LINTAS_BUKU_MEMPERDALAM',
    'LINTAS_BUKU_BERKAITAN_DENGAN',
]

# --- IO ---
OUTPUT_JSON = 'lintas_buku_edges.t075_k15.json'   # follow ann-v1 naming convention
CACHE_DIR   = '.classifier_cache'
REPLAY_TO_NEO4J = False                  # set True to MERGE edges into the DB after dump
"""))

# ── Imports ────────────────────────────────────────────────────────
cells.append(md("## Imports & driver"))

cells.append(code(r"""import os, json, hashlib, time
from pathlib import Path
from datetime import date
from typing import Optional

from neo4j import GraphDatabase

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session(database=NEO4J_DATABASE) as s:
    r = s.run('MATCH (c:Concept) RETURN count(c) AS n').single()
    print(f'Connected. Concept count: {r["n"]}')
"""))

# ── Stage 1 — Embed ────────────────────────────────────────────────
cells.append(md(r"""## Stage 1 — Embed concepts and store on Neo4j

Mirrors `find_similar_pairs_ann()` and `YhogaAdapter.build_embed_text()` /
`store_node_embeddings()` from `src/completion.py`.
"""))

cells.append(code(r"""# 1a. Pull concepts from Neo4j (name, description, materi_pokok_ref, grade, parent Bab)

PULL_QUERY = '''
MATCH (c:Concept)
OPTIONAL MATCH (ch:Chapter)-[:HAS_SUBTOPIC]->(:Subtopic)-[:HAS_CONCEPT]->(c)
RETURN
    c.name              AS name,
    c.description       AS description,
    c.materi_pokok_ref  AS materi_pokok_ref,
    c.grade             AS grade,
    ch.name             AS bab
'''

with driver.session(database=NEO4J_DATABASE) as s:
    concepts = [dict(r) for r in s.run(PULL_QUERY)]
print(f'Pulled {len(concepts)} concepts')
print('Sample:', concepts[0] if concepts else None)
"""))

cells.append(code(r"""# 1b. Build embed text — Yhoga adapter convention
# Format: name + description + materi_pokok_ref + grade (one block per concept)

def build_embed_text(c: dict) -> str:
    parts = [c['name'] or '']
    if c.get('description'):       parts.append(c['description'])
    if c.get('materi_pokok_ref'):  parts.append(f"Materi Pokok: {c['materi_pokok_ref']}")
    if c.get('grade'):             parts.append(f"Mata Pelajaran: {c['grade']}")
    return '. '.join(p.strip() for p in parts if p)

embed_texts = [build_embed_text(c) for c in concepts]
print('Sample embed text:')
print('  ', embed_texts[0][:200])
"""))

cells.append(code(r"""# 1c. Embed — dispatch on EMBED_BACKEND
# Choices: 'gemini' (matches ann-v1) or 'sentence-transformers' (matches v2)

if EMBED_BACKEND == 'gemini':
    from google import genai
    embed_client = genai.Client(api_key=GEMINI_API_KEY or os.environ.get('GEMINI_API_KEY',''))
    embeddings = []
    for i in range(0, len(embed_texts), EMBED_BATCH):
        batch = embed_texts[i:i+EMBED_BATCH]
        resp = embed_client.models.embed_content(model=EMBED_MODEL, contents=batch)
        embeddings.extend([e.values for e in resp.embeddings])
        print(f'  embedded {min(i+EMBED_BATCH, len(embed_texts))}/{len(embed_texts)}')

elif EMBED_BACKEND == 'sentence-transformers':
    from sentence_transformers import SentenceTransformer
    import numpy as np
    embedder = SentenceTransformer(EMBED_MODEL)
    embeddings = embedder.encode(
        embed_texts, normalize_embeddings=True,
        show_progress_bar=True, batch_size=EMBED_BATCH,
    )
    embeddings = [list(map(float, v)) for v in embeddings]

else:
    raise ValueError(f'Unknown EMBED_BACKEND: {EMBED_BACKEND!r}')

assert len(embeddings) == len(concepts)
EMBED_DIM = len(embeddings[0])  # override config with actual dim
print(f'embedded {len(embeddings)} concepts, dim={EMBED_DIM}')
"""))

cells.append(code(r"""# 1d. Write c.embedding + c.last_embed_model to Neo4j
# Idempotent — re-running just overwrites.

WRITE_EMBED_QUERY = '''
UNWIND $rows AS row
MATCH (c:Concept {name: row.name})
WHERE coalesce(c.grade, '') = coalesce(row.grade, '')
SET c.embedding = row.embedding,
    c.last_embed_model = $model
'''

rows = [
    {'name': c['name'], 'grade': c['grade'], 'embedding': e}
    for c, e in zip(concepts, embeddings)
]
with driver.session(database=NEO4J_DATABASE) as s:
    s.run(WRITE_EMBED_QUERY, rows=rows, model=EMBED_MODEL).consume()
print(f'Wrote {len(rows)} embeddings to Concept.embedding')
"""))

cells.append(code(r"""# 1e. Create vector index on Concept.embedding (cosine)
# Drops + recreates so dim changes don't conflict.

with driver.session(database=NEO4J_DATABASE) as s:
    try:
        s.run(f"DROP INDEX {VECTOR_INDEX_NAME} IF EXISTS").consume()
    except Exception as e:
        print('  (drop skipped):', e)
    s.run(f'''
        CREATE VECTOR INDEX {VECTOR_INDEX_NAME} IF NOT EXISTS
        FOR (c:Concept) ON c.embedding
        OPTIONS {{
          indexConfig: {{
            `vector.dimensions`: $dim,
            `vector.similarity_function`: 'cosine'
          }}
        }}
    ''', dim=EMBED_DIM).consume()
    # Wait briefly for index to come online
    for _ in range(30):
        st = s.run(f"SHOW INDEXES WHERE name='{VECTOR_INDEX_NAME}'").single()
        if st and st['state'] == 'ONLINE':
            break
        time.sleep(1)
    print('Index state:', st['state'] if st else 'missing')
"""))

# ── Stage 2 — ANN ──────────────────────────────────────────────────
cells.append(md(r"""## Stage 2 — ANN candidate retrieval

Mirrors `find_similar_pairs_ann()` from `src/completion.py`. Uses Neo4j
`db.index.vector.queryNodes()` for proper ANN (O(n log n)) rather than
brute-force NumPy O(n²). Applies `CROSS_GRADE_ONLY` + `SKIP_EXISTING_TYPED_EDGES`
filters as the in-memory layer does in `find_similar_pairs_ann`.
"""))

cells.append(code(r"""# 2a. Query top-k similar per concept, then filter

QUERY_ANN = '''
MATCH (q:Concept {name: $name})
WHERE coalesce(q.grade,'') = coalesce($grade,'')
CALL db.index.vector.queryNodes($idx, $k, q.embedding) YIELD node, score
WHERE node.name <> q.name AND score >= $threshold
RETURN node.name AS name, coalesce(node.grade,'') AS grade, score
'''

# Build grade lookup for cross-grade filter
grade_by_name = {c['name']: (c.get('grade') or '') for c in concepts}

pairs = []
seen = set()
with driver.session(database=NEO4J_DATABASE) as s:
    for c in concepts:
        result = s.run(
            QUERY_ANN,
            name=c['name'], grade=c['grade'] or '',
            idx=VECTOR_INDEX_NAME, k=TOP_K, threshold=COS_THRESHOLD,
        )
        for r in result:
            sg = grade_by_name.get(c['name'], '')
            tg = grade_by_name.get(r['name'], '')
            if CROSS_GRADE_ONLY:
                if not sg or not tg or sg == tg:
                    continue
            key = tuple(sorted([c['name'], r['name']]))
            if key in seen:
                continue
            seen.add(key)
            pairs.append({
                'source': c['name'], 'source_grade': sg,
                'target': r['name'], 'target_grade': tg,
                'similarity': float(r['score']),
            })

print(f'After ANN + cross-grade filter: {len(pairs)} undirected pairs')
"""))

cells.append(code(r"""# 2b. Skip pairs that already have a non-SIMILAR_TO typed edge between them

if SKIP_EXISTING_TYPED_EDGES and pairs:
    SKIP_QUERY = '''
    UNWIND $pairs AS p
    MATCH (a:Concept {name: p.source}) WHERE coalesce(a.grade,'') = coalesce(p.source_grade,'')
    MATCH (b:Concept {name: p.target}) WHERE coalesce(b.grade,'') = coalesce(p.target_grade,'')
    MATCH (a)-[r]-(b)
    WHERE NOT type(r) IN ['SIMILAR_TO']
    RETURN p.source AS s, p.source_grade AS sg, p.target AS t, p.target_grade AS tg
    '''
    with driver.session(database=NEO4J_DATABASE) as s:
        already = {(r['s'], r['sg'], r['t'], r['tg']) for r in s.run(SKIP_QUERY, pairs=pairs)}
    before = len(pairs)
    pairs = [
        p for p in pairs
        if (p['source'], p['source_grade'], p['target'], p['target_grade']) not in already
        and (p['target'], p['target_grade'], p['source'], p['source_grade']) not in already
    ]
    print(f'Dropped {before - len(pairs)}/{before} pairs already typed-connected')

print(f'Final candidate pairs: {len(pairs)}')
"""))

# ── Stage 3 — Graph context ────────────────────────────────────────
cells.append(md(r"""## Stage 3 — Graph context (KONTEKS GRAF)

For each candidate pair, fetch (parent Bab of each concept, top-N typed
out-edges of each concept, shared-neighbor concepts). The LLM gets this as a
`KONTEKS GRAF` block in the prompt so it can use existing graph signal as
evidence — not just the two concept strings + similarity score in isolation.
"""))

cells.append(code(r"""# 3a. Pull (bab, out_edges) for every concept referenced in pairs.
# One round-trip, dedupe by name+grade.

referenced = sorted({(p['source'], p['source_grade']) for p in pairs}
                  | {(p['target'], p['target_grade']) for p in pairs})

CTX_QUERY = '''
UNWIND $nodes AS n
MATCH (c:Concept {name: n.name})
WHERE coalesce(c.grade,'') = coalesce(n.grade,'')
OPTIONAL MATCH (ch:Chapter)-[:HAS_SUBTOPIC]->(:Subtopic)-[:HAS_CONCEPT]->(c)
WITH n, c, ch
OPTIONAL MATCH (c)-[r]->(t)
WHERE NOT type(r) IN ['SIMILAR_TO']
  AND NOT type(r) STARTS WITH 'HAS_'
WITH n, c, ch,
     collect({rel_type: type(r), target: t.name,
              confidence: coalesce(r.confidence, null)})[..$maxe] AS out_edges
RETURN n.name AS name, n.grade AS grade,
       ch.name AS bab, out_edges
'''

ctx_by_key = {}
with driver.session(database=NEO4J_DATABASE) as s:
    for r in s.run(CTX_QUERY,
                   nodes=[{'name':n, 'grade':g} for n,g in referenced],
                   maxe=NEIGHBORHOOD_MAX_EDGES):
        # filter out edges with null rel_type/target (from OPTIONAL MATCH no-hit)
        edges = [e for e in r['out_edges']
                 if e.get('rel_type') and e.get('target')]
        ctx_by_key[(r['name'], r['grade'] or '')] = {
            'bab': r['bab'],
            'out_edges': edges,
        }

print(f'Fetched context for {len(ctx_by_key)} concepts')

def shared_neighbors(ctx_a, ctx_b):
    ta = {e['target'] for e in ctx_a.get('out_edges',[]) if e.get('target')}
    tb = {e['target'] for e in ctx_b.get('out_edges',[]) if e.get('target')}
    return sorted(ta & tb)
"""))

# ── Stage 4 — Classify ─────────────────────────────────────────────
cells.append(md(r"""## Stage 4 — LLM classification

Closed-vocab classifier (5 LINTAS_BUKU_* types + `NONE`). Uses Google GenAI
SDK's `response_schema` with `enum` to enforce vocabulary at parse time — no
open-vocab leaks possible. KONTEKS GRAF block injects each concept's parent
Bab + typed out-edges + shared neighbors so the LLM uses existing graph
signal as evidence.

```mermaid
flowchart LR
    P[candidate pair] --> CK[compute<br/>ctx-fingerprint]
    CK --> CH{cache hit?}
    CH -->|yes| OUT[rel_type<br/>confidence<br/>description]
    CH -->|no| NB[build KONTEKS GRAF block<br/>bab + out_edges + shared]
    NB --> PR[render prompt<br/>+ response_schema enum]
    PR --> LLM[Gemini<br/>temperature=0.2]
    LLM --> OUT
    OUT --> ST[cache.put<br/>keyed by ctx-fingerprint]
```

Cache is per-pair, fingerprinted by neighborhood state so re-runs after the
graph gains edges produce a cache miss and re-classify.
"""))

cells.append(code(r"""# 4a. Cache helpers — keyed by (pair_sorted, model, prompt_version, ctx_fingerprint)

cache_root = Path(CACHE_DIR); cache_root.mkdir(exist_ok=True)

def ctx_fingerprint(ctx_a, ctx_b, shared):
    payload = json.dumps({
        'a': {'bab': ctx_a.get('bab'), 'edges': ctx_a.get('out_edges', [])},
        'b': {'bab': ctx_b.get('bab'), 'edges': ctx_b.get('out_edges', [])},
        'shared': shared,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(payload.encode('utf-8')).hexdigest()[:12]

def cache_key(source, target, sg, tg, fp):
    a, b = sorted([(source, sg), (target, tg)])
    parts = [a[0], a[1], b[0], b[1], f'model:{LLM_MODEL}', f'pv:{PROMPT_VERSION}', f'ctx:{fp}']
    return hashlib.sha256('||'.join(parts).encode('utf-8')).hexdigest()

def cache_get(key):
    p = cache_root / f'{key}.json'
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    return None

def cache_put(key, value):
    p = cache_root / f'{key}.json'
    p.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
"""))

cells.append(code(r"""# 4b. Prompt template + KONTEKS GRAF builder
# Stays close to `_build_neighborhood_block` + `_LINTAS_BUKU_*_PROMPT`.

LB_VOCAB_ADVICE = (
    "Gunakan konteks graf ini sebagai bukti tambahan. Tetangga bersama menandakan "
    "A dan B kemungkinan LINTAS_BUKU_BERKAITAN_DENGAN atau LINTAS_BUKU_SAMA_DENGAN. "
    "Jika tipe lain tidak tepat, gunakan LINTAS_BUKU_BERKAITAN_DENGAN sebagai fallback.\n"
)

def format_out_edges(edges):
    if not edges: return '  (tidak ada)'
    lines = []
    for e in edges:
        c = e.get('confidence')
        cs = f" (conf: {c:.2f})" if isinstance(c, (int, float)) else ''
        lines.append(f"  - {e['rel_type']} -> \"{e['target']}\"{cs}")
    return '\n'.join(lines)

def build_neighborhood_block(name_a, ctx_a, name_b, ctx_b, shared):
    bab_a, bab_b = ctx_a.get('bab'), ctx_b.get('bab')
    edges_a, edges_b = ctx_a.get('out_edges', []), ctx_b.get('out_edges', [])
    if not (bab_a or bab_b or edges_a or edges_b or shared):
        return ''
    bab_note = ''
    if bab_a and bab_b:
        bab_note = '(Bab yang sama)' if bab_a == bab_b else '(Bab berbeda)'
    return (
        "========================\n"
        "KONTEKS GRAF (HUBUNGAN YANG SUDAH ADA)\n"
        "========================\n"
        f'Konsep A ("{name_a}") berada di Bab: {bab_a or "(tidak diketahui)"}\n'
        f"Hubungan A yang sudah ada di graf:\n{format_out_edges(edges_a)}\n\n"
        f'Konsep B ("{name_b}") berada di Bab: {bab_b or "(tidak diketahui)"} {bab_note}\n'
        f"Hubungan B yang sudah ada di graf:\n{format_out_edges(edges_b)}\n\n"
        f"Tetangga bersama: {', '.join(shared) if shared else '(tidak ada)'}\n\n"
        f"{LB_VOCAB_ADVICE}"
    )

CLASSIFY_PROMPT_SINGLE = '''Anda adalah ahli kurikulum sains yang menganalisis keterkaitan lintas-buku antara konsep
pada Mata Pelajaran berbeda (Biologi/Fisika/Kimia Kelas XII pada Kurikulum Merdeka).

Diberikan dua konsep yang memiliki kemiripan semantik tinggi tetapi berasal dari buku berbeda:

- Konsep A: "{name_a}"
  Mata Pelajaran A: "{grade_a}"
  Deskripsi A: "{desc_a}"
  Materi Pokok A: {mp_a}

- Konsep B: "{name_b}"
  Mata Pelajaran B: "{grade_b}"
  Deskripsi B: "{desc_b}"
  Materi Pokok B: {mp_b}

{neighborhood_block}
Klasifikasikan hubungan lintas-buku antara A dan B sebagai SALAH SATU dari:

1. LINTAS_BUKU_SAMA_DENGAN: A dan B merujuk pada entitas yang sama meskipun di buku berbeda.
2. LINTAS_BUKU_APLIKASI_DARI: A adalah penerapan konsep B di disiplin lain. Asimetris.
3. LINTAS_BUKU_PRASYARAT_UNTUK: A pada satu MP adalah prasyarat memahami B pada MP lain. Asimetris.
4. LINTAS_BUKU_MEMPERDALAM: A memperdalam pemahaman B di buku lain. Asimetris.
5. LINTAS_BUKU_BERKAITAN_DENGAN: berkaitan umum lintas-buku, fallback. Simetris.
6. NONE: kemiripan hanya permukaan; tidak terkait secara curricular.

PENTING: Hanya klasifikasikan sebagai LINTAS_BUKU_* jika Mata Pelajaran A != Mata Pelajaran B.
Jika sama, kembalikan NONE.

Kembalikan JSON sesuai schema.'''

CLASSIFY_PROMPT_BATCH = '''Anda adalah ahli kurikulum sains yang menganalisis keterkaitan lintas-buku antara konsep
pada Mata Pelajaran berbeda (Biologi/Fisika/Kimia Kelas XII pada Kurikulum Merdeka).

Untuk SETIAP pasangan konsep di bawah ini, klasifikasikan hubungan lintas-buku sebagai
SALAH SATU dari: LINTAS_BUKU_SAMA_DENGAN, LINTAS_BUKU_APLIKASI_DARI,
LINTAS_BUKU_PRASYARAT_UNTUK, LINTAS_BUKU_MEMPERDALAM, LINTAS_BUKU_BERKAITAN_DENGAN, NONE.

ATURAN: Klasifikasikan sebagai salah satu dari 5 tipe LINTAS_BUKU_* HANYA jika
Mata Pelajaran A != Mata Pelajaran B. Jika sama, kembalikan NONE.

================ PASANGAN KONSEP ================
{pairs_block}
=================================================

Kembalikan JSON dengan field "items": array berisi satu entri per pasangan
(total {n_pairs} entri), setiap entri memiliki:
- pair_index: int
- rel_type: salah satu dari 5 LINTAS_BUKU_* atau NONE
- confidence: float 0.0-1.0
- description: satu kalimat singkat (<=25 kata) dalam bahasa Indonesia, kosong jika NONE.'''
"""))

cells.append(code(r"""# 4c. Response schemas — closed enum on rel_type via JSON Schema

SINGLE_RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'rel_type':    {'type': 'string', 'enum': LINTAS_BUKU_TYPES + ['NONE']},
        'confidence':  {'type': 'number'},
        'description': {'type': 'string'},
    },
    'required': ['rel_type', 'confidence', 'description'],
}

BATCH_RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'items': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'pair_index':  {'type': 'integer'},
                    'rel_type':    {'type': 'string', 'enum': LINTAS_BUKU_TYPES + ['NONE']},
                    'confidence':  {'type': 'number'},
                    'description': {'type': 'string'},
                },
                'required': ['pair_index', 'rel_type', 'confidence', 'description'],
            },
        },
    },
    'required': ['items'],
}

from google import genai
from google.genai import types as gtypes
llm_client = genai.Client(api_key=GEMINI_API_KEY or os.environ.get('GEMINI_API_KEY',''))

def classify_pair(name_a, grade_a, desc_a, mp_a,
                  name_b, grade_b, desc_b, mp_b,
                  neighborhood_block: str):
    prompt = CLASSIFY_PROMPT_SINGLE.format(
        name_a=name_a, grade_a=grade_a or '(tidak diketahui)',
        desc_a=desc_a or name_a, mp_a=mp_a or '(tidak ada)',
        name_b=name_b, grade_b=grade_b or '(tidak diketahui)',
        desc_b=desc_b or name_b, mp_b=mp_b or '(tidak ada)',
        neighborhood_block=neighborhood_block,
    )
    resp = llm_client.models.generate_content(
        model=LLM_MODEL, contents=prompt,
        config=gtypes.GenerateContentConfig(
            temperature=LLM_TEMPERATURE,
            response_mime_type='application/json',
            response_schema=SINGLE_RESPONSE_SCHEMA,
        ),
    )
    return json.loads(resp.text)

def classify_batch(pair_payloads: list[dict]):
    blocks = []
    for i, p in enumerate(pair_payloads):
        block = (
            f"[{i}]\n"
            f"  Konsep A: \"{p['name_a']}\"\n"
            f"  Mata Pelajaran A: \"{p['grade_a'] or '(tidak diketahui)'}\"\n"
            f"  Deskripsi A: \"{p['desc_a'] or p['name_a']}\"\n"
            f"  Materi Pokok A: {p['mp_a'] or '(tidak ada)'}\n"
            f"  Konsep B: \"{p['name_b']}\"\n"
            f"  Mata Pelajaran B: \"{p['grade_b'] or '(tidak diketahui)'}\"\n"
            f"  Deskripsi B: \"{p['desc_b'] or p['name_b']}\"\n"
            f"  Materi Pokok B: {p['mp_b'] or '(tidak ada)'}"
        )
        if p.get('neighborhood_block'):
            indented = '\n'.join('  ' + l for l in p['neighborhood_block'].splitlines())
            block += '\n' + indented
        blocks.append(block)
    prompt = CLASSIFY_PROMPT_BATCH.format(
        pairs_block='\n\n'.join(blocks), n_pairs=len(pair_payloads)
    )
    resp = llm_client.models.generate_content(
        model=LLM_MODEL, contents=prompt,
        config=gtypes.GenerateContentConfig(
            temperature=LLM_TEMPERATURE,
            response_mime_type='application/json',
            response_schema=BATCH_RESPONSE_SCHEMA,
        ),
    )
    return json.loads(resp.text)['items']
"""))

cells.append(code(r"""# 4d. Run classification — cache-aware, per-pair or batched

name_to_info = {(c['name'], c['grade'] or ''): c for c in concepts}

def info_for(pair, side):
    name, grade = pair[f'{side}'], pair[f'{side}_grade']
    info = name_to_info.get((name, grade), {})
    ctx = ctx_by_key.get((name, grade), {'bab': None, 'out_edges': []})
    return {
        'name': name, 'grade': grade,
        'description': info.get('description',''),
        'materi_pokok_ref': info.get('materi_pokok_ref',''),
        'bab': ctx.get('bab'),
        'out_edges': ctx.get('out_edges', []),
    }

results = [None] * len(pairs)
cache_hits = 0
uncached_idx = []

for i, p in enumerate(pairs):
    a = info_for(p, 'source')
    b = info_for(p, 'target')
    shared = shared_neighbors(
        ctx_by_key.get((a['name'], a['grade']), {}),
        ctx_by_key.get((b['name'], b['grade']), {}),
    )
    fp = ctx_fingerprint(ctx_by_key.get((a['name'], a['grade']), {}),
                        ctx_by_key.get((b['name'], b['grade']), {}),
                        shared)
    key = cache_key(p['source'], p['target'], p['source_grade'], p['target_grade'], fp)
    cached = cache_get(key)
    if cached is not None:
        results[i] = {**p, **cached}
        cache_hits += 1
    else:
        uncached_idx.append((i, a, b, shared, fp, key))

print(f'cache hits: {cache_hits}/{len(pairs)}')
print(f'pairs to classify: {len(uncached_idx)}')

# Process uncached
processed = cache_hits
failures = 0

for start in range(0, len(uncached_idx), BATCH_SIZE):
    chunk = uncached_idx[start:start+BATCH_SIZE]
    try:
        if BATCH_SIZE == 1:
            i, a, b, shared, fp, key = chunk[0]
            nb_block = build_neighborhood_block(a['name'], a, b['name'], b, shared)
            raw = classify_pair(
                a['name'], a['grade'], a['description'], a['materi_pokok_ref'],
                b['name'], b['grade'], b['description'], b['materi_pokok_ref'],
                nb_block,
            )
            outs = [(i, key, raw)]
        else:
            payloads = []
            for (_, a, b, shared, _, _) in chunk:
                nb_block = build_neighborhood_block(a['name'], a, b['name'], b, shared)
                payloads.append({
                    'name_a': a['name'], 'grade_a': a['grade'],
                    'desc_a':  a['description'], 'mp_a': a['materi_pokok_ref'],
                    'name_b': b['name'], 'grade_b': b['grade'],
                    'desc_b':  b['description'], 'mp_b': b['materi_pokok_ref'],
                    'neighborhood_block': nb_block,
                })
            items = classify_batch(payloads)
            by_idx = {it['pair_index']: it for it in items}
            outs = []
            for j, (i, _, _, _, _, key) in enumerate(chunk):
                raw = by_idx.get(j, {'rel_type':'NONE','confidence':0.0,'description':''})
                outs.append((i, key, raw))
    except Exception as e:
        print(f'  [batch failed at {start}]: {e}')
        for (i, _, _, _, _, _) in chunk:
            results[i] = {**pairs[i], 'rel_type':'NONE','confidence':0.0,'description':''}
        failures += len(chunk)
        processed += len(chunk)
        continue

    for i, key, raw in outs:
        rec = {
            'rel_type':    raw.get('rel_type','NONE'),
            'confidence':  float(raw.get('confidence', 0.0)),
            'description': raw.get('description',''),
        }
        results[i] = {**pairs[i], **rec}
        cache_put(key, rec)
    processed += len(chunk)
    print(f'  classified {processed}/{len(pairs)}')

print(f'done. failures={failures}')
"""))

# ── Stage 5 — Dump ─────────────────────────────────────────────────
cells.append(md(r"""## Stage 5 — Dump `lintas_buku_edges.json`

Friend-llm shape, drop-in compatible with `ann-classifier-v1` outputs.
Mirrors `dump_lintas_buku_results()` from `src/completion.py`.
"""))

cells.append(code(r"""# 5a. Build dump (friend-llm shape), drop "NONE" + low-confidence

real_edges = [r for r in results if r.get('rel_type') and r['rel_type'] != 'NONE']
if CONF_FILTER > 0:
    real_edges = [r for r in real_edges if r.get('confidence', 0) >= CONF_FILTER]

# instance counts snapshot
with driver.session(database=NEO4J_DATABASE) as s:
    inst = {}
    for r in s.run('MATCH (n) RETURN labels(n)[0] AS l, count(n) AS n'):
        if r['l']: inst[r['l']] = r['n']
    tot = s.run('MATCH ()-[r]->() RETURN count(r) AS n').single()
    inst['total_relationships'] = tot['n'] if tot else 0

breakdown = {}
edges_json = []
for r in real_edges:
    rt = r['rel_type']
    breakdown[rt] = breakdown.get(rt, 0) + 1
    suffix = rt.removeprefix('LINTAS_BUKU_') if rt.startswith('LINTAS_BUKU_') else rt
    edges_json.append({
        'rel_type': rt,
        'source_label': 'Concept',
        'source_name':  r['source'],
        'source_grade': r['source_grade'],
        'target_label': 'Concept',
        'target_name':  r['target'],
        'target_grade': r['target_grade'],
        'properties': {
            'description':   r.get('description',''),
            'relation_type': suffix,
            'confidence':    float(r.get('confidence', 0.0)),
            'method':        'ann-classifier-v1',
        },
    })

doc = {
    'version': 'ann-classifier-v1',
    'source_state': 'extraction-current',
    'date_captured': date.today().isoformat(),
    'captured_from': 'Yhoga Neo4j Aura Free instance',
    'method': 'ann + classifier',
    'params': {
        'embed_backend': EMBED_BACKEND,
        'embed_model':   EMBED_MODEL,
        'embed_dim':     EMBED_DIM,
        'chat_model':    LLM_MODEL,
        'temperature':   LLM_TEMPERATURE,
        'threshold':     COS_THRESHOLD,
        'top_k':         TOP_K,
        'scope':         'cross' if CROSS_GRADE_ONLY else 'all',
        'batch_size':    BATCH_SIZE,
        'conf_filter':   CONF_FILTER,
        'prompt_version': PROMPT_VERSION,
    },
    'edge_count': len(edges_json),
    'edge_type_breakdown': dict(sorted(breakdown.items(), key=lambda kv: -kv[1])),
    'instance_counts_at_capture': inst,
    'edges': edges_json,
}

Path(OUTPUT_JSON).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Wrote {len(edges_json)} edges across {len(breakdown)} types to {OUTPUT_JSON}')
print('Breakdown:', doc['edge_type_breakdown'])
"""))

# ── Stage 6 — Replay ──────────────────────────────────────────────
cells.append(md(r"""## Stage 6 — Optional replay to Neo4j

Set `REPLAY_TO_NEO4J = True` in hyperparams to MERGE the edges into upstream.
Keyed by `(Concept.name, Concept.grade)`. Edge properties: description,
relation_type (suffix), confidence, method.
"""))

cells.append(code(r"""# 6a. Replay — only runs if REPLAY_TO_NEO4J is True

if not REPLAY_TO_NEO4J:
    print('REPLAY_TO_NEO4J is False, skipping write-back.')
else:
    REPLAY_QUERY = '''
    UNWIND $edges AS e
    MATCH (a:Concept {name: e.source_name})
    WHERE coalesce(a.grade,'') = coalesce(e.source_grade,'')
    MATCH (b:Concept {name: e.target_name})
    WHERE coalesce(b.grade,'') = coalesce(e.target_grade,'')
    CALL apoc.merge.relationship(a, e.rel_type, {}, e.properties, b) YIELD rel
    RETURN count(rel) AS n
    '''
    # If APOC is not available, use static type per edge type instead (slower, simpler):
    SIMPLE_REPLAY = '''
    UNWIND $edges AS e
    MATCH (a:Concept {name: e.source_name}) WHERE coalesce(a.grade,'') = coalesce(e.source_grade,'')
    MATCH (b:Concept {name: e.target_name}) WHERE coalesce(b.grade,'') = coalesce(e.target_grade,'')
    CALL (a, b, e) {
      WITH a, b, e
      WHERE e.rel_type = 'LINTAS_BUKU_SAMA_DENGAN'
      MERGE (a)-[r:LINTAS_BUKU_SAMA_DENGAN]->(b)
      SET r += e.properties RETURN 1 AS n
    UNION
      WITH a, b, e
      WHERE e.rel_type = 'LINTAS_BUKU_APLIKASI_DARI'
      MERGE (a)-[r:LINTAS_BUKU_APLIKASI_DARI]->(b)
      SET r += e.properties RETURN 1 AS n
    UNION
      WITH a, b, e
      WHERE e.rel_type = 'LINTAS_BUKU_PRASYARAT_UNTUK'
      MERGE (a)-[r:LINTAS_BUKU_PRASYARAT_UNTUK]->(b)
      SET r += e.properties RETURN 1 AS n
    UNION
      WITH a, b, e
      WHERE e.rel_type = 'LINTAS_BUKU_MEMPERDALAM'
      MERGE (a)-[r:LINTAS_BUKU_MEMPERDALAM]->(b)
      SET r += e.properties RETURN 1 AS n
    UNION
      WITH a, b, e
      WHERE e.rel_type = 'LINTAS_BUKU_BERKAITAN_DENGAN'
      MERGE (a)-[r:LINTAS_BUKU_BERKAITAN_DENGAN]->(b)
      SET r += e.properties RETURN 1 AS n
    }
    RETURN sum(n) AS total
    '''
    with driver.session(database=NEO4J_DATABASE) as s:
        try:
            r = s.run(REPLAY_QUERY, edges=edges_json).single()
            print(f'APOC replay merged {r["n"]} edges')
        except Exception:
            r = s.run(SIMPLE_REPLAY, edges=edges_json).single()
            print(f'Simple replay merged {r["total"]} edges')
"""))

# ── Stage 7 — Metrics ─────────────────────────────────────────────
cells.append(md("## Stage 7 — Quick metrics on the staged output"))

cells.append(code(r"""# 7a. Type breakdown + concept coverage + confidence distribution

import statistics as st
print('=== Edge type breakdown ===')
for t, n in doc['edge_type_breakdown'].items():
    pct = 100 * n / max(doc['edge_count'], 1)
    print(f'  {t:35s} {n:>5d}  ({pct:5.1f}%)')

touched = set()
for e in edges_json:
    touched.add((e['source_name'], e['source_grade']))
    touched.add((e['target_name'], e['target_grade']))
total_c = inst.get('Concept', 0)
print(f'\nConcept coverage: {len(touched)}/{total_c} ({100*len(touched)/max(total_c,1):.1f}%)')

confs = [e['properties']['confidence'] for e in edges_json]
if confs:
    confs.sort()
    print(f'\nConfidence: min={confs[0]:.2f} median={st.median(confs):.2f} '
          f'mean={st.mean(confs):.2f} max={confs[-1]:.2f}')
    for lo, hi in [(0.95,1.01),(0.85,0.95),(0.70,0.85),(0.50,0.70),(0.0,0.50)]:
        n = sum(1 for c in confs if lo <= c < hi)
        print(f'  [{lo:.2f}, {hi:.2f}): {n}')
"""))

cells.append(code(r"""# Close driver
driver.close()
print('Done.')
"""))

# ── Assemble notebook ───────────────────────────────────────────────
nb = {
    'cells': cells,
    'metadata': {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python', 'version': '3.11'},
    },
    'nbformat': 4,
    'nbformat_minor': 5,
}

OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')
print(f'Wrote {OUT}  ({OUT.stat().st_size} bytes, {len(cells)} cells)')
