# Expert Feedback Data — Context Brief

> Handoff document for agents working with the expert review data collected via the **KG Review App** (kg-review-app.vercel.app). Covers the data model, where it lives, how to query it, and the key gotchas that have already cost a session of debugging.

## 1. What the data is

Domain experts (high-school Fisika/Kimia/Biologi teachers, Kelas XII) rated triples extracted from Indonesian curriculum textbooks. Each rating is one of:

| Rating | Meaning |
|---|---|
| `correct` | Relasi tepat secara konseptual |
| `partial` | Sebagian benar / butuh penajaman |
| `wrong` | Salah konseptual |
| `missing` | "Kurang konteks" — perlu asumsi/disclaimer tambahan |

Reviewers can also:
- Leave a free-text **comment** on individual triples
- Propose **missing triples** (relations they think should have been extracted but weren't)
- Write a **general feedback** paragraph

## 2. Where the data lives

Two sources — **Redis is authoritative**, JSON exports may be stale:

| Source | Path / location | Notes |
|---|---|---|
| Exported JSONs | `C:\Users\Soros\Downloads\Feedback-20260506T040248Z-3-001\Feedback\` | Snapshot pulled 2026-05-06. **Do not assume current** — reviewers can keep editing. |
| Live Redis | Upstash, `communal-horse-92107.upstash.io:6379` | Real-time state. Use `experiments/scripts/redis_check.py`. |

The kg-review-app frontend reads/writes Redis directly; the export is just a download of Redis keys at a point in time.

## 3. Filename and key conventions (gotcha!)

Reviewer accounts are named **per subject they were originally invited to**, but reviewers self-selected which course to review in the app. **The reviewer ID's subject label is NOT a reliable indicator of the course they actually reviewed.**

```
expert-<invitation_subject>-<reviewer_number>[-<course_reviewed>]
```

| Example filename | Reviewer | Course actually reviewed |
|---|---|---|
| `expert-biologi-1.json` | biologi-1 | biologi-kelas-xii (default) |
| `expert-fisika-2-kimia.json` | **fisika**-2 | **kimia**-kelas-xii ⚠️ |

Redis key format: `kg:progress:<reviewer_id>:<course_id>` where `<course_id>` is `{biologi,fisika,kimia}-kelas-xii-{numeric_suffix}`. Looking at the second segment of the Redis key is the *only* reliable way to know which course a reviewer actually rated.

## 4. Data schema per file/key

```jsonc
{
  "ratings": {
    "0": "correct",
    "1": "missing",
    // … keys are triple indices (numeric strings); not always contiguous
  },
  "comments": {
    "4": "pH didefinisikan berdasarkan aktivitas ion hidrogen…",
    "74": "pemurnian tembaga dilakukan melalui elektrorefining, bukan electroplating",
    // … sparse; only triples the reviewer commented on
  },
  "missingTriples": [
    {
      "chapter": "ELEKTROKIMIA",
      "subject": "Sel Elektrokimia",
      "relation": "Terdiri dari",
      "target": "Reaksi Setengah Sel",
      "description": ""
    }
    // … reviewer-proposed; may be empty
  ],
  "generalFeedback": "",      // optional global note
  "completedAt": "2026-05-08T12:34:31.159Z",  // null if still in progress
  "updatedAt":   "2026-05-08T12:38:12.727Z"
}
```

## 5. Metric formulas

These match the KG Review App's built-in admin scoring exactly. The numerator weights `partial` at half-credit:

```
numerator   = correct + 0.5 × partial
precision   = numerator / total_rated
recall      = numerator / (total_rated + len(missingTriples))
```

Notes:
- `missing` (kurang konteks) is counted in `total_rated` but contributes 0 to the numerator.
- If no `missingTriples` are added, `recall == precision` and recall provides no extra signal.
- Cohen's κ requires two reviewers rating **the same triples** on the same course; without that overlap, κ is not computable.

See `experiments/scripts/expert_review_analysis.py` for the reference implementation of all three metrics.

## 6. Querying Redis (Upstash)

### Connection
Upstash forces TLS. Connection string (currently hardcoded in `experiments/scripts/redis_check.py`):
```
rediss://default:<PASSWORD>@communal-horse-92107.upstash.io:6379
```
(`rediss://` with double `s` — the `redis://` scheme + `--tls` flag also works.) Move to env (`UPSTASH_REDIS_URL`) before any public-facing publication of this repo.

### Windows gotcha
Scoop's `redis-cli` for Windows ships **without a CA bundle**, so TLS verification fails with `SSL_connect failed: certificate verify failed`. Two fixes:

1. **Use Python** — `redis-py` + `certifi` works out of the box:
   ```python
   import redis, certifi
   r = redis.from_url(REDIS_URL, ssl_ca_certs=certifi.where(), decode_responses=True)
   ```
2. **Or pass cacert to redis-cli**:
   ```powershell
   $ca = uv run --with certifi python -c "import certifi; print(certifi.where())"
   redis-cli --tls --cacert $ca -u "redis://..." PING
   ```

### One-shot inspection
```bash
uv run python experiments/scripts/redis_check.py
```
Prints reviewer-by-reviewer rating distribution, completion status, and reconciles in-DB reviewers against the on-disk export folder.

### Useful key patterns
| Pattern | Purpose |
|---|---|
| `kg:courses` | The source dataset of triples (~230 KB JSON). Stable; this is what reviewers rate against. |
| `kg:progress:admin:*` | Admin starter slots — usually empty (~87 bytes). Ignore. |
| `kg:progress:expert-*:*-kelas-xii-*` | Reviewer progress. Size correlates with depth of review. |
| `kg:progress:dummy-user-1:*` | Test account. Exclude from real analysis. |

### Read-only invariant
All scripts in this repo must use read-only Redis commands (`GET`, `KEYS`, `SCAN`, `TYPE`, `STRLEN`, `DBSIZE`, etc.). **Never** `SET`, `DEL`, `FLUSHDB`, etc. — the live app writes there.

## 7. Current data state (as of 2026-05-08, last Redis dump)

5 reviewers produced substantive data, 9 sessions started but never advanced past empty:

| Reviewer (Redis ID) | Course | n rated | C/P/W/M | +missing | Status |
|---|---|---:|---:|---:|---|
| `expert-biologi-1` | biologi | 42 | 40/1/1/0 | 0 | partial |
| `expert-biologi-6` | biologi | 151 | 143/6/0/2 | 0 | done 2026-04-17 |
| `expert-fisika-2` | **kimia** ⚠️ | 54 | 47/5/2/0 | 0 | partial |
| `expert-fisika-6` | fisika | 240 | 186/40/3/11 | 0 | done 2026-04-20 |
| `expert-kimia-6` | kimia | 166 | 136/6/5/19 | **29** | done 2026-05-08 |

Aggregate precision ≈ 0.910; recall computable only for Kimia (0.713 via kimia-6's 29 added missing triples).

### Important staleness notes
- **`expert-kimia-6` re-saved on 2026-05-08** after the 2026-05-06 export. The on-disk JSON shows 0 missing triples; Redis shows 29. **For any new analysis, prefer Redis.** Re-export from the admin panel if you need the JSON form.
- `expert-fisika-6` opened the kimia course at 2026-05-08T10:43 — still empty as of last check. If completed, kimia becomes the first subject with a reviewer pair that overlaps enough for Cohen's κ.

## 8. Qualitative gold (already mined, useful for §4.2-style analysis)

`expert-kimia-6` left 30 comments. Three high-impact correction patterns:

- **Triple 4 (pH)**: definition should use ion *activity*, not concentration. Domain assumption (gamma=1) was hidden.
- **Triple 74 (pemurnian tembaga)**: `electroplating` is wrong — correct term is `elektrorefining`. Both terminologically plausible to a non-expert LLM.
- **Triple 139 (termoset)**: termoset *cannot* be melted back; system claim is wrong.

The 29 missing triples cluster by chapter: Elektrokimia (9), Makromolekul Organik (7), Gugus Fungsi (7), Larutan-Koloid (6). This distribution reveals systematic under-extraction in cause-effect chains, particularly around quantitative laws (Nernst, Faraday).

## 9. Scripts at a glance

| Script | Purpose |
|---|---|
| `experiments/scripts/redis_check.py` | Read-only Upstash inspection. Run first for current ground truth. |
| `experiments/scripts/expert_review_analysis.py` | Precision/recall/Cohen's κ over the JSON export folder. |
| `experiments/thesis_doc_inspect*.py` | Locate indices in the thesis Google Doc (unrelated to this brief). |

## 10. Open questions / known limits

- **No mapping from triple index → source dataset triple.** Reviewer JSONs use numeric indices but don't reference the source. Mapping requires the `kg:courses` Redis value at the time of export, which we have but haven't yet joined. Needed for per-Bab metrics.
- **Cohen's κ requires triple alignment.** Even when two reviewers exist for the same course, their indices must point to the same triples. Verify by checking `kg:courses` is unchanged between the two reviewers' `updatedAt` timestamps.
- **No version control on `kg:courses`.** If the app admin re-uploads a new triples JSON, prior reviewer ratings become misaligned. There is no audit trail for this in Redis.
