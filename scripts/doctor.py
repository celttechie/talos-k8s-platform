#!/usr/bin/env python3
"""
Talos Kubernetes Platform - Workstation Environment Doctor
Assesses local workstation development tools, CLI binaries, versions, and git quality gates.
"""

import json
import os
import shutil
import subprocess
import sys

from common import (
    BLUE,
    BOLD,
    GREEN,
    RED,
    RESET,
    YELLOW,
)

CHECKS = []

def check_local_item(name, command, min_version=None, required=True, purpose=""):
    """Check if a local CLI tool is installed and optionally verify version."""
    path = shutil.which(command.split()[0])
    if not path:
        status = f"{RED}MISSING{RESET}" if required else f"{YELLOW}OPTIONAL (NOT FOUND){RESET}"
        CHECKS.append((name, False if required else True, status, purpose))
        return

    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True).strip()
        version_line = output.splitlines()[0] if output else "Installed"
        status = f"{GREEN}OK{RESET} ({version_line})"
        CHECKS.append((name, True, status, purpose))
    except Exception as e:
        status = f"{YELLOW}INSTALLED (Version check failed: {e}){RESET}"
        CHECKS.append((name, True, status, purpose))

def check_gh_auth():
    """Check if GitHub CLI is authenticated on local workstation."""
    path = shutil.which("gh")
    if not path:
        CHECKS.append(("GitHub CLI Auth", False, f"{RED}gh CLI missing{RESET}", "Repo & Project Management"))
        return
    try:
        res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if res.returncode == 0:
            CHECKS.append(("GitHub CLI Auth", True, f"{GREEN}AUTHENTICATED{RESET}", "Milestones, PRs, & Issues"))
        else:
            CHECKS.append(("GitHub CLI Auth", False, f"{YELLOW}NOT AUTHENTICATED (`gh auth login` required){RESET}", "Project Management"))
    except Exception as e:
        CHECKS.append(("GitHub CLI Auth", False, f"{YELLOW}Error checking auth: {e}{RESET}", "Project Management"))

def check_pre_commit():
    """Check if pre-commit hooks are installed in .git/hooks."""
    hook_path = os.path.join(".git", "hooks", "pre-commit")
    if os.path.exists(hook_path):
        CHECKS.append(("Git Pre-Commit Hook", True, f"{GREEN}INSTALLED{RESET}", "Local Quality Gates"))
    else:
        CHECKS.append(("Git Pre-Commit Hook", False, f"{YELLOW}NOT INSTALLED (Run `pre-commit install`){RESET}", "Local Quality Gates"))

def main():
    print(f"\n{BLUE}{BOLD}=============================================================================={RESET}")
    print(f"{BLUE}{BOLD}     Talos Kubernetes Platform - Workstation Environment Doctor               {RESET}")
    print(f"{BLUE}{BOLD}=============================================================================={RESET}\n")

    check_local_item("Terraform / OpenTofu", "terraform version", required=True, purpose="Infrastructure as Code")
    check_local_item("Talos CLI (talosctl)", "talosctl version --client --short", required=True, purpose="Talos API & Node Management")
    check_local_item("Kubernetes CLI (kubectl)", "kubectl version --client -o yaml | grep gitVersion", required=True, purpose="Cluster Operations")
    check_local_item("Helm CLI", "helm version --short", required=True, purpose="Package & Chart Management")
    check_local_item("Cilium CLI", "cilium version --client", required=False, purpose="eBPF CNI & Hubble Diagnostics")
    check_local_item("Pre-Commit", "pre-commit --version", required=True, purpose="Git Code Quality Hooks")
    check_local_item("GitHub CLI (gh)", "gh --version", required=True, purpose="Issue & Milestone Tracking")
    check_local_item("Python 3", "python3 --version", required=True, purpose="Automation & Verification Scripts")
    check_gh_auth()
    check_pre_commit()

    all_passed = True
    print(f"{BOLD}{'Tool / Check':<32} {'Status':<36} {'Purpose'}{RESET}")
    print("-" * 80)
    for name, ok, status, purpose in CHECKS:
        if not ok:
            all_passed = False
        print(f"{name:<32} {status:<36} {purpose}")

    print("\n" + "-" * 80)
    if all_passed:
        print(f"{GREEN}{BOLD}🎉 Workstation client environment is 100% ready for platform development!{RESET}\n")
        return 0
    else:
        print(f"{YELLOW}{BOLD}⚠️  Some workstation prerequisites require attention (see above).{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
