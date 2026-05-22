"""Extract LLM/embedding/chunking parameters from Yhoga's notebooks."""
import json, os, re, sys

NB_DIR = os.path.join(os.path.dirname(__file__), 'yhoga', 'TA_KG')
nbs = ['TA_KG.ipynb', 'TA_KG_INTERKONEKSI-v1.ipynb', 'TA_KG_COMPLETION-v2.ipynb']

# Patterns to scan for
PATTERNS = [
    ('model_id',        r'(?:model[_ ]name|model_id|model\s*=)[\s:=]+["\']([\w\-/.\d:]+)["\']'),
    ('temperature',     r'temperature\s*[=:]\s*([\d.]+)'),
    ('top_p',           r'top_p\s*[=:]\s*([\d.]+)'),
    ('top_k',           r'(?<!_)top_k\s*[=:]\s*([\d]+)'),
    ('max_tokens',      r'(?:max_(?:output_)?tokens|maxOutputTokens)\s*[=:]\s*([\d]+)'),
    ('candidate_count', r'candidate_count\s*[=:]\s*([\d]+)'),
    ('chunk_size',      r'chunk_size\s*[=:]\s*([\d]+)'),
    ('chunk_overlap',   r'chunk_overlap\s*[=:]\s*([\d]+)'),
    ('embed_model',     r'(?:embed(?:ding)?_?model)[\s=:]+["\']([\w\-/.\d:]+)["\']'),
    ('output_dim',      r'output_dim(?:ensionality)?\s*[=:]\s*([\d]+)'),
    ('embed_task_type', r'task_type\s*[=:]\s*["\']([\w_]+)["\']'),
    ('batch_size',      r'batch_size\s*[=:]\s*([\d]+)'),
    ('seed',            r'(?<!\w)seed\s*[=:]\s*([\d]+)'),
    ('response_mime',   r'response_mime_type\s*[=:]\s*["\']([^"\']+)["\']'),
    ('safety',          r'safety_settings'),
    ('threshold',       r'(?:similarity_)?threshold\s*[=:]\s*([\d.]+)'),
    ('cosine',          r'cosine'),
    ('GenerationConfig',r'GenerationConfig\s*\('),
    ('genai_Client',    r'genai\.Client\('),
    ('pydantic',        r'(?:BaseModel|response_schema|response_model)'),
    ('cache',           r'(?:cache|sha256|hashlib)'),
]

def gather_source(path):
    nb = json.load(open(path, encoding='utf-8'))
    src = []
    for i, cell in enumerate(nb.get('cells', [])):
        if cell.get('cell_type') == 'code':
            text = ''.join(cell.get('source', []))
            src.append((i, text))
    return src

def scan(label, source_cells):
    hits = {p[0]: set() for p in PATTERNS}
    for idx, code in source_cells:
        for name, pat in PATTERNS:
            for m in re.finditer(pat, code, re.IGNORECASE):
                if m.groups():
                    hits[name].add(m.group(1))
                else:
                    hits[name].add('<present>')
    print(f'\n=== {label} ===')
    for name, _ in PATTERNS:
        if hits[name]:
            v = sorted(hits[name])
            print(f'  {name:18}: {v}')

for fn in nbs:
    p = os.path.join(NB_DIR, fn)
    if not os.path.exists(p):
        print(f'(missing) {fn}'); continue
    src = gather_source(p)
    print(f'\n>>> {fn}: {len(src)} code cells')
    scan(fn, src)
