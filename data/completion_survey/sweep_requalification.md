# Sweep Re-Qualification (cache-based, no API key)

Recomputed cosine + top_k rank for 117 surveyed cross-book edges from 342 cached embedding vectors (model `gemini/gemini-embedding-001`). No API calls, no Neo4j mutation.

## Survivors and survey-joined quality per config

| Config | Survivors | Rated | Validity | Type | Direction |
|---|--:|--:|--:|--:|--:|
| 0.85 / k5 | 14 | 12 | 100% | 100% | 83% |
| 0.80 / k10 | 42 | 34 | 100% | 100% | 71% |
| 0.75 / k15 | 72 | 62 | 100% | 100% | 74% |
| 0.70 / k20 | 101 | 87 | 100% | 100% | 74% |

> 11 surveyed edge(s) involve a concept missing from the embedding cache (description changed since embedding) and are excluded from survival: LB005, LB008, LB017, LB028, LB046, LB074, LB085, LB095, LB098, LB105, LB107

> 8 of 350 graph concepts lack a cached vector (re-embed needed for a full run): Stoikiometri Larutan, Perbandingan Sel Volta dan Sel Elektrolisis, Mobil Listrik, Pemanfaatan Inframerah, Gerak Relatif Newton, Dilatasi Waktu, Penambahan Kecepatan Relativistik, Pengerutan Panjang
