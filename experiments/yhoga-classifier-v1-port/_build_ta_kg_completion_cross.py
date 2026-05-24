"""Generator for TA_KG_COMPLETION_cross.ipynb — refocused cross-book completion.

A revised version of Yhoga's TA_KG_COMPLETION.ipynb (intra-book orphan completion)
that:
  - Targets cross-book completion only (LINTAS_BUKU_* vocab, no intra-book mode)
  - Adds KONTEKS GRAF block to the classifier prompt
  - Uses bidirectional ANN candidate retrieval (fixes direction-asymmetry bias)
  - Type-aware confidence thresholds (calibrated to per-type confidence signature)
  - Post-run analysis cells (confidence-by-type, direction distribution, bridge concepts)

Keeps his good design: explicit `direction` enum, cycle check on hierarchical
types, retry logic, evidence_quote, audit log, style.

Run: `python _build_ta_kg_completion_cross.py` to (re)generate the .ipynb.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
OUT  = HERE / "TA_KG_COMPLETION_cross.ipynb"

def md(src: str): return {'cell_type':'markdown','metadata':{},'source':src.splitlines(True)}
def code(src: str): return {'cell_type':'code','metadata':{},'source':src.splitlines(True),
                            'execution_count':None,'outputs':[]}

cells = []

# ── Title ───────────────────────────────────────────────────────────
cells.append(md(r"""# 🧩 KG Completion — Cross-Book Edition (Pass-1, LINTAS_BUKU_*)

Refokus dari `TA_KG_COMPLETION.ipynb` (intra-book orphan completion) ke **cross-book completion** menggunakan vokabulari tertutup `LINTAS_BUKU_*` sesuai ontologi proyek.

**Perubahan metodologis vs versi sebelumnya:**

1. **Vokabulari `LINTAS_BUKU_*`** (5 tipe) menggantikan vokabulari intra-buku — tipe relasi yang konsisten dengan scope pasangan (cross-book).
2. **Blok `KONTEKS GRAF`** ditambahkan ke prompt classifier — LLM melihat existing typed edges + parent subtopic + shared neighbors tiap konsep, bukan hanya nama + deskripsi.
3. **Bidirectional ANN candidate retrieval** — pasangan disurfacekan jika muncul di top-k salah satu *atau* kedua endpoint (memperbaiki bias arah dari per-anchor top-k).
4. **Type-aware confidence thresholds** — `BERKAITAN_DENGAN` (catch-all) ber-threshold lebih ketat dibanding tipe struktural; cocok dengan signature confidence-per-type yang ditemukan empiris.
5. **Post-run analyses** — signature confidence-by-type, distribusi arah PRASYARAT_UNTUK, dan deteksi *bridge concepts*.

**5 LINTAS_BUKU_* relation types:**
1. `LINTAS_BUKU_SAMA_DENGAN` (sym) — entitas yang sama dijelaskan di buku berbeda
2. `LINTAS_BUKU_APLIKASI_DARI` (asym) — A adalah penerapan B di disiplin lain
3. `LINTAS_BUKU_PRASYARAT_UNTUK` (asym, hierarkis, cycle-checked)
4. `LINTAS_BUKU_MEMPERDALAM` (asym) — A memperdalam pemahaman B di buku lain
5. `LINTAS_BUKU_BERKAITAN_DENGAN` (sym, fallback)
"""))

# ── Cell 1: config markdown ─────────────────────────────────────────
cells.append(md("## ⚙️ Konfigurasi\n\nEdit cell ini untuk tuning."))

# ── Cell 2: config code ─────────────────────────────────────────────
cells.append(code(r"""from pathlib import Path

PROJECT_DIR = Path('/Users/fadrianyhoga/Documents/Skripsi')
OUTPUTS_DIR = PROJECT_DIR / 'outputs'

INPUT_FILES = {
    'Biologi Kelas XII': OUTPUTS_DIR / 'Biologi Kelas XII_20260427_222657_expert_boosted.json',
    'Fisika Kelas XII':  OUTPUTS_DIR / 'Fisika Kelas XII_20260427_222657_expert_boosted.json',
    'Kimia Kelas XII':   OUTPUTS_DIR / 'Kimia Kelas XII_20260427_222657_expert_boosted.json',
}

# ── tuning ────────────────────────────────────────────────────────────
EMBEDDING_MODEL = 'paraphrase-multilingual-mpnet-base-v2'
LLM_MODEL       = 'gemini-2.5-flash'
GEMINI_API_KEY  = ''   # paste your key

COS_THRESHOLD   = 0.75   # cosine cutoff utk kandidat partner
TOP_K           = 15     # top-k per concept (bidirectional union)

# ── type-aware confidence thresholds ─────────────────────────────────
# Empiris: BERKAITAN_DENGAN cluster mean conf ~0.61 (uncertainty bucket).
# Tipe struktural cluster mean conf ~0.9. Threshold lebih ketat untuk catch-all.
CONF_THRESHOLD_BY_TYPE = {
    'LINTAS_BUKU_BERKAITAN_DENGAN': 0.85,   # catch-all, strict
    'default':                       0.7,    # tipe struktural
}

ALLOWED_TYPES = [
    'LINTAS_BUKU_SAMA_DENGAN',          # sym, identity
    'LINTAS_BUKU_APLIKASI_DARI',        # asym, specialization
    'LINTAS_BUKU_PRASYARAT_UNTUK',      # asym, pedagogical, hierarchical
    'LINTAS_BUKU_MEMPERDALAM',          # asym, depth-extension
    'LINTAS_BUKU_BERKAITAN_DENGAN',     # sym, fallback
]
SYMMETRIC    = {'LINTAS_BUKU_SAMA_DENGAN', 'LINTAS_BUKU_BERKAITAN_DENGAN'}
ASYMMETRIC   = {'LINTAS_BUKU_APLIKASI_DARI', 'LINTAS_BUKU_PRASYARAT_UNTUK', 'LINTAS_BUKU_MEMPERDALAM'}
HIERARCHICAL = {'LINTAS_BUKU_PRASYARAT_UNTUK'}  # cycle-checked

# Cap out-edges per concept dalam blok KONTEKS GRAF (membatasi ukuran prompt)
NEIGHBORHOOD_MAX_EDGES = 5

print(f'COS_THRESHOLD = {COS_THRESHOLD} | TOP_K = {TOP_K}')
print(f'CONF thresholds: {CONF_THRESHOLD_BY_TYPE}')
print(f'Embedding: {EMBEDDING_MODEL}')
print(f'LLM      : {LLM_MODEL}')
"""))

# ── Cell 3: helpers markdown ─────────────────────────────────────────
cells.append(md("## 🔧 Helpers + Definitions"))

cells.append(code(r"""import json, re, time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import numpy as np

# ── definitions used in the classifier prompt ────────────────────────
TYPE_DEFINITIONS = '''
1. LINTAS_BUKU_SAMA_DENGAN     — A dan B merujuk pada entitas/konsep yang sama,
                                 meski dibahas di buku berbeda. Simetris.
                                 Contoh: "Energi" (Fisika) <-> "Energi" (Kimia).
2. LINTAS_BUKU_APLIKASI_DARI   — A adalah penerapan/manifestasi konsep B di
                                 disiplin lain. Asimetris (arah dari aplikasi ke prinsip).
                                 Contoh: "Difusi" (Biologi) <- "Gerak Brown" (Fisika).
3. LINTAS_BUKU_PRASYARAT_UNTUK — A pada satu mata pelajaran adalah prasyarat
                                 untuk memahami B pada mata pelajaran lain.
                                 Asimetris (arah dari prasyarat ke konsep berikutnya).
                                 Contoh: "Stoikiometri" (Kimia) -> "Termokimia" (Fisika lintas).
4. LINTAS_BUKU_MEMPERDALAM     — A memperdalam/memperluas pemahaman konsep B
                                 di buku lain. Asimetris.
                                 Contoh: "Termodinamika" (Fisika) -> "Reaksi Endoterm" (Kimia).
5. LINTAS_BUKU_BERKAITAN_DENGAN — Berkaitan secara umum lintas-buku (fallback).
                                  Simetris. Pilih ini jika empat tipe di atas tidak tepat.
'''

def normalize_name(s):
    return re.sub(r'\s+', ' ', (s or '').strip().lower())

def conf_threshold_for(rel_type):
    return CONF_THRESHOLD_BY_TYPE.get(rel_type, CONF_THRESHOLD_BY_TYPE['default'])
"""))

# ── Cell 4: load books markdown ─────────────────────────────────────
cells.append(md("## 1️⃣ Load Books & Build Concept Registry"))

cells.append(code(r"""@dataclass
class ConceptRef:
    book: str
    chapter: str
    subtopic: str
    name: str
    description: str
    # Existing typed relations (untuk KONTEKS GRAF block — bukan untuk filter)
    out_edges: list = field(default_factory=list)   # list of (rel_type, target_name) dalam buku yang sama
    cross_out: list = field(default_factory=list)   # list of (rel_type, target_book, target_name)

    @property
    def key(self):
        return (self.book, normalize_name(self.name))

    @property
    def text_for_embedding(self):
        return f'{self.name}: {self.description}'


def load_books():
    books = {n: json.load(open(p, encoding='utf-8')) for n, p in INPUT_FILES.items()}
    concepts = {}

    # Pass 1: register concepts
    for book_name, data in books.items():
        for ch in data['chapters']:
            for sub in ch.get('subtopics', []):
                for c in sub.get('concepts', []):
                    key = (book_name, normalize_name(c['name']))
                    concepts[key] = ConceptRef(
                        book=book_name, chapter=ch['chapter'], subtopic=sub['name'],
                        name=c['name'], description=c.get('description', ''),
                    )

    # Pass 2: harvest existing typed edges (for KONTEKS GRAF, excluding filler)
    for book_name, data in books.items():
        for ch in data['chapters']:
            for sub in ch.get('subtopics', []):
                for c in sub.get('concepts', []):
                    src_key = (book_name, normalize_name(c['name']))
                    if src_key not in concepts: continue
                    src = concepts[src_key]
                    for r in c.get('relations', []):
                        # Exclude filler (auto-pad ADC) dari konteks
                        if r.get('expert_validation_added', False):
                            continue
                        rt = r.get('type', '')
                        tgt = r.get('target', '')
                        if rt and tgt:
                            src.out_edges.append((rt, tgt))
                    for r in c.get('cross_book_links', []):
                        rt = r.get('relation_type', '')
                        tb = r.get('target_book', '')
                        tn = r.get('target_concept', '')
                        if rt and tb and tn:
                            src.cross_out.append((rt, tb, tn))
    return books, list(concepts.values())


books, concepts = load_books()
print(f'Total concepts: {len(concepts)} across {len(books)} books')
print(f'  by book: {dict((b, sum(1 for c in concepts if c.book == b)) for b in books)}')
"""))

# ── Cell 5: embedding markdown ───────────────────────────────────────
cells.append(md("## 2️⃣ Build Embeddings"))

cells.append(code(r"""from sentence_transformers import SentenceTransformer

print(f'Loading {EMBEDDING_MODEL} ...')
embedder = SentenceTransformer(EMBEDDING_MODEL)
texts = [c.text_for_embedding for c in concepts]
print(f'Encoding {len(texts)} concept texts ...')
embeddings = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=True, batch_size=32)
embeddings = np.asarray(embeddings, dtype=np.float32)
print(f'Embeddings shape: {embeddings.shape}')
"""))

# ── Cell 6: ANN markdown ─────────────────────────────────────────────
cells.append(md(r"""## 3️⃣ Bidirectional Cross-Book Candidate Retrieval

**Methodology:** untuk tiap pasangan (A, B) lintas-buku dengan score cosine `>= COS_THRESHOLD`, pasangan disurfacekan jika A muncul di top-k dari B **atau** B muncul di top-k dari A. Versi sebelumnya hanya query dari satu anchor sehingga rentan terhadap directional asymmetry pada ANN.
"""))

cells.append(code(r"""def find_cross_grade_candidates_bidirectional(all_concepts, embs, top_k=TOP_K, threshold=COS_THRESHOLD):
    '''Return list of (concept_a, concept_b, score) tuples.

    Pair (A, B) lolos jika:
      - source.book != target.book
      - score >= threshold
      - A in B's top-k OR B in A's top-k
    '''
    n = len(all_concepts)
    seen = set()
    pairs = []
    for i, a in enumerate(all_concepts):
        sims = embs @ embs[i]
        sims[i] = -1.0
        # Top-k candidates above threshold
        order = np.argsort(-sims)
        for j in order[: top_k * 4]:
            score = float(sims[j])
            if score < threshold:
                break
            b = all_concepts[j]
            if b.book == a.book:
                continue   # cross-grade only
            key = tuple(sorted([(a.book, a.name), (b.book, b.name)]))
            if key in seen:
                continue
            seen.add(key)
            # Order: lexically first endpoint as A (deterministic; LLM picks direction)
            (ab, an), (bb, bn) = key
            ca = next(c for c in all_concepts if c.book == ab and c.name == an)
            cb = next(c for c in all_concepts if c.book == bb and c.name == bn)
            pairs.append((ca, cb, score))
            if sum(1 for p in pairs if p[0].key == a.key or p[1].key == a.key) >= top_k:
                break
    return pairs


pairs = find_cross_grade_candidates_bidirectional(concepts, embeddings)
print(f'Cross-grade candidate pairs (bidirectional union): {len(pairs)}')

# Distribution by subject pair
from collections import Counter
def short(g): return g.replace(' Kelas XII', '')
pair_dist = Counter(' <-> '.join(sorted([short(a.book), short(b.book)])) for a, b, _ in pairs)
print(f'  by subject pair: {dict(pair_dist)}')

# Sample
print('\nSample candidates:')
for a, b, s in pairs[:8]:
    print(f'  cos={s:.3f}  [{short(a.book)}] {a.name}  <->  [{short(b.book)}] {b.name}')
"""))

# ── Cell 7: KONTEKS GRAF markdown ────────────────────────────────────
cells.append(md(r"""## 4️⃣ KONTEKS GRAF — Graph Context Block

**Methodology:** LLM classifier menerima konteks graf eksplisit untuk tiap konsep:
- Parent subtopic (lokasi konseptual)
- Existing typed out-edges (bukti relasi yang sudah ada — non-filler)
- Shared neighbors (target yang dirujuk oleh kedua konsep)

Tanpa blok ini, LLM hanya melihat pasangan dalam isolasi (nama + deskripsi + similarity). Dengan blok ini, LLM dapat menggunakan struktur graf yang sudah ada sebagai bukti tambahan untuk klasifikasi.
"""))

cells.append(code(r"""LB_VOCAB_ADVICE = (
    "Gunakan konteks graf ini sebagai bukti tambahan. Tetangga bersama "
    "menandakan A dan B kemungkinan LINTAS_BUKU_BERKAITAN_DENGAN atau "
    "LINTAS_BUKU_SAMA_DENGAN. Jika hubungan yang sudah ada di graf "
    "menunjukkan A merupakan kasus khusus dari konsep yang lebih umum di "
    "buku lain, pertimbangkan LINTAS_BUKU_APLIKASI_DARI. Jika tipe lain "
    "tidak tepat, gunakan LINTAS_BUKU_BERKAITAN_DENGAN sebagai fallback.\n"
)


def format_out_edges(edges, max_n=NEIGHBORHOOD_MAX_EDGES):
    if not edges:
        return '  (tidak ada)'
    lines = []
    for rt, tgt in edges[:max_n]:
        lines.append(f'  - {rt} -> "{tgt}"')
    if len(edges) > max_n:
        lines.append(f'  ... +{len(edges) - max_n} edge lain')
    return '\n'.join(lines)


def shared_neighbors(a: ConceptRef, b: ConceptRef):
    '''Concepts that both A and B point to via a typed edge (intra-book or cross).'''
    ta = {tgt for _, tgt in a.out_edges} | {f'{tb}::{tn}' for _, tb, tn in a.cross_out}
    tb_set = {tgt for _, tgt in b.out_edges} | {f'{tb}::{tn}' for _, tb, tn in b.cross_out}
    return sorted(ta & tb_set)


def build_konteks_graf(a: ConceptRef, b: ConceptRef):
    '''Render the KONTEKS GRAF prompt section. Empty string jika tidak ada signal.'''
    a_edges = list(a.out_edges) + [(rt, f'{tb}::{tn}') for rt, tb, tn in a.cross_out]
    b_edges = list(b.out_edges) + [(rt, f'{tb}::{tn}') for rt, tb, tn in b.cross_out]
    shared = shared_neighbors(a, b)
    if not (a.subtopic or b.subtopic or a_edges or b_edges or shared):
        return ''
    return (
        "========================\n"
        "KONTEKS GRAF (HUBUNGAN YANG SUDAH ADA)\n"
        "========================\n"
        f'Konsep A ("{a.name}") berada di Subtopic: {a.subtopic or "(tidak diketahui)"}\n'
        f"Hubungan A yang sudah ada di graf:\n{format_out_edges(a_edges)}\n\n"
        f'Konsep B ("{b.name}") berada di Subtopic: {b.subtopic or "(tidak diketahui)"}\n'
        f"Hubungan B yang sudah ada di graf:\n{format_out_edges(b_edges)}\n\n"
        f"Tetangga bersama (target yang sama-sama dirujuk A dan B): "
        f"{', '.join(shared) if shared else '(tidak ada)'}\n\n"
        f"{LB_VOCAB_ADVICE}"
    )
"""))

# ── Cell 8: classifier markdown ──────────────────────────────────────
cells.append(md("## 5️⃣ LLM Relation Typing (Gemini, strict JSON enum + KONTEKS GRAF)"))

cells.append(code(r"""from google import genai
from google.genai import types as gtypes
import random

client = genai.Client(api_key=GEMINI_API_KEY)

LLM_SYSTEM_PROMPT = f'''Anda adalah ahli kurikulum sains SMA yang menentukan jenis
keterkaitan lintas-buku antara dua konsep dari Mata Pelajaran yang berbeda
(Biologi/Fisika/Kimia Kelas XII pada Kurikulum Merdeka).

Pilih SATU dari 6 nilai untuk relation_type (5 tipe LINTAS_BUKU_* valid + NONE
jika tidak ada keterkaitan kurikuler yang masuk akal).

DEFINISI 5 TIPE RELASI YANG DIIZINKAN:
{TYPE_DEFINITIONS}

ATURAN PENTING:
- Hanya klasifikasikan sebagai LINTAS_BUKU_* jika Mata Pelajaran A != Mata Pelajaran B.
  Jika sama, kembalikan NONE.
- Pilih NONE jika tidak ada relasi yang jelas atau evidence terlalu lemah.
- Untuk tipe asimetris (APLIKASI_DARI, PRASYARAT_UNTUK, MEMPERDALAM), tentukan direction:
  A_TO_B = relasi dari konsep A ke konsep B
  B_TO_A = relasi dari konsep B ke konsep A
- SAMA_DENGAN dan BERKAITAN_DENGAN selalu SYMMETRIC.
- evidence_quote: kutip dari deskripsi konsep yang diberikan (bukan dari blok KONTEKS GRAF).
- confidence: 0.0-1.0, gunakan 0.85+ hanya jika sangat yakin.
'''

RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'relation_type':  {'type': 'string', 'enum': ALLOWED_TYPES + ['NONE']},
        'direction':      {'type': 'string', 'enum': ['A_TO_B', 'B_TO_A', 'SYMMETRIC']},
        'confidence':     {'type': 'number'},
        'evidence_quote': {'type': 'string'},
        'rationale':      {'type': 'string'},
    },
    'required': ['relation_type', 'direction', 'confidence', 'evidence_quote', 'rationale'],
}

# ── retry config (handle 503 / 429 / dll) ────────────────────────────
RETRY_MAX_ATTEMPTS = 10
RETRY_BASE_DELAY   = 3.0
RETRY_MAX_DELAY    = 60.0
RETRYABLE_KEYWORDS = ('UNAVAILABLE', 'RESOURCE_EXHAUSTED', 'INTERNAL',
                       'DEADLINE_EXCEEDED', 'overloaded', '503', '429',
                       '500', '502', '504')


def _is_retryable(exc):
    msg = str(exc)
    return any(kw in msg for kw in RETRYABLE_KEYWORDS)


def predict_relation(a: ConceptRef, b: ConceptRef, similarity: float):
    konteks = build_konteks_graf(a, b)
    user_prompt = f'''Tentukan jenis relasi LINTAS_BUKU antara dua konsep berikut.

KONSEP A:
  Buku    : {a.book}
  Bab     : {a.chapter}
  Subtopic: {a.subtopic}
  Nama    : {a.name}
  Deskripsi: {a.description}

KONSEP B:
  Buku    : {b.book}
  Bab     : {b.chapter}
  Subtopic: {b.subtopic}
  Nama    : {b.name}
  Deskripsi: {b.description}

Embedding similarity: {similarity:.3f}

{konteks}
Output JSON sesuai schema.'''
    last_err = None
    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            resp = client.models.generate_content(
                model=LLM_MODEL,
                contents=user_prompt,
                config=gtypes.GenerateContentConfig(
                    system_instruction=LLM_SYSTEM_PROMPT,
                    response_mime_type='application/json',
                    response_schema=RESPONSE_SCHEMA,
                    temperature=0.2,
                ),
            )
            return json.loads(resp.text)
        except Exception as e:
            last_err = e
            if attempt == RETRY_MAX_ATTEMPTS - 1 or not _is_retryable(e):
                break
            delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
            delay += random.uniform(0, delay * 0.25)
            print(f'  [retry {attempt+1}/{RETRY_MAX_ATTEMPTS-1}] {a.name} <-> {b.name} -> wait {delay:.1f}s ({type(e).__name__})')
            time.sleep(delay)
    print(f'  [llm-error] {a.name} <-> {b.name}: {last_err}')
    return None
"""))

# ── Cell 9: validation markdown ──────────────────────────────────────
cells.append(md(r"""## 6️⃣ Validation Helpers (type-aware confidence + cycle check)

**Methodology:** confidence threshold dipisah per relation_type. `BERKAITAN_DENGAN` (catch-all) mendapat threshold lebih ketat (0.85) karena empiris cluster mean conf-nya rendah (~0.6); tipe struktural seperti `PRASYARAT_UNTUK` cukup 0.7 karena mean conf-nya ~0.9.
"""))

cells.append(code(r"""def validate_prediction(pred):
    if not pred:
        return False, 'empty'
    rtype = pred.get('relation_type')
    if rtype == 'NONE':
        return False, 'NONE'
    if rtype not in ALLOWED_TYPES:
        return False, f'bad_type:{rtype}'
    # Type-aware confidence threshold
    conf = pred.get('confidence', 0)
    thr = conf_threshold_for(rtype)
    if conf < thr:
        return False, f'low_conf:{conf:.2f}<{thr}'
    direction = pred.get('direction')
    if rtype in ASYMMETRIC and direction == 'SYMMETRIC':
        return False, 'asym_but_symmetric'
    if rtype in SYMMETRIC and direction != 'SYMMETRIC':
        return False, 'sym_but_directional'
    return True, 'ok'


def detect_cycle(edges, src, tgt):
    '''Apakah menambahkan src -> tgt akan menutup cycle pada DAG existing?'''
    adj = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
    adj.setdefault(src, []).append(tgt)
    visited = set()
    stack = [tgt]
    while stack:
        n = stack.pop()
        if n == src:
            return True
        if n in visited:
            continue
        visited.add(n)
        stack.extend(adj.get(n, []))
    return False
"""))

# ── Cell 10: run markdown ────────────────────────────────────────────
cells.append(md(r"""## 7️⃣ Run LLM Typing on All Cross-Grade Pairs

⚠️ Setiap pasangan = 1 API call ke Gemini. Pastikan jumlah pair (lihat output cell ANN) sudah masuk akal sebelum jalan.
"""))

cells.append(code(r"""new_edges = []
rejected = []
existing_directed = []   # untuk cycle check
n_pairs = len(pairs)
t0 = time.time()

for idx, (a, b, score) in enumerate(pairs, start=1):
    pred = predict_relation(a, b, score)
    ok, why = validate_prediction(pred)
    if not ok:
        rejected.append((a.name, b.name, why))
        continue

    # Determine direction (LLM-emitted)
    if pred['direction'] == 'B_TO_A':
        src, tgt = b, a
    else:
        src, tgt = a, b

    # Cycle check for hierarchical types
    if pred['relation_type'] in HIERARCHICAL:
        src_id = f'{src.book}::{src.name}'
        tgt_id = f'{tgt.book}::{tgt.name}'
        if detect_cycle(existing_directed, src_id, tgt_id):
            rejected.append((a.name, b.name, 'would_cycle'))
            continue
        existing_directed.append((src_id, tgt_id))

    new_edges.append({
        'source_book': src.book, 'source': src.name,
        'target_book': tgt.book, 'target': tgt.name,
        'type': pred['relation_type'], 'direction': pred['direction'],
        'confidence': pred['confidence'],
        'evidence_quote': pred.get('evidence_quote', ''),
        'rationale': pred.get('rationale', ''),
        'similarity': score,
    })

    if idx % 25 == 0:
        rate = idx / max(time.time() - t0, 1e-3)
        print(f'  [{idx}/{n_pairs}] accepted={len(new_edges)} rejected={len(rejected)} ({rate:.1f}/s)')

    # Small delay
    time.sleep(1.0)

print(f'\nDONE: {len(new_edges)} edges accepted, {len(rejected)} rejected')

# Type distribution
type_counts = {}
for e in new_edges:
    type_counts[e['type']] = type_counts.get(e['type'], 0) + 1
print(f'Type distribution: {type_counts}')

# Reject reasons
from collections import Counter
print(f'Reject reasons: {dict(Counter(r[2] for r in rejected))}')
"""))

# ── Cell 11: save markdown ──────────────────────────────────────────
cells.append(md("## 8️⃣ Merge & Save (cross-book only)"))

cells.append(code(r"""# Edges land in cross_book_links[] on the source concept.
# No filler removal (cross-book pipeline doesn't manage intra-book filler).

edges_by_source = {}
for e in new_edges:
    edges_by_source.setdefault((e['source_book'], normalize_name(e['source'])), []).append(e)

for book_name, data in books.items():
    for ch in data['chapters']:
        for sub in ch.get('subtopics', []):
            for c in sub.get('concepts', []):
                key = (book_name, normalize_name(c['name']))
                for e in edges_by_source.get(key, []):
                    c.setdefault('cross_book_links', []).append({
                        'target_book': e['target_book'],
                        'target_concept': e['target'],
                        'relation_type': e['type'],
                        'direction': e['direction'],
                        'explanation': e['rationale'],
                        'evidence_quote': e['evidence_quote'],
                        'confidence': e['confidence'],
                        'completion_added': True,
                    })

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for book_name, data in books.items():
    slug = book_name.replace(' ', '_')
    path = OUTPUTS_DIR / f'{slug}_{timestamp}_completed_lintas_buku.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  saved -> {path.name}')

audit = {
    'timestamp': timestamp,
    'mode': 'cross-book LINTAS_BUKU_*',
    'config': {
        'cos_threshold': COS_THRESHOLD, 'top_k': TOP_K,
        'conf_threshold_by_type': CONF_THRESHOLD_BY_TYPE,
        'embedding_model': EMBEDDING_MODEL, 'llm_model': LLM_MODEL,
        'allowed_types': ALLOWED_TYPES,
    },
    'stats': {
        'total_concepts': len(concepts),
        'cross_grade_pairs_evaluated': n_pairs,
        'edges_accepted': len(new_edges),
        'edges_rejected': len(rejected),
        'type_distribution': type_counts,
    },
    'new_edges': new_edges,
    'rejected_sample': rejected[:50],
}
audit_path = OUTPUTS_DIR / f'completion_lintas_buku_{timestamp}_audit.json'
audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'  audit -> {audit_path.name}')
"""))

# ── Cell 12: analyses markdown ──────────────────────────────────────
cells.append(md(r"""## 9️⃣ Post-Run Analyses

Tiga properti yang berguna untuk laporan tugas akhir:
- **Confidence-by-type signature** — apakah classifier menggunakan confidence sebagai meta-sinyal?
- **Direction distribution untuk PRASYARAT_UNTUK** — apakah arah relasi konsisten dengan urutan kurikulum?
- **Bridge concepts** — konsep mana yang menjembatani 2+ mata pelajaran lain?
"""))

cells.append(code(r"""import statistics as st
from collections import defaultdict

print('='*60)
print('[1] CONFIDENCE-BY-TYPE SIGNATURE')
print('='*60)
by_type = defaultdict(list)
for e in new_edges:
    by_type[e['type']].append(e['confidence'])
for t in sorted(by_type, key=lambda k: -st.mean(by_type[k])):
    cs = by_type[t]
    print(f'  {t:35s}  n={len(cs):3d}  mean={st.mean(cs):.2f}  median={st.median(cs):.2f}  range=[{min(cs):.2f},{max(cs):.2f}]')

print()
print('='*60)
print('[2] DIRECTION DISTRIBUTION (PRASYARAT_UNTUK)')
print('='*60)
prereq = [e for e in new_edges if e['type'] == 'LINTAS_BUKU_PRASYARAT_UNTUK']
dirs = Counter(f'{short(e["source_book"])} -> {short(e["target_book"])}' for e in prereq)
print(f'  Total PRASYARAT_UNTUK edges: {len(prereq)}')
for d, n in dirs.most_common():
    pct = 100*n/max(len(prereq), 1)
    print(f'    {d:30s}  {n:3d}  ({pct:.0f}%)')

print()
print('='*60)
print('[3] BRIDGE CONCEPTS (konsep tunggal yang menyentuh 2+ buku lain)')
print('='*60)
concept_reaches = defaultdict(set)
for e in new_edges:
    src = (e['source_book'], e['source'])
    tgt = (e['target_book'], e['target'])
    concept_reaches[src].add(short(e['target_book']))
    concept_reaches[tgt].add(short(e['source_book']))
bridges = {k: v for k, v in concept_reaches.items() if len(v) > 1}
print(f'  {len(bridges)} bridge concepts (touching 2+ subjects via cross-book edges)')
for (book, name), reaches in sorted(bridges.items(), key=lambda kv: -len(kv[1]))[:10]:
    print(f'    [{short(book)}] {name!r} -> reaches {sorted(reaches)}')
"""))

# ── Cell 13: summary markdown ───────────────────────────────────────
cells.append(md("## 🔟 Quick Summary"))

cells.append(code(r"""print('='*60)
print('CROSS-BOOK COMPLETION SUMMARY (LINTAS_BUKU_*)')
print('='*60)
print(f'Total concepts          : {len(concepts)}')
print(f'Cross-grade pairs (ANN) : {n_pairs}')
print(f'Edges accepted          : {len(new_edges)}')
print(f'Edges rejected          : {len(rejected)}')
print(f'  - by type-aware conf  : {sum(1 for r in rejected if r[2].startswith("low_conf"))}')
print(f'  - by NONE             : {sum(1 for r in rejected if r[2] == "NONE")}')
print(f'  - by would_cycle      : {sum(1 for r in rejected if r[2] == "would_cycle")}')
print(f'Type distribution       : {type_counts}')
print()
unique_concepts_touched = len({(e['source_book'], e['source']) for e in new_edges} |
                              {(e['target_book'], e['target']) for e in new_edges})
print(f'Unique concepts touched : {unique_concepts_touched}/{len(concepts)} ({100*unique_concepts_touched/len(concepts):.1f}%)')
"""))

# ── assemble notebook ────────────────────────────────────────────────
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
