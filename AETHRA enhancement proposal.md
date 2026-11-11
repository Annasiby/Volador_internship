# Feature Proposal: Project-Level Analysis Run History

## Problem

Aethra supports analysis runs for vegetation and wetland projects. However, the current runs API focuses on launching a run and retrieving its status using a specific `run_id`.

For researchers, farmers, and environmental teams, this creates a workflow limitation: users need a convenient way to review previous analyses for the same project. Without a project-level run history, it is harder to revisit an earlier result, identify a failed run, or understand how analysis outcomes changed over time.

**Relevant code:** `backend/app/routers/runs.py`

- `POST /api/runs` — starts an analysis.
- `GET /api/runs/{run_id}` — retrieves an individual run's status.

The backend already organizes project workspaces and run outputs, making run-history retrieval a practical extension of the existing architecture.

## Proposed Solution

Introduce a **Project Analysis History** feature.

Add a project-scoped API endpoint:

`GET /api/projects/{project_id}/runs`

The endpoint should return a list of analysis runs associated with the requested project, including:

- Run ID
- Analysis mode: Vegetation or Wetland
- Run status: queued, running, completed, or failed, using the project's actual status conventions
- Start time and completion time, when available
- Analysis dates, when available
- A concise failure message, when available

The frontend can display these records in a simple history panel. Selecting a completed run should allow users to open its existing results and reports.

The feature should reuse the existing run state and project storage mechanisms rather than introducing a new database or changing the analysis pipeline.

## Acceptance Criteria

1. A valid project returns its associated analysis runs.
2. Runs are ordered from newest to oldest.
3. Runs from another project are never included.
4. The response includes useful status and timestamp information.
5. A nonexistent project returns a clear `404` response.
6. Missing or incomplete run metadata is handled without crashing the endpoint.
7. Existing run-launching, status, result, and report APIs continue to work.
8. Tests cover successful retrieval, empty history, invalid project IDs, and project isolation.

## Estimated Effort

**3–4 working days**

| Work | Estimate |
|---|---:|
| Review run metadata and storage structure | 0.5 day |
| Implement project-level history endpoint | 1 day |
| Add frontend history panel and result navigation | 1 day |
| Tests, integration, and documentation | 0.5–1.5 days |

## Risks and Mitigations

- **Incomplete metadata:** Older runs may not contain all fields. Return optional fields safely and avoid assuming every run has a completion timestamp.
- **In-memory run state:** Some status information is tracked in memory. Use persisted run metadata where available and verify behavior after backend restarts.
- **Large run history:** A project may accumulate many runs. Keep the response lightweight and consider pagination if history grows substantially.
- **Existing result compatibility:** Reuse the current result and report endpoints instead of duplicating their retrieval logic.

## Expected User Value

Users can revisit past analyses, track their project’s analysis history, and access earlier results without manually remembering run IDs. This improves traceability and makes Volador more useful for ongoing environmental monitoring.
