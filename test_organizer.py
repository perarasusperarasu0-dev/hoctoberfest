"""
Unit tests for core/organizer.py
"""

from pathlib import Path
import json
import pytest
from core.organizer import (
    SafeOrganizer,
    resolve_collision_path,
    ProposedAction,
)


@pytest.fixture
def org_workspace(tmp_path: Path):
    """Sets up temporary source and destination folders."""
    src = tmp_path / "source"
    dst = tmp_path / "organized"
    log_dir = tmp_path / "logs"
    src.mkdir(parents=True, exist_ok=True)
    dst.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    return {"src": src, "dst": dst, "log_dir": log_dir}


def test_resolve_collision_path_non_existing(org_workspace):
    dst = org_workspace["dst"]
    target = resolve_collision_path(dst, "new_file.txt")
    assert target.name == "new_file.txt"


def test_resolve_collision_path_increments(org_workspace):
    dst = org_workspace["dst"]
    # Create existing files
    (dst / "report.pdf").write_text("v1")
    (dst / "report (1).pdf").write_text("v2")

    target = resolve_collision_path(dst, "report.pdf")
    assert target.name == "report (2).pdf"


def test_execute_batch_copy_mode(org_workspace):
    src = org_workspace["src"]
    dst = org_workspace["dst"]
    log_dir = org_workspace["log_dir"]

    # Create dummy source file
    test_file = src / "tax_2026.pdf"
    test_file.write_text("Secret financial data here")

    organizer = SafeOrganizer(log_dir=log_dir)
    target_dir = dst / "Finance"
    proposal = ProposedAction(
        file_path=test_file,
        file_name=test_file.name,
        proposed_category="Finance",
        target_dir=target_dir,
        proposed_destination=target_dir / test_file.name,
        reason="Invoice detected",
        is_selected=True,
    )

    batch_res = organizer.execute_batch([proposal], action_mode="COPY")
    assert batch_res.success_count == 1
    assert test_file.exists()  # Original still safe
    assert (target_dir / "tax_2026.pdf").exists()  # Copy created

    # Check Audit Log: must NOT contain sensitive contents
    log_file = log_dir / "lazysort_audit.jsonl"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Secret financial data here" not in content
    log_entry = json.loads(content.strip().splitlines()[-1])
    assert log_entry["action_type"] == "COPY"
    assert log_entry["status"] == "SUCCESS"


def test_execute_batch_move_and_undo(org_workspace):
    src = org_workspace["src"]
    dst = org_workspace["dst"]
    log_dir = org_workspace["log_dir"]

    test_file = src / "notes.txt"
    test_file.write_text("Lecture notes content")

    organizer = SafeOrganizer(log_dir=log_dir)
    target_dir = dst / "Education"
    proposal = ProposedAction(
        file_path=test_file,
        file_name=test_file.name,
        proposed_category="Education",
        target_dir=target_dir,
        proposed_destination=target_dir / test_file.name,
        reason="Class notes",
        is_selected=True,
    )

    # 1. Execute MOVE
    batch_res = organizer.execute_batch([proposal], action_mode="MOVE")
    assert batch_res.success_count == 1
    assert not test_file.exists()  # Moved from source
    assert (target_dir / "notes.txt").exists()  # Now in target

    # 2. Execute UNDO
    undo_res = organizer.undo_batch(batch_res.batch_id)
    assert undo_res["ok"] is True
    assert undo_res["undone_count"] == 1
    assert test_file.exists()  # Restored to source
    assert not (target_dir / "notes.txt").exists()
