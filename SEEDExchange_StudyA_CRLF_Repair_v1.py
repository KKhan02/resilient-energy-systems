#!/usr/bin/env python3
"""Study A v4 safe local repair for Git-for-Windows CRLF checkout conversion.

The three baseline GitLab source files are checked against SHA256 checksums verified
on main at commit 9aaca5473838b69de442cb238ba40a0e97405844.

Dry run by default. With --apply, only convert CRLF -> LF when the result is
BYTE FOR BYTE identical to the expected GitLab baseline. Never modify inputs
with any other difference. Backups remain inside this local project checkout.

Usage from the repository root, Miniforge Prompt or Anaconda Prompt:
  python SEEDExchange_StudyA_CRLF_Repair_v1.py --repo-root .
  python SEEDExchange_StudyA_CRLF_Repair_v1.py --repo-root . --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

SOURCE_HASHES = {
    "case1/studies/epm_gis_pandapower_v1/data/houses_candidate_associations.csv":
        "ad830d00739180d41755605b79d3091abbd9d4e3804779d526f8b33012cf50b9",
    "case1/studies/epm_gis_pandapower_v1/data/transformers_evidence.csv":
        "ca65a576a04db1f2e352233a9420ef88311d1cfa1429abf4b7c2d95812634891",
    "case1/studies/epm_gis_pandapower_v1/data/epm_network_relevant_sanitized.geojson":
        "adfa33a8a01b0b33ee449c69924515fed05ad49665868e8c1ae8ba5d047c1bab",
}

BACKUP_REL = "case1/studies/SEEDExchange_StudyA_LocalPreflight_v4/outputs/source_line_ending_backups_v1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit(root: Path) -> tuple[list[dict], bool]:
    rows = []
    for rel, expected in SOURCE_HASHES.items():
        path = root / rel
        row = {"file": rel, "expected_sha256": expected}
        if not path.is_file():
            row.update(status="MISSING", actual_sha256=None, canonical_sha256=None)
        else:
            original = path.read_bytes()
            raw_sha = sha256(original)
            canonical = original.replace(b"\r\n", b"\n")
            canonical_sha = sha256(canonical)
            if raw_sha == expected:
                status = "MATCH"
            elif canonical != original and canonical_sha == expected:
                status = "CRLF_ONLY"
            else:
                status = "DIFFERENT_CONTENT_OR_FORMAT"
            row.update(status=status, actual_sha256=raw_sha,
                       canonical_sha256=canonical_sha, size_bytes=len(original),
                       crlf_count=original.count(b"\r\n"))
        rows.append(row)
    safe = all(row["status"] in ("MATCH", "CRLF_ONLY") for row in rows)
    return rows, safe


def atomic_write(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def repair(root: Path, rows: list[dict]) -> list[str]:
    """Apply only proven newline conversions, with a verified backup first."""
    candidates = [r for r in rows if r["status"] == "CRLF_ONLY"]
    if not candidates:
        return []
    backup_dir = root / BACKUP_REL
    backup_dir.mkdir(parents=True, exist_ok=True)
    # Validate all backups before modifying any source. A different existing backup
    # is a blocker rather than something we silently overwrite.
    for r in candidates:
        path = root / r["file"]
        backup = backup_dir / path.name
        if backup.exists() and sha256(backup.read_bytes()) != r["actual_sha256"]:
            raise RuntimeError(f"Existing backup differs; not overwriting: {backup}")
    for r in candidates:
        path = root / r["file"]
        backup = backup_dir / path.name
        if not backup.exists():
            shutil.copy2(path, backup)
        original = path.read_bytes()
        if sha256(original) != r["actual_sha256"]:
            raise RuntimeError(f"Source changed since audit: {path}")
        canonical = original.replace(b"\r\n", b"\n")
        if sha256(canonical) != r["expected_sha256"]:
            raise RuntimeError(f"Source changed after audit, not modifying: {path}")
        atomic_write(path, canonical)
        if sha256(path.read_bytes()) != r["expected_sha256"]:
            raise RuntimeError(f"Post-write verification failed: {path}")
    return [r["file"] for r in candidates]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."),
                        help="Path to your local resilient-energy-systems checkout")
    parser.add_argument("--apply", action="store_true",
                        help="Repair newline-only differences; saves original files as backups")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    rows, safe = audit(root)
    print("Study A v4 source integrity and line-ending audit")
    print("Repo root:", root)
    for r in rows:
        print(f"  {r['status']}: {r['file']}")
        if r["status"] != "MATCH":
            print(f"    actual: {r['actual_sha256']}")
            print(f"    LF-normalized: {r['canonical_sha256']}")
            print(f"    expected: {r['expected_sha256']}")
    if not safe:
        print("STOP: At least one input differs beyond confirmed CRLF conversion or is missing.")
        print("No file was changed. Inspect those inputs before running the preflight.")
        return 2
    if args.apply:
        changed = repair(root, rows)
        after, after_safe = audit(root)
        if not after_safe or any(r["status"] != "MATCH" for r in after):
            print("ERROR: Final source hashes are not all canonical.")
            return 3
        print("Successfully normalized:", len(changed), "source file(s).")
        print("Original bytes backed up under:", root / BACKUP_REL)
        print("All three sources now match the exact GitLab canonical SHA-256 hashes.")
    else:
        print("PASS: Inputs are canonical or differ ONLY by CRLF conversion.")
        print("Dry run. Add --apply to safely normalize and back up any CRLF-only files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
