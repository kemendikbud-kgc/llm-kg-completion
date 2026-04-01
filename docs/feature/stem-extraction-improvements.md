# STEM Extraction Improvements Plan

Enrich the Knowledge Graph for Physics and Chemistry textbooks by capturing structured formulas, variables, processes, and cross-subject connections that the current pipeline loses.

## Context

The current pipeline extracts Konsep/SubKonsep with text descriptions, which works well for Biology (text-heavy) but produces sparse KGs for Physics and Chemistry. The core problem: **formulas, variables, units, and multi-step processes are buried in description strings** with no structured representation, making them unqueryable and invisible to the similarity/completion engine.

## Improvements

### 1. Schema: Add `formula` and `variables` Fields

**Files:** `src/schemas.py`

**Why:** Formulas are the connective tissue between Physics/Chemistry concepts. Without structured formula data, the KG can't express that "Hukum Newton II" and "Gaya Gesek" share variable `F`, or that `PV = nRT` links Tekanan, Volume, Suhu, and Mol.

**Changes:**

```python
class SubKonsep(BaseModel):
    name: str
    description: str
    formula: list[str] = []       # e.g., ["F = ma", "a = F/m"]
    variables: list[str] = []     # e.g., ["F (gaya, N)", "m (massa, kg)"]

class Konsep(BaseModel):
    name: str
    description: str
    sub_konsep: list[SubKonsep] = []
    formula: list[str] = []
    variables: list[str] = []

class KonsepWithRelations(BaseModel):
    name: str
    description: str
    relations: list[KonsepRelation] = []
    formula: list[str] = []
    variables: list[str] = []
```

**Graph impact:** New `(:Variable {name, unit})` nodes with `USES_VARIABLE` edges from Konsep/SubKonsep. Enables queries like "find all concepts involving variable F" and cross-chapter edges through shared variables.

### 2. Prompts: Explicit Formula & Variable Extraction Instructions

**Files:** `src/prompts.py`

**Why:** The LLM won't reliably extract formulas unless explicitly instructed. Current prompts say "extract concepts" but never mention formulas, variables, or units.

**Changes to all prompts (default, strict, cot, toc_bab):**

Add a section after DEFINISI ONTOLOGI:

```
## RUMUS DAN VARIABEL (Fisika/Kimia)

Untuk mata pelajaran Fisika dan Kimia:
1. Ekstrak rumus/persamaan penting sebagai field "formula" (notasi teks, misal: "F = m × a")
2. Daftar variabel yang terlibat sebagai field "variables" dengan format: "simbol (nama, satuan)"
   Contoh: ["F (gaya, N)", "m (massa, kg)", "a (percepatan, m/s²)"]
3. Jika konsep memiliki rumus turunan, sertakan semua bentuk (misal: "v = s/t", "s = v × t")
```

Update the JSON output format examples to include `formula` and `variables` fields.

### 3. Prompts: Extract Worked Example Applications

**Files:** `src/prompts.py`

**Why:** Contoh Soal sections show which concepts combine in practice — rich relationship data currently discarded by the filter. We don't need the full problem, just the application pattern.

**Changes:**

Replace the blanket "Abaikan instruksi soal, pertanyaan latihan" with:

```
## CONTOH SOAL

- Abaikan teks soal dan jawaban secara detail
- TETAPI ekstrak pola penerapan konsep: konsep apa yang digunakan bersama?
- Contoh: jika soal menggunakan Hukum Newton II dan Gaya Gesek pada bidang miring,
  tambahkan relasi BERINTERAKSI_DENGAN antara kedua konsep tersebut
```

### 4. Schema: Add Process/Mechanism Support

**Files:** `src/schemas.py`, `src/prompts.py`

**Why:** Chemistry has reaction mechanisms, titration steps, equilibrium shifts. Biology has metabolic pathways. These are ordered sequences that connect concepts, not captured by flat Konsep/SubKonsep.

**Changes to `src/schemas.py`:**

Map process/reaction variants to existing canonical types (no new relation types needed):

```python
# In RELATION_TYPE_MAPPING:
"TAHAP_DARI": "BAGIAN_DARI",
"LANGKAH_DALAM": "BAGIAN_DARI",
"MENGHASILKAN": "MENYEBABKAN",
"MENGHASILKAN_PRODUK": "MENYEBABKAN",
```

**Prompt addition:**

```
## PROSES DAN MEKANISME (Kimia/Biologi)

Untuk proses bertahap (mekanisme reaksi, jalur metabolisme, prosedur titrasi):
- Gunakan relasi LANGKAH_DALAM untuk menghubungkan langkah ke proses induk
- Gunakan relasi MENYEBABKAN antar langkah berurutan
- Contoh: "Ionisasi" LANGKAH_DALAM "Reaksi Asam-Basa"
```

### 5. Schema: Add Conditions/Constraints

**Files:** `src/schemas.py`

**Why:** Physics and Chemistry concepts have applicability conditions ("berlaku pada suhu konstan", "hanya untuk gas ideal"). These conditions connect concepts (Boyle's Law ↔ constant temperature ↔ Thermodynamics).

**Changes:**

```python
class Konsep(BaseModel):
    name: str
    description: str
    sub_konsep: list[SubKonsep] = []
    formula: list[str] = []
    variables: list[str] = []
    kondisi: list[str] = []  # e.g., ["suhu konstan", "gas ideal"]
```

**Prompt addition:**

```
## KONDISI BERLAKU

Jika konsep hanya berlaku dalam kondisi tertentu, catat dalam field "kondisi".
Contoh: ["suhu konstan", "gas ideal", "tanpa gesekan"]
```

### 6. Graph: Variable Nodes and Cross-Concept Edges

**Files:** `src/graph.py`

**Why:** With formula/variable data in the schema, we need to create graph structures that make them queryable.

**Changes:**

Add `insert_variables()` function:

```python
def insert_variables(tx, konsep_name: str, variables: list[str]):
    """Create Variable nodes and USES_VARIABLE edges."""
    for var_str in variables:
        # Parse "F (gaya, N)" → name="F", label="gaya", unit="N"
        # MERGE Variable node, CREATE edge to Konsep
```

After inserting all konsep, run a post-processing step:

```python
def create_shared_variable_edges(tx):
    """Create SHARES_VARIABLE edges between Konsep that use the same variable."""
    # MATCH (a:Konsep)-[:USES_VARIABLE]->(v:Variable)<-[:USES_VARIABLE]-(b:Konsep)
    # WHERE a <> b
    # MERGE (a)-[:SHARES_VARIABLE {variable: v.name}]->(b)
```

### 7. Completion: Include Formulas in Embeddings

**Files:** `src/completion.py`

**Why:** Currently only konsep name + description are embedded. Adding formulas and variables to the embedding text will improve similarity discovery for Physics concepts that share mathematical structure.

**Changes:**

When building the text to embed, concatenate:

```python
embed_text = f"{konsep.name}: {konsep.description}"
if konsep.formula:
    embed_text += f" Rumus: {', '.join(konsep.formula)}"
if konsep.variables:
    embed_text += f" Variabel: {', '.join(konsep.variables)}"
```

## Implementation Order

1. **Schema changes** (`schemas.py`) — add fields, new relation types
2. **Prompt updates** (`prompts.py`) — formula/variable instructions, worked examples, processes
3. **Graph updates** (`graph.py`) — Variable nodes, shared-variable edges
4. **Completion updates** (`completion.py`) — enriched embedding text
5. **App UI** (`app.py`) — display formula/variable data in results

## Verification

1. Run extraction on a Physics textbook chapter (e.g., Hukum Newton) — verify `formula` and `variables` fields are populated
2. Check Neo4j for Variable nodes and USES_VARIABLE/SHARES_VARIABLE edges
3. Compare KG node/edge counts before and after for a Physics book — expect significant increase
4. Run similarity discovery — verify Physics concepts now cluster better via shared formulas
5. Test backward compatibility — old cache files (without formula fields) should still load (Pydantic defaults handle this)

## Cache Compatibility

Adding optional fields with defaults (`formula: list[str] = []`) is backward-compatible with existing cache JSON. Old cache entries missing these fields will deserialize with empty lists. No cache migration needed, but prompt version should be bumped (v4 for default, v5 for toc_bab) so new extractions use the updated prompts.
