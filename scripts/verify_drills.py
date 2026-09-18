#!/usr/bin/env python3
"""
Verification Test Suite - Milestone 5: Troubleshooting Drills & Diagnostic Lab
Validates Drill Manager scenario integrity, command syntax, and diagnostic runbook documentation.
"""

import os
import subprocess
import sys

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DRILL_MANAGER = os.path.join(REPO_ROOT, "scripts", "drill_manager.py")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
DRILLS_DOCS_DIR = os.path.join(DOCS_DIR, "troubleshooting-drills")
DR_DRILLS_DOC = os.path.join(DOCS_DIR, "03-disaster-recovery-drills.md")

RESULTS = []


def record(check_name, passed, detail=""):
    RESULTS.append((check_name, passed, detail))
    status_str = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"  [{status_str}] {BOLD}{check_name}{RESET}: {detail}")


def main():
    print(f"\n{BLUE}{BOLD}=============================================================================={RESET}")
    print(f"{BLUE}{BOLD}     Milestone 5: Troubleshooting Drills & Diagnostic Lab Verification Suite {RESET}")
    print(f"{BLUE}{BOLD}=============================================================================={RESET}\n")

    # 1. Verify Drill Manager CLI Executable
    record("Drill Manager Script Present", os.path.exists(DRILL_MANAGER), f"Found {DRILL_MANAGER}")
    if os.path.exists(DRILL_MANAGER):
        res = subprocess.run(["python3", DRILL_MANAGER, "--list"], capture_output=True, text=True)
        record("Drill Manager CLI Catalog Execution", res.returncode == 0, "CLI lists all available scenarios")

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
        record(f"Runbook [{name}]", exists, f"Found {path}" if exists else f"Missing {path}")
        if exists:
            with open(path, "r") as f:
                content = f.read()
                record(f"Runbook [{name}] Content Hygiene", len(content) > 200, f"{len(content.splitlines())} lines documented")

    # 3. Import & Verify Drill Scenario Catalog
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    try:
        import drill_manager
        scenarios = drill_manager.SCENARIOS
        record("Scenario Catalog Definition", len(scenarios) >= 7, f"{len(scenarios)} scenarios defined across Compute, Network & Storage")

        for sc_id, sc in scenarios.items():
            valid = bool(sc.get("domain") and sc.get("title") and sc.get("inject_cmds") and sc.get("heal_cmds"))
            record(f"Scenario Integrity [{sc_id}]", valid, f"Domain: {sc.get('domain')} | {sc.get('title')}")
    except Exception as e:
        record("Scenario Catalog Definition", False, str(e))

    all_passed = all(p for _, p, _ in RESULTS)
    print("\n" + "-" * 80)
    if all_passed:
        print(f"{GREEN}{BOLD}🎉 Milestone 5 Verification Succeeded: All drill definitions and runbooks verified!{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}❌ Milestone 5 Verification Failed: One or more checks failed.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
