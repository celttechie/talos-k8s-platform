#!/usr/bin/env python3
"""
Talos Kubernetes Platform - Shared Automation & Verification Utilities
Provides unified target host resolution, Terraform output parsing, TCP connectivity
probing with SSH fallback, subprocess execution, and standardized test reporting.
"""

import json
import os
import re
import socket
import subprocess
import sys

# -----------------------------------------------------------------------------
# Terminal Styling Constants
# -----------------------------------------------------------------------------
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


def get_repo_root():
    """Return the absolute path to the repository root."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_target_env(env_path=None):
    """Load and parse key-value pairs from target.env file.

    Returns:
        dict: Parsed environment variables from target.env.
    """
    if env_path is None:
        env_path = os.path.join(get_repo_root(), "target.env")

    env_vars = {}
    if os.path.exists(env_path):
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip().strip('"\'')
        except Exception:
            pass
    return env_vars


def get_target_host(repo_root=None):
    """Dynamically determine target hypervisor host from environment, target.env, or terraform.tfvars.

    Search precedence:
    1. TARGET_HOST environment variable
    2. TARGET_HOST declared in target.env
    3. libvirt_uri parsed from terraform/environments/02-talos-cluster/terraform.tfvars
    4. libvirt_uri parsed from terraform/environments/01-nested-sandbox/terraform.tfvars

    Returns:
        str or None: Discovered hostname / IP address, or None if local.
    """
    if os.getenv("TARGET_HOST"):
        return os.getenv("TARGET_HOST")

    if repo_root is None:
        repo_root = get_repo_root()

    # Check target.env
    target_env = load_target_env(os.path.join(repo_root, "target.env"))
    if target_env.get("TARGET_HOST"):
        return target_env["TARGET_HOST"]

    # Check terraform.tfvars across stages
    for stage in ["02-talos-cluster", "01-nested-sandbox"]:
        tfvars_path = os.path.join(repo_root, "terraform", "environments", stage, "terraform.tfvars")
        if os.path.exists(tfvars_path):
            try:
                with open(tfvars_path, "r") as f:
                    for line in f:
                        if "libvirt_uri" in line:
                            match = re.search(r"@([^/:]+)", line)
                            if match:
                                return match.group(1)
            except Exception:
                pass
    return None


def get_terraform_outputs(environment_name, repo_root=None):
    """Retrieve and parse JSON outputs from a Terraform environment directory.

    Args:
        environment_name (str): Environment folder name (e.g. '01-nested-sandbox' or '02-talos-cluster').
        repo_root (str, optional): Root repository path.

    Returns:
        dict or None: Parsed JSON outputs, or None if state is uninitialized.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    env_dir = os.path.join(repo_root, "terraform", "environments", environment_name)
    if not os.path.exists(env_dir):
        return None

    try:
        res = subprocess.run(
            ["terraform", f"-chdir={env_dir}", "output", "-json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(res.stdout)
    except Exception:
        return None


def run_cmd(cmd, check=True, capture=True, timeout=None, shell=True):
    """Execute a system command and return CompletedProcess.

    Args:
        cmd (str or list): Command to execute.
        check (bool): If True, logs error and returns process without raising exception.
        capture (bool): If True, captures stdout and stderr.
        timeout (int, optional): Timeout in seconds.
        shell (bool): Run command through shell.

    Returns:
        subprocess.CompletedProcess: Result of command execution.
    """
    try:
        res = subprocess.run(cmd, shell=shell, text=True, capture_output=capture, timeout=timeout)
        if check and res.returncode != 0:
            if capture and res.stderr:
                print(f"{RED}Command failed: {cmd}\n{res.stderr.strip()}{RESET}")
        return res
    except subprocess.TimeoutExpired:
        print(f"{RED}Command timed out after {timeout}s: {cmd}{RESET}")
        return subprocess.CompletedProcess(args=cmd, returncode=124, stdout="", stderr=f"Timeout after {timeout}s")


def validate_yaml_file(filepath):
    """Validate that a file exists and contains valid YAML content.

    Args:
        filepath (str): Path to YAML manifest file.

    Returns:
        tuple (bool, str): (True, 'Valid YAML schema') or (False, error_message).
    """
    try:
        import yaml
        with open(filepath, "r") as f:
            list(yaml.safe_load_all(f))
        return True, "Valid YAML schema"
    except Exception as e:
        return False, str(e)


def check_tcp_port(ip, port, timeout=3, target_host=None):
    """Check TCP connectivity to an IP and port, with automatic remote SSH fallback.

    Args:
        ip (str): Destination IP address.
        port (int): Destination TCP port.
        timeout (int): Timeout in seconds.
        target_host (str, optional): Target hypervisor host for SSH fallback.

    Returns:
        bool: True if port is responsive, False otherwise.
    """
    # 1. Try direct local socket probe
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            return True
    except Exception:
        pass

    # 2. Remote SSH fallback
    if target_host is None:
        target_host = get_target_host()

    if not target_host or target_host in ["localhost", "127.0.0.1"]:
        return False

    try:
        cmd = [
            "ssh", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no",
            target_host,
            f"python3 -c 'import socket; s = socket.socket(); s.settimeout({timeout}); res = s.connect_ex((\"{ip}\", {port})); s.close(); exit(res)'"
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=timeout + 3)
        return res.returncode == 0
    except Exception:
        return False


# -----------------------------------------------------------------------------
# Test Reporting & Results Tracker
# -----------------------------------------------------------------------------
class TestReporter:
    """Standardized test result accumulator and formatter across verification suites."""

    def __init__(self, title):
        self.title = title
        self.results = []
        print(f"\n{BLUE}{BOLD}{'=' * 78}{RESET}")
        print(f"{BLUE}{BOLD}     {self.title:<73}{RESET}")
        print(f"{BLUE}{BOLD}{'=' * 78}{RESET}\n")

    def record(self, check_name, passed, detail=""):
        """Record a single check result and print formatted output."""
        self.results.append((check_name, passed, detail))
        status_str = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  [{status_str}] {BOLD}{check_name}{RESET}: {detail}")

    @property
    def all_passed(self):
        """Return True if all recorded checks passed."""
        return bool(self.results) and all(passed for _, passed, _ in self.results)

    def summary(self, success_message="Verification Succeeded!", fail_message="Verification Failed: Some checks did not pass."):
        """Print test summary banner and return appropriate exit code (0 or 1)."""
        print("\n" + "-" * 78)
        if self.all_passed:
            prefix = "" if success_message.startswith("🎉") else "🎉 "
            print(f"{GREEN}{BOLD}{prefix}{success_message}{RESET}\n")
            return 0
        else:
            prefix = "" if fail_message.startswith("❌") else "❌ "
            print(f"{RED}{BOLD}{prefix}{fail_message}{RESET}\n")
            return 1
