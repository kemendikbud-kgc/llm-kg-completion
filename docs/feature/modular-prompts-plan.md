# Modular Prompt System for Experimental Extraction

**Goal:** Allow users to edit, save, and switch between different extraction prompts in the Streamlit UI, enabling experimentation with various extraction methods without code changes.

---

## Current State

| Component | Location | Status |
|-----------|----------|--------|
| System prompt | `src/extraction.py:20-28` | Hardcoded |
| Output schema | `src/schemas.py` | Fixed Pydantic model (`TopicExtraction`) |
| UI | `app.py` | No prompt customization |

---

## Proposed Architecture

```
data/
  prompts/
    default.json              # Simple Topic/SubTopic extraction
    sma_science_ontology.json # Rich Indonesian science curriculum
    custom_*.json             # User-created experiments

src/
  prompts.py                  # NEW: Prompt loader/manager

app.py                        # MODIFIED: Prompt selector + editor UI
```

---

## Implementation Details

### 1. Create `src/prompts.py`

Prompt configuration manager with the following interface:

```python
PROMPTS_DIR = Path("data/prompts")

def list_prompts() -> list[str]:
    """Return available prompt names."""

def load_prompt(name: str) -> dict:
    """Load prompt config: {name, description, system_prompt}."""

def save_prompt(name: str, system_prompt: str, description: str = "") -> None:
    """Save new or edited prompt config to file."""

def get_default_prompt() -> dict:
    """Return built-in fallback if no configs exist."""
```

**Config file structure:**
```json
{
  "name": "SMA Science Ontology",
  "description": "Rich Indonesian science curriculum extraction with domain concepts",
  "system_prompt": "Kamu adalah asisten ekstraksi..."
}
```

---

### 2. Create `data/prompts/default.json`

Extract current hardcoded prompt:

```json
{
  "name": "Default",
  "description": "Simple Topic/SubTopic extraction for general curriculum documents",
  "system_prompt": "You are an expert curriculum designer. I will give you a text from a science curriculum.\n\nDefinitions:\n- Topic: An abstract concept taught in a session.\n- Sub-Topic: Fine-grained content explained in detail.\n\nTask: Extract all Topics and Sub-Topics from the text below.\nOutput strictly in JSON format matching the schema."
}
```

---

### 3. Create `data/prompts/sma_science_ontology.json`

Port the rich ontology from `experiments/new-experiment.ipynb`:

```json
{
  "name": "SMA Science Ontology",
  "description": "Rich extraction with domain concepts (Energi, Materi, etc.) and inter-concept relations. Best for Indonesian SMA science textbooks.",
  "system_prompt": "Kamu adalah asisten ekstraksi pengetahuan ilmiah untuk buku teks SMA Kurikulum Merdeka Indonesia.\nTugasmu: membaca bagian teks pelajaran dan mengekstrak konsep-konsep ilmiah beserta relasinya\nsesuai ontologi yang telah didefinisikan.\n\nOntologi domain konsep yang tersedia:\n  Energi, Materi, Gaya_dan_Interaksi, Struktur, Sistem,\n  Perubahan, Kesetimbangan, Informasi_Biologis, Skala_dan_Representasi\n\nTipe relasi antar konsep yang diizinkan:\n  isRelatedTo, isPrerequisiteOf, explains, causes, appliesTo, analogousTo\n\nKembalikan HANYA satu objek JSON yang valid dengan struktur berikut:\n{\n  \"mata_pelajaran\": \"<Fisika|Kimia|Biologi>\",\n  \"bab\": \"<judul bab>\",\n  \"subbab\": \"<judul subbab>\",\n  \"konsep\": [\n    {\n      \"nama\": \"<nama konsep utama>\",\n      \"definisi\": \"<definisi singkat>\",\n      \"subkonsep\": [\"...\"]\n    }\n  ]\n}"
}
```

---

### 4. Modify `src/extraction.py`

**Changes:**

1. Import prompts module
2. Add `prompt_name` parameter to `extract_topics()`
3. Load system prompt dynamically
4. Include prompt name in cache key

```python
# Before
def extract_topics(text: str, model: str | None = None, use_cache: bool = True) -> tuple[dict, bool]:

# After
def extract_topics(
    text: str,
    model: str | None = None,
    prompt_name: str = "default",
    use_cache: bool = True
) -> tuple[dict, bool]:
    prompt = load_prompt(prompt_name)
    system_prompt = prompt["system_prompt"]
    # Use system_prompt in LLMTextCompletionProgram...

# Cache key change
def _cache_key(text: str, model: str, prompt_name: str) -> str:
    return hashlib.sha256((text + model + prompt_name).encode()).hexdigest()
```

---

### 5. Modify `app.py` - Add Prompt UI

Add new sidebar section below model selection:

```
[Model Settings]
  Chat Model: [dropdown]
  Embedding Model: [dropdown]

[Extraction Method]          <-- NEW SECTION
  Prompt: [Default ▼]
  
  [Edit Prompt] expander:
    Name: [text input]
    Description: [text area]
    System Prompt: [large text area]
    [Save as New] [Reset]
```

**Implementation sketch:**

```python
with st.sidebar:
    st.divider()
    st.header("Extraction Method")
    
    prompt_names = list_prompts()
    selected_prompt = st.selectbox("Prompt", options=prompt_names)
    
    with st.expander("Edit Prompt"):
        prompt_config = load_prompt(selected_prompt)
        edited_prompt = st.text_area(
            "System Prompt",
            value=prompt_config["system_prompt"],
            height=300
        )
        new_name = st.text_input("Save as (name)")
        if st.button("Save"):
            save_prompt(new_name or selected_prompt, edited_prompt)
            st.success(f"Saved as {new_name or selected_prompt}")
```

Update extraction call:

```python
result, from_cache = extract_topics(
    raw_text,
    model=selected_chat_model,
    prompt_name=selected_prompt,
    use_cache=use_cache
)
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Schema handling | Fixed Pydantic schema | Guarantees compatibility with Neo4j graph structure |
| Storage | File system (`data/prompts/`) | Version-controllable, persistent, shareable |
| Cache invalidation | Include prompt in hash | Different prompts shouldn't share cache |
| Notebook ontology | Include as built-in preset | Useful for Indonesian SMA science experiments |

---

## File Summary

| File | Action | Est. Lines |
|------|--------|------------|
| `src/prompts.py` | Create | ~50 |
| `data/prompts/default.json` | Create | ~10 |
| `data/prompts/sma_science_ontology.json` | Create | ~40 |
| `src/extraction.py` | Modify | +15 |
| `app.py` | Modify | +50 |

**Total: ~165 new/modified lines**

---

## Future Enhancements (Out of Scope)

- Dynamic schema support (allow custom Pydantic models per prompt)
- Prompt versioning/diffing
- Import/export prompt configs
- Prompt testing/benchmarking UI
