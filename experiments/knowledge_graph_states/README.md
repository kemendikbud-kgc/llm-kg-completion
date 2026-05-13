# Knowledge Graph States

This folder catalogs versioned snapshots of the thesis KG (Yhoga schema:
`Grade → Chapter → Subtopic → Concept` + `ConceptTarget`, see
`docs/yhoga-ontology.ttl`).

## Layout

```
knowledge_graph_states/
├── MANIFEST.md                          ← catalog of every state. Read this first.
├── README.md                            ← you are here
├── extraction-v<N>[-<descriptor>]/      ← ingestion-axis states (canonical pre-completion line)
│   ├── derivation.md
│   ├── *.json                            (text artifacts: extraction output / edge dumps)
│   └── snapshot.backup.ref               (pointer to the binary .backup in Drive)
└── completion-experiments/              ← branches off an ingestion state, one folder per method run
    └── <method-slug>/
        ├── derivation.md
        ├── *.json
        └── snapshot.backup.ref
```

Ingestion states are linear (v1 → v2 → …). Completion experiments are
branches — multiple experiments can share the same ingestion baseline.

## Why this exists

The thesis needs unambiguous, citable states of the KG so that
"method X was run on state Y" is reproducible from source. Binary `.backup`
files capture the live DB byte-for-byte but live outside git (too big);
JSON dumps + Cypher derivation scripts live inside git and are diffable.

## Workflow

1. Each new KG state gets a new versioned folder + a new row in `MANIFEST.md`.
2. The binary `.backup` lives in Drive; we keep a `snapshot.backup.ref`
   pointer with URL + sha256 hash + size in git.
3. The `derivation.md` documents *how* the state was produced (script,
   parameters, model, date) so it can be regenerated.
4. Wherever possible, also keep a text-form dump of what changed
   (e.g. `lintas_buku_edges.json` for a completion-step state) so diffs
   between methods don't require restoring the DB.
