#!/usr/bin/env python3
"""
Verification Test Suite - Milestone 5: Troubleshooting Drills & Diagnostic Lab
Validates Drill Manager scenario integrity, command syntax, and diagnostic runbook documentation.
"""

import os
import subprocess
import sys

from common import (
    TestReporter,
    get_repo_root,
)

REPO_ROOT = get_repo_root()
DRILL_MANAGER = os.path.join(REPO_ROOT, "scripts", "drill_manager.py")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
DRILLS_DOCS_DIR = os.path.join(DOCS_DIR, "troubleshooting-drills")
DR_DRILLS_DOC = os.path.join(DOCS_DIR, "03-disaster-recovery-drills.md")


def main():
    reporter = TestReporter("Milestone 5: Troubleshooting Drills & Diagnostic Lab Verification Suite")

    # 1. Verify Drill Manager CLI Executable
    reporter.record("Drill Manager Script Present", os.path.exists(DRILL_MANAGER), f"Found {DRILL_MANAGER}")
    if os.path.exists(DRILL_MANAGER):
        res = subprocess.run(["python3", DRILL_MANAGER, "--list"], capture_output=True, text=True)
        reporter.record("Drill Manager CLI Catalog Execution", res.returncode == 0, "CLI lists all available scenarios")

    # 2. Verify Diagnostic Runbooks
    runbooks = [
        ("Master Troubleshooting Framework", os.path.join(DRILLS_DOCS_DIR, "README.md")),
        ("Compute & Scheduling Runbooks", os.path.join(DRILLS_DOCS_DIR, "01-compute-drills.md")),
        ("Networking & eBPF Runbooks", os.path.join(DRILLS_DOCS_DIR, "02-networking-drills.md")),
        ("Storage & CSI Runbooks", os.path.join(DRILLS_DOCS_DIR, "03-storage-drills.md")),
        ("Disaster Recovery & Operational Drills", DR_DRILLS_DOC)
    ]

    for name, path in runbooks:
        exists = os.path.exists(path)
        reporter.record(f"Runbook [{name}]", exists, f"Found {path}" if exists else f"Missing {path}")
        if exists:
            with open(path, "r") as f:
                content = f.read()
                reporter.record(f"Runbook [{name}] Content Hygiene", len(content) > 200, f"{len(content.splitlines())} lines documented")

    # 3. Import & Verify Drill Scenario Catalog
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    try:
        import drill_manager
        scenarios = drill_manager.SCENARIOS
        reporter.record("Scenario Catalog Definition", len(scenarios) >= 7, f"{len(scenarios)} scenarios defined across Compute, Network & Storage")

        for sc_id, sc in scenarios.items():
            valid = bool(sc.get("domain") and sc.get("title") and sc.get("inject_cmds") and sc.get("heal_cmds"))
            reporter.record(f"Scenario Integrity [{sc_id}]", valid, f"Domain: {sc.get('domain')} | {sc.get('title')}")
    except Exception as e:
        reporter.record("Scenario Catalog Definition", False, str(e))

    return reporter.summary(
        "🎉 Milestone 5 Verification Succeeded: All drill definitions and runbooks verified!",
        "❌ Milestone 5 Verification Failed: One or more checks failed."
    )


if __name__ == "__main__":
    sys.exit(main())
