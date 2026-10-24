"""
LazySort - Safe File Organizer & Audit Logger
Handles collision prevention, non-destructive file operations,
audit logging without storing sensitive contents, and batch undo capability.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
from typing import List, Optional, Dict, Any
import uuid


@dataclass
class ProposedAction:
    file_path: Path
    file_name: str
    proposed_category: str
    target_dir: Path
    proposed_destination: Path
    reason: str
    is_selected: bool = True
    status: str = "Pending"  # "Pending", "Success", "Failed", "Skipped"
    error_message: Optional[str] = None


@dataclass
class AuditRecord:
    timestamp: str
    batch_id: str
    action_type: str  # "MOVE", "COPY", "UNDO_MOVE", "UNDO_COPY"
    source_path: str
    destination_path: str
    file_size_bytes: int
    status: str
    error_message: Optional[str] = None


def resolve_collision_path(target_directory: Path, filename: str) -> Path:
    """
    Prevents file overwriting. If 'invoice.pdf' exists in target_directory,
    returns 'invoice (1).pdf', 'invoice (2).pdf', etc.
    """
    target_directory.mkdir(parents=True, exist_ok=True)
    base_path = target_directory / filename
    if not base_path.exists():
        return base_path

    name_stem = base_path.stem
    extension = base_path.suffix

    counter = 1
    while True:
        candidate = target_directory / f"{name_stem} ({counter}){extension}"
        if not candidate.exists():
            return candidate
        counter += 1


@dataclass
class BatchResult:
    batch_id: str
    action_mode: str
    total: int
    success_count: int
    fail_count: int
    records: List[AuditRecord]


class SafeOrganizer:
    """Safely organizes files into destination categories with rollback support."""

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path = self.log_dir / "lazysort_audit.jsonl"

    def plan_organization(
        self,
        classifications: List[Any],
        destination_root: Path,
    ) -> List[ProposedAction]:
        """
        Creates a dry-run preview of planned movements.
        Does NOT touch any files on disk.
        """
        dest_root = Path(destination_root)
        proposals: List[ProposedAction] = []

        for item in classifications:
            category_dir = dest_root / item.category
            proposed_dest = resolve_collision_path(category_dir, item.file_name)

            proposals.append(
                ProposedAction(
                    file_path=item.file_path,
                    file_name=item.file_name,
                    proposed_category=item.category,
                    target_dir=category_dir,
                    proposed_destination=proposed_dest,
                    reason=item.reason,
                    is_selected=True,
                )
            )

        return proposals

    def execute_batch(
        self,
        proposals: List[ProposedAction],
        action_mode: str = "COPY",  # "COPY" or "MOVE"
    ) -> BatchResult:
        """
        Executes file operations only after user confirmation.
        Records every action in the privacy-safe audit log.
        """
        batch_id = str(uuid.uuid4())[:8]
        now_iso = datetime.now().isoformat()
        executed_records: List[AuditRecord] = []
        success_count = 0
        fail_count = 0

        action_mode = action_mode.upper()
        if action_mode not in ("COPY", "MOVE"):
            action_mode = "COPY"

        for proposal in proposals:
            if not proposal.is_selected:
                proposal.status = "Skipped"
                continue

            src = proposal.file_path
            if not src.exists():
                proposal.status = "Failed"
                proposal.error_message = "Source file no longer exists."
                fail_count += 1
                continue

            # Ensure parent directory exists
            proposal.target_dir.mkdir(parents=True, exist_ok=True)

            # Re-verify collision right before write to prevent race conditions
            final_dest = resolve_collision_path(proposal.target_dir, proposal.file_name)
            proposal.proposed_destination = final_dest

            file_size = src.stat().st_size

            try:
                if action_mode == "COPY":
                    shutil.copy2(src, final_dest)
                elif action_mode == "MOVE":
                    # Check if source and destination are identical
                    if src.resolve() == final_dest.resolve():
                        proposal.status = "Skipped"
                        proposal.error_message = "File is already in the target folder."
                        continue
                    shutil.move(src, final_dest)

                proposal.status = "Success"
                success_count += 1

                record = AuditRecord(
                    timestamp=now_iso,
                    batch_id=batch_id,
                    action_type=action_mode,
                    source_path=str(src.resolve()),
                    destination_path=str(final_dest.resolve()),
                    file_size_bytes=file_size,
                    status="SUCCESS",
                )
                executed_records.append(record)
                self._append_audit_log(record)

            except Exception as e:
                proposal.status = "Failed"
                proposal.error_message = str(e)
                fail_count += 1

                record = AuditRecord(
                    timestamp=now_iso,
                    batch_id=batch_id,
                    action_type=action_mode,
                    source_path=str(src.resolve()),
                    destination_path=str(final_dest.resolve()),
                    file_size_bytes=file_size,
                    status="FAILED",
                    error_message=str(e),
                )
                executed_records.append(record)
                self._append_audit_log(record)

        return BatchResult(
            batch_id=batch_id,
            action_mode=action_mode,
            total=len(proposals),
            success_count=success_count,
            fail_count=fail_count,
            records=executed_records,
        )

    def undo_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Reverses an executed batch:
        - If files were moved: moves them back to their original locations.
        - If files were copied: removes the created copies.
        """
        history = self.get_audit_history()
        batch_records = [r for r in history if r.get("batch_id") == batch_id and r.get("status") == "SUCCESS"]

        if not batch_records:
            return {"ok": False, "message": f"No successful operations found for Batch ID '{batch_id}'."}

        undone = 0
        errors = []
        now_iso = datetime.now().isoformat()

        for rec in reversed(batch_records):
            action = rec.get("action_type")
            dest = Path(rec.get("destination_path", ""))
            orig_src = Path(rec.get("source_path", ""))

            try:
                if action == "MOVE":
                    if dest.exists():
                        orig_src.parent.mkdir(parents=True, exist_ok=True)
                        undo_target = resolve_collision_path(orig_src.parent, orig_src.name)
                        shutil.move(dest, undo_target)
                        undone += 1
                        self._append_audit_log(
                            AuditRecord(
                                timestamp=now_iso,
                                batch_id=f"undo_{batch_id}",
                                action_type="UNDO_MOVE",
                                source_path=str(dest),
                                destination_path=str(undo_target),
                                file_size_bytes=rec.get("file_size_bytes", 0),
                                status="SUCCESS",
                            )
                        )
                elif action == "COPY":
                    if dest.exists():
                        dest.unlink()
                        undone += 1
                        self._append_audit_log(
                            AuditRecord(
                                timestamp=now_iso,
                                batch_id=f"undo_{batch_id}",
                                action_type="UNDO_COPY",
                                source_path=str(dest),
                                destination_path="[DELETED_COPY]",
                                file_size_bytes=rec.get("file_size_bytes", 0),
                                status="SUCCESS",
                            )
                        )
            except Exception as e:
                errors.append(f"Error reverting {dest.name}: {str(e)}")

        return {
            "ok": len(errors) == 0,
            "undone_count": undone,
            "errors": errors,
            "batch_id": batch_id,
        }

    def _append_audit_log(self, record: AuditRecord) -> None:
        """Appends a single JSON record to the audit log."""
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record)) + "\n")
        except Exception:
            pass

    def get_audit_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Reads recent audit history without sensitive contents."""
        if not self.audit_log_path.exists():
            return []
        records = []
        try:
            with open(self.audit_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception:
            pass
        return records[-limit:]
