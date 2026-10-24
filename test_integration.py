"""
End-to-end integration test for LazySort.
Tests sample file generation, extraction, classification, collision prevention, and undo.
"""

from pathlib import Path
import pytest
from core.extractor import extract_file_content
from core.classifier import SemanticClassifier
from core.organizer import SafeOrganizer
from core.demo_data import generate_sample_dataset


def test_full_end_to_end_flow(tmp_path: Path):
    sample_dir = tmp_path / "test_samples"
    dest_dir = tmp_path / "test_organized"
    log_dir = tmp_path / "test_logs"

    # 1. Generate sample dataset
    sample_files = generate_sample_dataset(sample_dir)
    assert len(sample_files) == 8

    # 2. Extract & Classify
    classifier = SemanticClassifier()
    extracted_items = [extract_file_content(f) for f in sample_files]
    classifications = [classifier.classify_file(e, demo_mode=True) for e in extracted_items]
    assert len(classifications) == 8

    # 3. Plan Organization
    organizer = SafeOrganizer(log_dir=log_dir)
    proposals = organizer.plan_organization(classifications, dest_dir)
    assert len(proposals) == 8

    # Verify categories
    categories = {p.proposed_category for p in proposals}
    assert "Finance" in categories
    assert "Work" in categories
    assert "Education" in categories
    assert "Documents" in categories
    assert "Images" in categories
    assert "Others" in categories

    # 4. Execute Batch 1 (COPY)
    batch_1 = organizer.execute_batch(proposals, action_mode="COPY")
    assert batch_1.success_count == 8
    assert batch_1.fail_count == 0

    # Verify files created in destination
    for cat in ["Finance", "Work", "Education", "Documents", "Images", "Others"]:
        cat_folder = dest_dir / cat
        assert cat_folder.exists(), f"Expected category folder {cat} to exist"

    # 5. Collision Prevention Test: Execute identical batch a second time
    proposals_2 = organizer.plan_organization(classifications, dest_dir)
    batch_2 = organizer.execute_batch(proposals_2, action_mode="COPY")
    assert batch_2.success_count == 8

    # Check that collision files with " (1)" were generated
    collision_files = list(dest_dir.rglob("* (1).*"))
    assert len(collision_files) == 8

    # 6. Undo Test: Revert batch 2
    undo_res = organizer.undo_batch(batch_2.batch_id)
    assert undo_res["ok"] is True
    assert undo_res["undone_count"] == 8

    # Collision copies should be deleted
    remaining_collision_files = list(dest_dir.rglob("* (1).*"))
    assert len(remaining_collision_files) == 0

    # Original organized batch 1 should remain intact
    batch_1_files = list(dest_dir.rglob("*.*"))
    assert len(batch_1_files) == 8
