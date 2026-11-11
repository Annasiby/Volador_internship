# Feature Proposal: Project-Level Analysis Run History

**Product:** Aethra  
**Scope:** Backend API, run metadata, frontend history panel  
**Status:** Proposed  
**Estimate:** 4.5–5 working days

## Problem

Aethra supports analysis runs for vegetation and wetland projects. Today the runs API (`backend/app/routers/runs.py`) can only launch a run and fetch one run’s status by `run_id`:

- `POST /api/runs` starts an analysis.
- `GET /api/runs/{run_id}` returns a single run’s status.

There is no way to ask “what runs does this project have?” Researchers, farmers and environmental teams must remember run IDs to revisit an earlier result, find a failed run, or compare how outcomes changed over time. The frontend can only restore a project’s `latest_run_id`, so every earlier run is effectively unreachable from the UI.

Code review of the current implementation also shows that the existing run state is less durable than it appears, which affects how this feature must be built:

1. **Run status is memory-only.** `RUN_STATES` in `backend/app/services.py` is an in-memory dict. The code comment mentions JSON persistence, but nothing writes status to disk. A failed run therefore disappears after a backend restart.
2. **Recovered runs can be mislabeled.** After a restart, `RunWorker.get_run_status` rebuilds state from disk and defaults the status to `COMPLETED` when none is stored. Neither `manifest.json` nor `metadata.json` contains a status, so an incomplete or failed run can be reported as completed. One example in the repository is a run folder holding only alignment outputs, a config file and logs, with no results.
3. **Key fields are never saved.** Analysis mode, `project_id` and `started_at` are not persisted with a run. The project link exists only through the folder path `storage/projects/<project_id>/runs/`.
4. **Run IDs are not globally unique.** `run_id` is `run_YYYYMMDD_HHMMSS`, and `RUN_STATES` is keyed by `run_id` alone, so two projects launching in the same second can collide.
5. **Two on-disk layouts exist.** Older runs are stored as `runs/<id>/<id>/…` and current runs as `runs/<id>/…`. The results and reports routers already handle both, but run-status recovery does not. The `runs/` folder also contains temporary dot-prefixed config files that are not runs.

## Proposed Solution

Introduce a **Project Analysis History** feature.

### 1. New endpoint

`GET /api/projects/{project_id}/runs?limit=50&offset=0`

Returns the runs belonging to the requested project, newest first.

```json
{
  "project_id": "prj_1790921535755",
  "total": 12,
  "runs": [
    {
      "run_id": "run_20261002_055157",
      "mode": "wetland",
      "mode_inferred": false,
      "status": "COMPLETED",
      "created_at": "2026-10-02T05:51:57Z",
      "started_at": "2026-10-02T05:51:58Z",
      "completed_at": "2026-10-02T05:52:11Z",
      "t1_date": "2023-08-14",
      "t2_date": "2023-08-28",
      "error": null
    }
  ]
}
```

Field rules:

- `run_id` and `status` are always present. Every other field is optional so legacy runs serialize cleanly.
- `status` returns the project’s real values: `QUEUED`, `VALIDATING`, `PREPROCESSING`, `INFERENCE`, `CHANGE_ANALYSIS`, `REPORTING`, `COMPLETED`, `FAILED`. The frontend already uses these. Any in-progress value means “running”.
- `mode` is `vegetation` or `wetland`. `mode_inferred` is true when it was derived rather than recorded.
- `error` is a concise message truncated to about 300 characters, with no stack traces and no filesystem paths.
- Pagination is included from the start: `limit` defaults to 50 (maximum 200), plus `offset`. Adding it later would be a breaking change.

### 2. Persist a small run metadata file (additive)

`RunWorker.start_run` writes `run_meta.json` into the run folder at launch and updates it at completion or failure. It contains `project_id`, `mode`, `status`, `created_at`, `started_at`, `completed_at`, `t1_date`, `t2_date` and a truncated `error`.

- This is the only change to existing code paths. The analysis pipeline, the database layer (none is introduced) and the launch, status, results and report APIs are unchanged.
- It fixes the “failed run shows as completed after restart” defect, and it makes listing cheap because the large `analysis_result.json` no longer has to be parsed for every row.
- **Legacy runs** (no `run_meta.json`) are handled by inference: status and errors from `analysis_result.json`, dates and timestamps from `metadata.json`, and mode from the presence of wetland outputs. Inferred values are flagged, and a run with no usable evidence is reported with a conservative status rather than assumed complete.

### 3. Listing logic (service layer)

Implement `RunWorker.list_project_runs(project_id, limit, offset)` in `services.py`, with a thin route in `projects.py`:

1. Resolve the project through the existing `ProjectStore.get_project`. Unknown project returns `404 Project <id> not found`, matching the other routes.
2. List only directories inside the project’s `runs/` folder, skipping dot-prefixed files.
3. Sort by `run_id` descending. The timestamp is embedded in the ID, so ordering needs no file reads. Fall back to modification time for IDs that don’t match the pattern, with `run_id` as a deterministic tiebreaker.
4. Slice the requested page first, then read metadata only for those runs. Each read is wrapped in error handling, so a missing or corrupt file produces a degraded entry and a logged warning, never a 500.
5. Overlay in-memory state only for active runs whose `project_id` matches, so a run ID collision can never leak another project’s run into the list.
6. Support both the legacy nested layout and the current flat layout.

### 4. Frontend

- `getProjectRuns(projectId)` in `frontend/src/api/client.ts`.
- A `selectRun(runId)` method in `ProjectContext`. The context currently tracks a single active run, so this sets the selected run and reuses the existing `loadRunData`.
- A history panel with loading, empty, error and populated states, a status badge per run, and timestamps shown in the user’s locale.
- Completed runs open their existing results and reports. Failed runs show the short error message. Queued and running runs are shown but not openable.
- The list refreshes when a run is launched or finishes. No new real-time mechanism is added.

## Acceptance Criteria

- A valid project returns its own analysis runs.
- Runs are ordered from newest to oldest, deterministically.
- Runs from another project are never included, even when two projects share the same `run_id`.
- The response includes status, mode, start and completion times, analysis dates and a concise failure message where available.
- A project with no runs returns `200` with an empty list.
- A nonexistent or malformed project ID returns a clear `404`.
- Missing, incomplete or corrupt run metadata is handled without crashing the endpoint.
- A run that failed before a backend restart still shows as failed afterwards, and a partial run is never reported as completed.
- `limit` and `offset` behave correctly at their boundaries.
- Existing run-launch, status, result, layer and report APIs continue to work with their existing tests unmodified.
- Selecting a completed run in the UI opens its existing results and report.
- Tests cover success, ordering, empty history, invalid project IDs, project isolation, legacy layouts, corrupt metadata, restart behavior and pagination.

## Estimated Effort

| Work | Estimate |
|---|---|
| Finalize schema and contract (`RunSummary`, `ProjectRunsResponse`) | 0.25 day |
| `run_meta.json` write in `RunWorker` and legacy inference helper | 1 day |
| `list_project_runs` service function and `GET /api/projects/{id}/runs` route | 1 day |
| Backend tests, including a temporary-storage fixture (in parallel with the two items above) | 1 day |
| Frontend: API client, `selectRun`, history panel and result navigation | 1–1.5 days |
| Documentation (OpenAPI descriptions, metadata schema note), regression run, manual QA on a real project folder | 0.5 day |
| **Total** | **4.5–5 days** |

The original 3–4 day estimate did not include the metadata sidecar, legacy-layout handling or the context change on the frontend.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| **Incomplete legacy metadata.** Older runs lack status, mode and start time, and some are partial. | Make all non-ID fields optional. Infer from `analysis_result.json` and `metadata.json`, flag inferred values, and never default an unknown run to completed. |
| **In-memory run state.** Status is lost on restart and recovery defaults to `COMPLETED`. | Persist `run_meta.json` at launch and at terminal states. Add a restart-simulation test. Consider also correcting the recovery default in a follow-up. |
| **Run ID collisions across projects.** IDs have one-second resolution and `RUN_STATES` is keyed by `run_id` alone. | Filter strictly by project directory and by `project_id` in any in-memory overlay. Add an isolation test using identical run IDs. Track unique ID generation as a separate ticket. |
| **Two storage layouts.** Nested legacy folders and stray temporary files in `runs/`. | Detect both layouts, skip dotfiles, and cover each case with a test. |
| **Large run history.** A project can accumulate many runs. | Sort by ID without reading files, paginate before reading metadata, and keep each row lightweight. |
| **Tests write to the real `backend/storage`.** Existing tests use the live storage directory. | New tests redirect `app.services.STORAGE_DIR` to a temporary directory so they do not add files to the repository. |
| **Existing result and report compatibility.** | Reuse the current results and report endpoints through `run_id` instead of duplicating retrieval logic. Run the existing tests unmodified as a regression gate. |
| **Single-run frontend state.** `ProjectContext` tracks one active run. | Add `selectRun` as a small, isolated addition and verify that launching a new run still clears prior results correctly. |

## Out of Scope

- Changes to the analysis pipeline or engine.
- A new database or run-queue mechanism.
- Run deletion, comparison views or export of history.
- Replacing the `run_id` scheme (tracked separately).
- Repository clean-up of committed `storage/` outputs, cache folders and backup files (recommended as a separate change).

## Rollout

1. Merge the backend with the endpoint and sidecar write, behind no flag since it is purely additive.
2. Verify against a project containing both legacy and new runs.
3. Ship the frontend panel.
4. Monitor `5xx` responses on the new endpoint and the count of runs skipped as corrupt.

## Expected User Value

Users can revisit past analyses, spot failed runs, and open earlier results and reports without remembering run IDs. Teams get a reliable audit trail of what was run, in which mode and for which dates, which supports ongoing environmental monitoring. As a side benefit, persisting run status fixes a latent defect where failed or partial runs could be shown as completed after a restart.
