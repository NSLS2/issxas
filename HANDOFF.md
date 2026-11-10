# ISS Tiled Performance — Handoff Notes

**Date:** 2026-11-05  
**Participants so far:** Dan Allan, Kari Barry (test scans)  
**Repos in play:** `NSLS2/issxas`, `NSLS2/iss-profile-collection`

---

## Background

ISS switched from legacy databroker (MongoDB, in-process) to Tiled
(HTTP, central server). Post-scan processing became slow. We debugged
using Loki access logs on the central Tiled server.

**Tiled topology at ISS:**

- `iss/migration` — PG-backed, what the writer currently writes to
- `iss/raw` — MongoDB-backed, what the old databroker code reads from

The writing service account (`3c02439d`) only writes to `iss/migration`.
A separate service account (`b01dc96c`) retries `iss/raw` for every new
scan and gets 404 — those scans don't exist in MongoDB. This is a
separate configuration question (should ISS dual-write?).

The reading client (`kbarry` = Kari's profile collection session) reads
from `iss/migration` via `tiled_reading_client`.

---

## What we measured

Before any fixes, a simple fly scan (2 streams: `apb_stream`, `pb9_enc1`)
triggered **27 HTTP requests** from the read side, taking **~20 seconds**:

- 10× `GET /metadata/<uid>` — the run-level start doc, re-fetched on
  every `hdr.start` property access
- 6× `GET /search/<uid>/stream` — stream child enumeration, repeated
  3× per stream instead of once
- 2× `GET /array/full/...` — the actual data (the only 2 useful calls)
- 1× `POST /custom/validate/<uid>?fix=true&read=true` — migration fixup,
  ~2s, triggered on first access of a new run; not removable from client
- 1× `PATCH /metadata/<uid>` — follows the validate call

The write side completes in ~4 seconds for the same scan. The 20-second
overhead was entirely navigation round-trips.

Root causes:

1. **`db[uid]` called independently in each `load_*` function.** On a
   Tiled client, `db[uid]` resolves the run via `GET /metadata/<uid>`.
   The `xas` library was calling this in every `load_apb_dataset_from_db`,
   `load_apb_trig_dataset_from_db`, `load_xs3_dataset_from_db`, etc. —
   once per stream type, all for the same uid. That accounts for the 10×
   `GET /metadata/<uid>` seen per scan.

2. **Per-stream node traversal on every field access.** Each call to
   `_read_tiled_field(hdr, stream_name, field)` traverses the lazy Tiled
   node tree from the run down to the array: `hdr[stream][data][field]`.
   Each level of that traversal issues search/metadata requests, producing
   ~5 requests per field before the actual `GET /array/full/...`. This is
   the dominant overhead and is not yet fixed.

Note: `hdr.start` itself is **not** an HTTP round-trip — it is populated
from the same response that resolved the run. The cost is entirely in
`db[uid]` calls and stream node traversal.

---

## Changes made

### `NSLS2/issxas` — branch `perf/avoid-redundant-tiled-fetches-ds`

Commit `30a2d6d` on top of `data-security`.

**Files changed:** `xas/db_io.py`, `xas/process.py`

Key changes:

- All `load_*` functions in `db_io.py` gain an optional `hdr=None`
  parameter. When provided by the caller, the internal `db[uid]` lookup
  is skipped.
- Each function snapshots `start = dict(hdr.start)` once at the top and
  uses the local dict throughout. (`hdr.start` is not itself an HTTP
  request, but snapshotting avoids any future regression if that changes.)
- `process.py` resolves `hdr` once per uid in `process_interpolate_bin`,
  `get_processed_df_from_uid`, and
  `get_processed_df_from_uid_for_epics_fly_scan`; snapshots `start` and
  `stream_names` immediately; passes `hdr=hdr` to every `load_*` call.
- Conflict resolution with `data-security`: that branch had already
  replaced `hdr.data()` calls with `_read_tiled_field`/`_read_tiled_records`
  helpers in `load_xs3_dataset_from_db` and `load_xia_dataset_from_db`;
  we kept those and added the `hdr=` parameter only.

**To sign and push:**
```bash
git -C ~/Repos/bnl/ansible/issxas rebase \
    --exec 'git commit --amend --no-edit -S' \
    upstream-https/data-security &&
git -C ~/Repos/bnl/ansible/issxas push origin perf/avoid-redundant-tiled-fetches-ds
```

### `NSLS2/iss-profile-collection` — branch `perf/avoid-redundant-tiled-fetches`

Commit `5ce3cd1` on top of `data-security`.

**Files changed:** `startup/62-general_scans.py`,
`startup/82-johann_plans.py`, `startup/83-johann_alignment_plans.py`

Key changes:

- `tuning_scan`: `hdr.table()` called once and result reused (was called
  twice, once per column access).
- `johann_add_scan_to_fly_calibration_data_plan` and
  `johann_add_scan_to_alignment_data_plan`: `start = dict(db[uid].start)`
  snapshotted once; subsequent accesses use the local dict.

**To sign and push:**
```bash
git -C ~/Repos/bnl/ansible/iss-profile-collection rebase \
    --exec 'git commit --amend --no-edit -S' \
    42f62417d5a0edcf700eca01607b3bf1cf875a7c &&
git -C ~/Repos/bnl/ansible/iss-profile-collection push origin perf/avoid-redundant-tiled-fetches
```

---

## Current status (as of end of session)

The `issxas` changes were deployed to the editable install at
`/nsls2/data/iss/shared/config/repos/xas/` via `pixi clean && pixi install`.

**The Loki logs for the first post-deploy scan (`3447e4ac`,
scan_id=222591) still show 27 requests and ~74 seconds** — worse than
before. The `hdr=` fix correctly eliminates redundant `db[uid]` calls,
but the dominant overhead is the per-stream node traversal inside
`_read_tiled_field`/`_read_tiled_records`, which is unchanged. That
traversal generates ~5 requests per stream field regardless of whether
`hdr` is shared.

There is also a new 31-second pause between the validate+patch step and
the first search call, which was not present before. Likely the
`IndexError` (see below) being caught and silently swallowed somewhere,
or a blocking call in the new `_read_tiled_field` path introduced by
`data-security`. Needs a full traceback to confirm.

**The main remaining work** is fixing the per-stream traversal overhead
(open issue 2 below), not the `hdr=` / `hdr.start` changes already made.

---

## Open issues

### 1. `IndexError` in `interpolate.py` (separate from the performance work)

An `IndexError` out of pandas is raised inside `xas/interpolate.py`
during post-scan processing. The likely cause is `interpolate()` being
called with an empty DataFrame for one of the streams:

```python
# interpolate.py:13
min_timestamp = max([dataset.get(key).iloc[0, 0] for key in dataset])
```

If any stream has zero rows (e.g. `load_apb_dataset_from_db` strips all
rows as padding), `iloc[0, 0]` raises `IndexError`. This was present
before our changes and is independent of the Tiled work. Fix: guard
against empty DataFrames before calling `interpolate()`, or inside
`interpolate()` itself.

### 2. Per-stream navigation overhead — the main remaining problem

Each call to `_read_tiled_field(hdr, stream_name, field)` traverses the
lazy Tiled node tree from scratch: `hdr[stream_name]['data'][field]`.
Each level issues HTTP requests, producing roughly:

```
GET /search/<uid>/<stream>           ← enumerate stream children
GET /metadata/<uid>/<stream>/internal
GET /search/<uid>/<stream>           ← again (Tiled client re-queries)
GET /search/<uid>/<stream>           ← again
GET /metadata/<uid>/<stream>/<field> ← array metadata
GET /array/full/<uid>/<stream>/<field>  ← actual data
```

For a scan with 2 streams and 1 field each, that's ~10 navigation
requests for 2 data reads. This is the **dominant overhead** and is not
addressed by the `hdr=` fix.

**What to try next:**

- Navigate to each stream node once and cache it:
  ```python
  stream_node = hdr[stream_name]['data']
  apb_data = stream_node['apb_stream'].read()
  enc_data = stream_node['pb9_enc1'].read()
  ```
  This should collapse the repeated search/metadata calls per stream.

- Alternatively, check whether the Tiled client has a bulk-read path
  that fetches all fields of a stream in one request.

The `hdr=` parameter already in place is the right foundation — the
caller now holds a single resolved `hdr` object. The next step is to
navigate into each stream node once and reuse that node for all field
reads rather than re-traversing from `hdr` for every field.

### 3. `POST /custom/validate/<uid>?fix=true&read=true` adds ~2s

This is triggered by the Tiled client on first access of a run written
by the migration writer. It's server-side migration fixup and cannot be
eliminated from the client. The ~2s it takes is the floor for first
access of any new run.

### 4. `iss/raw` 404s

The processing service account (`b01dc96c`) retries `iss/raw` for every
new scan and gets 404. If ISS is not supposed to dual-write to both
`raw` and `migration`, this service should be pointed at `migration`
only. If ISS should dual-write, the `TiledWriter` in
`startup/02-tiled-writer.py` needs a second subscriber pointed at
`from_profile("nsls2")["iss"]["raw"]`.

---

## Useful commands for further debugging

```bash
# Watch live Tiled requests for kbarry on ISS
# (replace time window as needed)
START=$(date -u -d '-5 minutes' +%FT%TZ)
END=$(date -u +%FT%TZ)
# via loki.sh in the opencode skills:
/etc/opencode/skills/loki-logs/scripts/loki.sh range \
    '{service_name=~"tiled-800."} |~ "kbarry" |~ "/iss/" !~ "MemoryHandler"' \
    "$START" "$END" 200

# Count requests and timing for a specific scan UID
# (substitute the UID)
/etc/opencode/skills/loki-logs/scripts/loki.sh range \
    '{service_name=~"tiled-800."} |~ "<uid>" !~ "MemoryHandler"' \
    "$START" "$END" 200
```

The repo clones with the branches are at:
- `~/Repos/bnl/ansible/issxas/` (branch `perf/avoid-redundant-tiled-fetches-ds`)
- `~/Repos/bnl/ansible/iss-profile-collection/` (branch `perf/avoid-redundant-tiled-fetches`)
