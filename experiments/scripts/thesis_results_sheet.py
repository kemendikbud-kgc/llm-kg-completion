"""
Sync expert review results from Upstash Redis to a Google Sheet.

The Sheet is the live source for thesis Bab 4 charts. Three tabs:
  distribution      — per-reviewer Correct/Partial/Wrong/MissingContext counts
  precision         — per-reviewer precision (and aggregate row)
  missing_per_bab   — count of reviewer-added missing triples grouped by chapter

Two modes:
  default        — pull Redis, overwrite the three data ranges
  --bootstrap    — additionally (re)create the three charts on each tab

Re-run after new reviewer data lands; linked charts in the thesis Doc will
show an "Update" button the next time you open the Doc.

Env vars:
  THESIS_RESULTS_SHEET_ID   — required. Spreadsheet ID.
  UPSTASH_REDIS_URL         — optional. Defaults to the hardcoded URL in
                              experiments/scripts/redis_check.py for backwards compat.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import certifi
import redis
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEFAULT_REDIS_URL = (
    "rediss://default:gQAAAAAAAWfLAAIncDEyZjAzMWVmMDQ1OGM0ODk5YWFhZDAxY2IzOGVhNDY1MnAxOTIxMDc"
    "@communal-horse-92107.upstash.io:6379"
)

SHEET_ID = os.environ.get("THESIS_RESULTS_SHEET_ID")
REDIS_URL = os.environ.get("UPSTASH_REDIS_URL", DEFAULT_REDIS_URL)

# Sheet IDs from bootstrap; keep in sync with the tab order if you re-create.
TAB_IDS = {"distribution": 0, "precision": 1, "missing_per_bab": 2}


def gws(args: list[str], json_body: str | None = None) -> dict | None:
    """Run gws CLI, strip 'Using keyring' preamble, return parsed JSON or None."""
    cmd = ["gws", *args, "--format", "json"]
    if json_body is not None:
        cmd += ["--json", json_body]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[gws ERROR] cmd={' '.join(cmd)}", file=sys.stderr)
        print(res.stderr, file=sys.stderr)
        raise SystemExit(1)
    out = res.stdout
    i = out.find("{")
    if i == -1:
        return None
    payload = json.loads(out[i:])
    if isinstance(payload, dict) and "error" in payload:
        raise SystemExit(f"[gws API ERROR] {payload['error']}")
    return payload


# ---------- data extraction ----------------------------------------------------

def fetch_redis_state() -> tuple[list[dict], Counter]:
    """Returns (reviewer_rows, missing_per_chapter)."""
    r = redis.from_url(REDIS_URL, ssl_ca_certs=certifi.where(), decode_responses=True)
    keys = sorted(r.keys("kg:progress:*"))
    rows: list[dict] = []
    missing_per_chapter: Counter = Counter()
    for k in keys:
        raw = r.get(k)
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            continue
        rest = k.replace("kg:progress:", "")
        if ":" not in rest:
            continue
        reviewer, course = rest.split(":", 1)
        if reviewer.startswith("dummy") or reviewer == "admin":
            continue
        ratings = d.get("ratings", {}) or {}
        if not ratings:
            continue
        counts = Counter(ratings.values())
        missing_triples = d.get("missingTriples", []) or []
        rows.append(
            {
                "reviewer": reviewer,
                "course": course,
                "n": len(ratings),
                "correct": counts.get("correct", 0),
                "partial": counts.get("partial", 0),
                "wrong": counts.get("wrong", 0),
                "missing_context": counts.get("missing", 0),
                "n_added_missing": len(missing_triples),
                "completed_at": d.get("completedAt") or "",
                "updated_at": d.get("updatedAt") or "",
            }
        )
        for mt in missing_triples:
            chapter = (mt.get("chapter") or "(tanpa Bab)").strip()
            missing_per_chapter[chapter] += 1

    rows.sort(key=lambda x: (x["course"], x["reviewer"]))
    return rows, missing_per_chapter


# ---------- value table builders ----------------------------------------------

def build_distribution_values(rows: list[dict]) -> list[list]:
    header = ["Reviewer", "Course", "Benar", "Sebagian", "Salah", "Kurang Konteks", "n"]
    out = [header]
    for r in rows:
        out.append(
            [
                r["reviewer"],
                r["course"],
                r["correct"],
                r["partial"],
                r["wrong"],
                r["missing_context"],
                r["n"],
            ]
        )
    return out


def build_precision_values(rows: list[dict]) -> list[list]:
    header = ["Reviewer", "Mata Pelajaran", "n", "Presisi", "Recall (jika ada)"]
    out = [header]
    total_num = total_den = 0
    for r in rows:
        num = r["correct"] + 0.5 * r["partial"]
        prec = num / r["n"] if r["n"] else float("nan")
        rec = (
            num / (r["n"] + r["n_added_missing"])
            if r["n_added_missing"]
            else ""
        )
        subject = r["course"].split("-")[0]
        out.append(
            [
                r["reviewer"],
                subject,
                r["n"],
                round(prec, 4),
                round(rec, 4) if isinstance(rec, float) else rec,
            ]
        )
        total_num += num
        total_den += r["n"]
    if total_den:
        out.append(["Rata-rata", "", total_den, round(total_num / total_den, 4), ""])
    return out


def build_missing_per_bab_values(missing: Counter) -> list[list]:
    header = ["Bab / Chapter", "Jumlah Missing Triple"]
    out = [header]
    for chapter, n in sorted(missing.items(), key=lambda kv: -kv[1]):
        out.append([chapter, n])
    return out


# ---------- write to sheet -----------------------------------------------------

def write_values(sheet_id: str, tab: str, values: list[list]) -> None:
    cols = max(len(r) for r in values)
    end_col = chr(ord("A") + cols - 1)
    rng = f"{tab}!A1:{end_col}{len(values) + 50}"
    # Clear then write to avoid leftover rows when reviewer count shrinks.
    gws(
        ["sheets", "spreadsheets", "values", "clear",
         "--params", json.dumps({"spreadsheetId": sheet_id, "range": rng})],
    )
    body = {"values": values}
    gws(
        [
            "sheets", "spreadsheets", "values", "update",
            "--params", json.dumps({
                "spreadsheetId": sheet_id,
                "range": f"{tab}!A1",
                "valueInputOption": "RAW",
            }),
        ],
        json_body=json.dumps(body),
    )


# ---------- chart specs --------------------------------------------------------

def _range(sheet_id: int, r0: int, r1: int, c0: int, c1: int) -> dict:
    return {
        "sources": [{
            "sheetId": sheet_id,
            "startRowIndex": r0, "endRowIndex": r1,
            "startColumnIndex": c0, "endColumnIndex": c1,
        }]
    }


def chart_distribution_spec(n_rows: int, sheet_id: int) -> dict:
    """Stacked column chart: x = reviewer, stacked series = C/P/W/M."""
    end_row = n_rows + 1  # +1 for header
    return {
        "title": "Distribusi Penilaian per Reviewer (Fase 1)",
        "basicChart": {
            "chartType": "COLUMN",
            "stackedType": "STACKED",
            "legendPosition": "BOTTOM_LEGEND",
            "headerCount": 1,
            "axis": [
                {"position": "BOTTOM_AXIS", "title": "Reviewer"},
                {"position": "LEFT_AXIS", "title": "Jumlah Triple"},
            ],
            "domains": [{"domain": {"sourceRange": _range(sheet_id, 0, end_row, 0, 1)}}],
            "series": [
                {"series": {"sourceRange": _range(sheet_id, 0, end_row, 2, 3)}, "targetAxis": "LEFT_AXIS"},
                {"series": {"sourceRange": _range(sheet_id, 0, end_row, 3, 4)}, "targetAxis": "LEFT_AXIS"},
                {"series": {"sourceRange": _range(sheet_id, 0, end_row, 4, 5)}, "targetAxis": "LEFT_AXIS"},
                {"series": {"sourceRange": _range(sheet_id, 0, end_row, 5, 6)}, "targetAxis": "LEFT_AXIS"},
            ],
        },
    }


def chart_precision_spec(n_rows: int, sheet_id: int) -> dict:
    """Column chart of precision per reviewer (excludes the Rata-rata row)."""
    end_row = n_rows  # exclude average row
    return {
        "title": "Presisi Validasi per Reviewer",
        "basicChart": {
            "chartType": "COLUMN",
            "legendPosition": "NO_LEGEND",
            "headerCount": 1,
            "axis": [
                {"position": "BOTTOM_AXIS", "title": "Reviewer"},
                {"position": "LEFT_AXIS", "title": "Presisi"},
            ],
            "domains": [{"domain": {"sourceRange": _range(sheet_id, 0, end_row, 0, 1)}}],
            "series": [
                {"series": {"sourceRange": _range(sheet_id, 0, end_row, 3, 4)}, "targetAxis": "LEFT_AXIS"},
            ],
        },
    }


def chart_missing_per_bab_spec(n_rows: int, sheet_id: int) -> dict:
    """Horizontal bar chart of missing triples per chapter."""
    end_row = n_rows + 1
    return {
        "title": "Missing Triple yang Diusulkan Pakar — per Bab",
        "basicChart": {
            "chartType": "BAR",
            "legendPosition": "NO_LEGEND",
            "headerCount": 1,
            "axis": [
                {"position": "BOTTOM_AXIS", "title": "Jumlah Missing Triple"},
                {"position": "LEFT_AXIS", "title": "Bab"},
            ],
            "domains": [{"domain": {"sourceRange": _range(sheet_id, 0, end_row, 0, 1)}}],
            "series": [
                {"series": {"sourceRange": _range(sheet_id, 0, end_row, 1, 2)}, "targetAxis": "BOTTOM_AXIS"},
            ],
        },
    }


# ---------- chart create/replace ----------------------------------------------

def list_chart_ids(sheet_id: str) -> dict[int, list[int]]:
    """sheetId -> [chartId,...] currently embedded in that tab."""
    result = gws(
        ["sheets", "spreadsheets", "get",
         "--params", json.dumps({"spreadsheetId": sheet_id, "fields": "sheets(properties.sheetId,charts.chartId)"})],
    )
    out: dict[int, list[int]] = {}
    for s in (result or {}).get("sheets", []):
        sid = s["properties"]["sheetId"]
        out[sid] = [c["chartId"] for c in s.get("charts", [])]
    return out


def replace_charts(sheet_id: str, n_dist: int, n_prec: int, n_miss: int) -> None:
    """Delete any existing charts and re-add the three with current row counts."""
    existing = list_chart_ids(sheet_id)
    requests: list[dict] = []
    for chart_ids in existing.values():
        for cid in chart_ids:
            requests.append({"deleteEmbeddedObject": {"objectId": cid}})

    def add(spec: dict, target_sheet_id: int, anchor_col: int) -> dict:
        return {
            "addChart": {
                "chart": {
                    "spec": spec,
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": target_sheet_id,
                                "rowIndex": 0,
                                "columnIndex": anchor_col,
                            },
                            "widthPixels": 640,
                            "heightPixels": 360,
                        }
                    },
                }
            }
        }

    requests.append(add(chart_distribution_spec(n_dist, TAB_IDS["distribution"]),
                        TAB_IDS["distribution"], anchor_col=8))
    requests.append(add(chart_precision_spec(n_prec, TAB_IDS["precision"]),
                        TAB_IDS["precision"], anchor_col=6))
    requests.append(add(chart_missing_per_bab_spec(n_miss, TAB_IDS["missing_per_bab"]),
                        TAB_IDS["missing_per_bab"], anchor_col=4))

    gws(
        ["sheets", "spreadsheets", "batchUpdate",
         "--params", json.dumps({"spreadsheetId": sheet_id})],
        json_body=json.dumps({"requests": requests}),
    )


# ---------- main ---------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", action="store_true",
                        help="Also (re)create the three charts.")
    args = parser.parse_args()

    if not SHEET_ID:
        print("THESIS_RESULTS_SHEET_ID not set in .env", file=sys.stderr)
        return 1

    rows, missing = fetch_redis_state()
    print(f"Pulled {len(rows)} substantive reviewer sessions, "
          f"{sum(missing.values())} missing triples across {len(missing)} Bab.")

    dist_vals = build_distribution_values(rows)
    prec_vals = build_precision_values(rows)
    miss_vals = build_missing_per_bab_values(missing)

    write_values(SHEET_ID, "distribution", dist_vals)
    write_values(SHEET_ID, "precision", prec_vals)
    write_values(SHEET_ID, "missing_per_bab", miss_vals)

    if args.bootstrap:
        # n_dist = number of reviewer rows (excl header)
        # n_prec = reviewer rows + 1 (header included in end_row); exclude Rata-rata row from chart
        #         we pass len(rows) so chart domain covers header..last reviewer (n_prec rows after header)
        # n_miss = number of chapters
        replace_charts(
            SHEET_ID,
            n_dist=len(rows),
            n_prec=len(rows),
            n_miss=len(miss_vals) - 1,
        )
        print("Charts (re)created.")

    print(f"\nSheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
