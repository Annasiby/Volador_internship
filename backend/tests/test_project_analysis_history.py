"""
backend/tests/test_project_analysis_history.py
==============================================
Tests for the Project Analysis History feature:
- Listing runs per project
- Ordering newest to oldest deterministically
- Project isolation (preventing cross-project run leaks)
- Metadata durability and restart behavior
- Corrupt/missing metadata degradation without 500
- Legacy layouts (flat vs nested)
- Pagination limits and offsets
"""

import sys
import json
import shutil
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
ENGINE_SRC = BACKEND_DIR / "Engine_module" / "src"
sys.path.insert(0, str(ENGINE_SRC))

from app.services import ProjectStore, RunWorker, RUN_STATES, STORAGE_DIR
from app.routers.projects import list_project_runs
from app.schemas import ProjectRunsResponse


def test_list_project_runs_success():
    """Test that a valid project returns its runs with correct structure."""
    res = list_project_runs("prj_1790921535755", limit=50, offset=0)
    assert res["project_id"] == "prj_1790921535755"
    assert res["total"] >= 5
    assert len(res["runs"]) >= 5

    # Check ordering: newest to oldest
    run_ids = [r["run_id"] for r in res["runs"]]
    assert run_ids == sorted(run_ids, reverse=True)

    # Check run fields
    for r in res["runs"]:
        assert "run_id" in r
        assert "status" in r
        assert r["status"] in ["COMPLETED", "FAILED", "QUEUED", "VALIDATING", "PREPROCESSING", "INFERENCE", "CHANGE_ANALYSIS", "REPORTING"]
        if r["error"]:
            assert len(r["error"]) <= 300
            assert "C:\\" not in r["error"]
            assert "Traceback" not in r["error"]


def test_empty_project_history():
    """Test that a project with no runs returns 200 with an empty list."""
    # Create temporary project
    proj = ProjectStore.create_project("Empty History Project", "Desc", "AOI")
    proj_id = proj["id"]
    try:
        res = list_project_runs(proj_id, limit=50, offset=0)
        assert res["project_id"] == proj_id
        assert res["total"] == 0
        assert res["runs"] == []
    finally:
        ProjectStore.delete_project(proj_id)


def test_invalid_project_404():
    """Test that nonexistent project ID raises 404."""
    from fastapi import HTTPException

    try:
        list_project_runs("nonexistent_prj_99999999", limit=50, offset=0)
        assert False, "Should have raised HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert "nonexistent_prj_99999999 not found" in exc.detail


def test_project_isolation_and_collision():
    """
    Test that runs from another project are never included,
    even when two projects share the same run_id and active memory.
    """
    proj_a = ProjectStore.create_project("Project A", "Isolation test", "AOI")
    proj_b = ProjectStore.create_project("Project B", "Isolation test", "AOI")
    p_a_id = proj_a["id"]
    p_b_id = proj_b["id"]

    try:
        # Create identical run_id in both projects on disk
        collision_run_id = "run_20261117_120000"
        dir_a = STORAGE_DIR / "projects" / p_a_id / "runs" / collision_run_id
        dir_b = STORAGE_DIR / "projects" / p_b_id / "runs" / collision_run_id
        dir_a.mkdir(parents=True, exist_ok=True)
        dir_b.mkdir(parents=True, exist_ok=True)

        meta_a = {
            "project_id": p_a_id,
            "run_id": collision_run_id,
            "status": "COMPLETED",
            "mode": "wetland",
            "created_at": "2026-11-17T12:00:00Z"
        }
        meta_b = {
            "project_id": p_b_id,
            "run_id": collision_run_id,
            "status": "FAILED",
            "mode": "vegetation",
            "created_at": "2026-11-17T12:00:00Z",
            "error": "Error in Project B"
        }
        with open(dir_a / "run_meta.json", "w") as f:
            json.dump(meta_a, f)
        with open(dir_b / "run_meta.json", "w") as f:
            json.dump(meta_b, f)

        # Set RUN_STATES to Project B's state
        RUN_STATES[collision_run_id] = {
            "project_id": p_b_id,
            "run_id": collision_run_id,
            "status": "FAILED",
            "error": "In-memory state for B"
        }

        # List Project A: must NOT leak Project B's in-memory state
        res_a = list_project_runs(p_a_id, limit=50, offset=0)
        assert res_a["total"] == 1
        assert res_a["runs"][0]["run_id"] == collision_run_id
        assert res_a["runs"][0]["status"] == "COMPLETED"
        assert res_a["runs"][0]["mode"] == "wetland"
        assert res_a["runs"][0]["error"] is None

        # List Project B: receives Project B's state
        res_b = list_project_runs(p_b_id, limit=50, offset=0)
        assert res_b["total"] == 1
        assert res_b["runs"][0]["run_id"] == collision_run_id
        assert res_b["runs"][0]["status"] == "FAILED"
        assert res_b["runs"][0]["mode"] == "vegetation"
    finally:
        RUN_STATES.pop(collision_run_id, None)
        ProjectStore.delete_project(p_a_id)
        ProjectStore.delete_project(p_b_id)


def test_corrupt_metadata_degradation():
    """Test that a corrupt run_meta.json produces degraded entry, not a 500."""
    proj = ProjectStore.create_project("Corrupt Test Project", "Desc", "AOI")
    p_id = proj["id"]
    try:
        run_id = "run_20261117_130000"
        run_dir = STORAGE_DIR / "projects" / p_id / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        # Corrupt JSON
        with open(run_dir / "run_meta.json", "w") as f:
            f.write("{invalid json file content!!")

        res = list_project_runs(p_id, limit=50, offset=0)
        assert res["total"] == 1
        entry = res["runs"][0]
        assert entry["run_id"] == run_id
        assert entry["status"] == "FAILED"
        assert "incomplete" in entry["error"].lower() or "unreadable" in entry["error"].lower() or "terminated" in entry["error"].lower()
    finally:
        ProjectStore.delete_project(p_id)


def test_legacy_nested_layout():
    """Test that legacy nested runs/<id>/<id>/... are resolved cleanly."""
    proj = ProjectStore.create_project("Legacy Layout Project", "Desc", "AOI")
    p_id = proj["id"]
    try:
        run_id = "run_20261117_140000"
        nested_dir = STORAGE_DIR / "projects" / p_id / "runs" / run_id / run_id
        nested_dir.mkdir(parents=True, exist_ok=True)
        with open(nested_dir / "analysis_result.json", "w") as f:
            json.dump({
                "run_id": run_id,
                "status": "SUCCESS",
                "analysis_mode": "vegetation"
            }, f)

        res = list_project_runs(p_id, limit=50, offset=0)
        assert res["total"] == 1
        entry = res["runs"][0]
        assert entry["run_id"] == run_id
        assert entry["status"] == "COMPLETED"
        assert entry["mode"] == "vegetation"
        assert entry["mode_inferred"] is True
    finally:
        ProjectStore.delete_project(p_id)


def test_pagination():
    """Test limit and offset boundaries."""
    res_page1 = list_project_runs("prj_1790921535755", limit=2, offset=0)
    assert len(res_page1["runs"]) == 2

    res_page2 = list_project_runs("prj_1790921535755", limit=2, offset=2)
    assert len(res_page2["runs"]) == 2
    assert res_page1["runs"][0]["run_id"] != res_page2["runs"][0]["run_id"]

    # Offset beyond total
    res_out_of_bounds = list_project_runs("prj_1790921535755", limit=50, offset=1000)
    assert res_out_of_bounds["runs"] == []
    assert res_out_of_bounds["total"] >= 5


if __name__ == "__main__":
    test_list_project_runs_success()
    test_empty_project_history()
    test_invalid_project_404()
    test_project_isolation_and_collision()
    test_corrupt_metadata_degradation()
    test_legacy_nested_layout()
    test_pagination()
    print("ALL TESTS PASSED SUCCESSFULLY!")
